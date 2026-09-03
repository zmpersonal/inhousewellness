"""Caption generation -- the ONLY place a model call is permitted in the cycle.

One batched call per cycle covering every post (4 Pinterest + 1 IG + 1 FB),
never one call per post. Input is the compact brief assembled by code; output is
a strict JSON array validated against a schema and then run through the Round 1
output validator before anything can be scheduled.

On validation failure: retry once, then halt with a BLOCKED report. There is no
path that publishes a degraded caption.

Token usage is instrumented per cycle and reported as cost per published post.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .limits import (ARCHETYPE_BODY, MIN_BODY_ROWS, PIN_ALT_MAX, PIN_ALT_MIN,
                     PIN_TITLE_MAX, PIN_TITLE_MIN, card_archetype)
from . import facts as FACTS
from .validator import PostRejected, assert_no_shared_text, validate
from .voice import VOICE

MODEL = "claude-opus-5"
MAX_RETRIES = 1

# Published pricing is per million tokens; kept here so cost-per-post is
# reported in dollars rather than raw counts.
PRICE_PER_MTOK = {"input": 5.0, "output": 25.0}


NUMERIC_RULE = """\
NUMBERS -- enforced in code, a violation halts the run
Every numeral you write must come from this post's `facts` block, verbatim.
Do not round, convert, average, extrapolate or combine them. Do not introduce a
figure that is not there -- no prices, dates, percentages or counts of your own.
If a post has no `facts` block, write it with no numerals at all beyond small
ordinals (1-10) used structurally.
"""

SCHEMA_DOC = """\
Return ONLY a JSON array. One object per order_id, same order, no prose, no
markdown fence.

Every object carries the platform copy AND a "card" object -- the body of the
rendered image. The card is not optional: a card with only a headline renders
~70% empty and is rejected in code.

pinterest: {"order_id": str, "title": str, "text": str, "alt_text": str, "card": {...}}
instagram: {"order_id": str, "text": str, "slides": [str, ...], "card": {...}}
facebook:  {"order_id": str, "text": str, "first_comment": str, "card": {...}}

The "card" object always has:
  "kicker"   short sentence-case label, 2-5 words. NEVER ALL-CAPS.
  "headline" 4-12 words that MAKE A CLAIM. See below -- this is the single
             biggest quality lever on the card.
  "note"     optional one-line caveat or source note

HEADLINES ASSERT, THEY DO NOT LABEL A TOPIC
Say something the reader would not already assume, or contradict something they
would. Lead with the figure where it carries the claim.
  good  "Same 180F. Completely different heat." / "71 of 90 need no electrician."
  bad   "Infrared vs steam: the differences that matter" / "Understanding humidity"
REJECTED phrases: "what actually matters", "the differences that matter", "what
you need to know", "a complete guide", "everything about", "what actually
differs", "the real difference". If the figures support nothing surprising, say
the plainest useful thing -- do not reach for drama the data does not carry.

plus the fields for this order's card_archetype:

  comparison  "a", "b"  column labels (2-3 words each)
              "rows"    3-5 rows, each ["label", "aValue", "bValue"]
  cost        "figure"  the headline number, e.g. "$0.71"
              "unit"    what it measures, one line
              "rows"    3-5 rows, each ["label", "value"]
  spec        "rows"    3-6 rows, each ["label", "value"]
  checklist   "items"   3-6 short strings
  evidence    "claim", "finding", "strength" (strong|moderate|limited), "source"
  correction  "xLabel", "yLabel"  sentence-case column labels
              "x"       2-4 things buyers wrongly compare
              "y"       2-4 things that actually decide it

Card values are terse -- they sit in a table, not a paragraph. Table cells are
2-6 words. Never write "N/A"; if a value is genuinely unpublished, say
"Not published".

TABLE CELLS CARRY MEASUREMENTS, NOT ADJECTIVES (enforced in code)
comparison/cost/spec need >=2 cells stating a real value.
  good  "130 to 150F"  "5 to 15%"  "240V / 20 amps"  "$3,299"  "15 min"
  bad   "Lower"  "Higher"  "Flexible"  "Limited"  "Occasional"  "Not required"
Drop a row rather than fill it with a comparative adjective. Your brief carries
`figures_payload` -- values already measured from the named source. USE THEM
VERBATIM as cells; reword the row LABEL if you like, never the value.
"""


def build_prompt(brief):
    return (
        f"{VOICE}\n{NUMERIC_RULE}\n{SCHEMA_DOC}\n"
        f"Write copy for these {len(brief)} posts. Each post's copy must be "
        f"written for its own platform; never reuse a sentence across platforms.\n\n"
        f"{json.dumps(brief, separators=(',', ':'))}"
    )


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    # Why a retry happened. A successful cycle that silently retried hides the
    # reason -- and if UNGROUNDED_NUMERAL was the cause, that is exactly the
    # signal about prompt presentation we need to see.
    attempt_errors: list = field(default_factory=list)

    def add(self, i, o):
        self.input_tokens += i
        self.output_tokens += o
        self.calls += 1

    @property
    def usd(self):
        return (self.input_tokens / 1e6 * PRICE_PER_MTOK["input"]
                + self.output_tokens / 1e6 * PRICE_PER_MTOK["output"])

    def report(self, n_posts):
        per = self.usd / n_posts if n_posts else 0.0
        return (f"tokens in {self.input_tokens:,} / out {self.output_tokens:,} "
                f"over {self.calls} call(s) = ${self.usd:.4f}; "
                f"${per:.4f} per published post")


class CaptionError(Exception):
    pass


def _strip_fence(s):
    s = (s or "").strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", s, re.S)
    return (m.group(1) if m else s).strip()


def parse_response(raw, brief):
    """Parse and shape-check. Raises CaptionError with an actionable message."""
    try:
        data = json.loads(_strip_fence(raw))
    except json.JSONDecodeError as e:
        raise CaptionError(f"response is not valid JSON: {e}")
    if not isinstance(data, list):
        raise CaptionError(f"expected a JSON array, got {type(data).__name__}")

    by_id = {}
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise CaptionError(f"item {i} is not an object")
        oid = obj.get("order_id")
        if not oid:
            raise CaptionError(f"item {i} has no order_id")
        by_id[oid] = obj

    missing = [b["order_id"] for b in brief if b["order_id"] not in by_id]
    if missing:
        raise CaptionError(f"missing copy for {len(missing)} order(s): {missing[:3]}")

    for b in brief:
        obj, p = by_id[b["order_id"]], b["platform"]
        need = {"pinterest": ("title", "text", "alt_text"),
                "instagram": ("text", "slides"),
                "facebook": ("text", "first_comment")}[p]
        for f in need:
            if f not in obj or obj[f] in (None, "", []):
                raise CaptionError(f"{b['order_id']}: missing required field {f!r}")
        if p == "instagram" and not isinstance(obj["slides"], list):
            raise CaptionError(f"{b['order_id']}: slides must be a list")

        card = obj.get("card")
        if not isinstance(card, dict) or not card:
            raise CaptionError(
                f"{b['order_id']}: missing the 'card' object — the rendered image "
                f"body. A card with only a headline renders ~70% empty.")
        arch = b.get("card_archetype")
        spec = ARCHETYPE_BODY.get(arch)
        if spec:
            gaps = [f for f in spec["required"] if card.get(f) in (None, "", [], {})]
            if gaps:
                raise CaptionError(
                    f"{b['order_id']}: card is a {arch} and is missing {gaps}; "
                    f"expected {spec['desc']}")
    return by_id


def to_posts(by_id, orders):
    """Map model output + code-owned fields into validator-shaped posts.

    Structural fields (link, board_id, media) come from the work order, never
    from the model. The model supplies prose only.
    """
    posts = []
    for o in orders:
        c = by_id[o["order_id"]]
        card = dict(c.get("card") or {})
        p = {"id": o["item_id"], "platform": o["platform"],
             "text": c["text"], "mediaUrls": o.get("mediaUrls") or [],
             "_archetype": o.get("card_archetype"),
             "_body": card,
             # What the figures are ABOUT, and what the destination is about.
             # Used by DESTINATION_MISMATCH; absent means "cannot judge".
             "_figure_terms": o.get("figure_terms"),
             "_destination_terms": o.get("destination_terms")}
        if o["platform"] == "pinterest":
            p.update(title=c["title"], altText=c["alt_text"],
                     link=o["link"], boardId=o["board_id"])
        elif o["platform"] == "facebook":
            # The model writes the sentence; CODE appends the URL. The model is
            # never given the chance to emit a link at all, so it cannot
            # fabricate one, mistype one, or leave a placeholder where one
            # should be. Facebook links live in the first comment, never the body.
            lead = re.sub(r"https?://\S+", "", c["first_comment"]).strip(" :-\u2014")
            p["firstComment"] = f"{lead}: {o['link']}" if lead else o["link"]
            p["_link"] = o["link"]
        else:
            p["_slides"] = c["slides"]
            p["_bio_link"] = o["link"]      # link-in-bio target
        posts.append(p)
    return posts


def generate(orders, brief, call_model, *, media_by_order=None, usage=None):
    """Run the single batched call, validate, retry once, else raise.

    call_model(prompt) -> (text, input_tokens, output_tokens)
    """
    usage = usage or Usage()
    # Each post is validated against its OWN grounding: the facts it was given.
    grounding_by_id = {}
    for o in orders:
        sd = o.get("source_data")
        fp = o.get("figures_payload")
        # Everything the brief SHOWS this order -- facts, notes and the measured
        # figures payload -- is what its numerals may draw from.
        extra = json.dumps(fp) if fp else None
        if sd or extra:
            grounding_by_id[o["item_id"]] = FACTS.grounding_text(sd, extra=extra)
        else:
            grounding_by_id[o["item_id"]] = None
    if media_by_order:
        for o in orders:
            o["mediaUrls"] = media_by_order.get(o["order_id"], [])

    prompt, errors = build_prompt(brief), []
    for attempt in range(MAX_RETRIES + 1):
        raw, tin, tout = call_model(prompt)
        usage.add(tin, tout)
        try:
            by_id = parse_response(raw, brief)
            posts = to_posts(by_id, orders)
            results = [validate(p, grounding=grounding_by_id.get(p["id"]))
                       for p in posts]
            bad = [r for r in results if not r.ok]
            if bad:
                raise CaptionError("validator rejected:\n" +
                                   "\n".join(r.summary() for r in bad))
            assert_no_shared_text(posts)
            return posts, usage
        except (CaptionError, PostRejected) as e:
            errors.append(f"attempt {attempt + 1}: {e}")
            usage.attempt_errors.append(f"attempt {attempt + 1}: {e}")
            prompt = (build_prompt(brief) +
                      "\n\nYour previous attempt was REJECTED. Fix exactly these "
                      "problems and return the full corrected array:\n" + str(e))

    raise CaptionError(
        "BLOCKED: caption generation failed validation after "
        f"{MAX_RETRIES + 1} attempts. Nothing published.\n" + "\n\n".join(errors))
