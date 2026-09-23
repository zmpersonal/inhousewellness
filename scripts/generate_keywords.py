#!/usr/bin/env python3
"""Round 19 — grow the keyword queue from the corpus we already hold.

THE CONSTRAINT THIS EXISTS FOR. 62 distinct keyword signatures are eligible.
At 14 pins a week that is 4.4 weeks, and the 120-day repost floor then leaves
~16 weeks with nothing eligible. Scheduling four weeks against that queue would
consume 56 of 62 and strand the account. 14/week needs a queue that refills.

No external API and NO MODEL CALL. Candidates come from the 1,908-page corpus
this repo already carries -- titles and slugs across INH and the ten satellites
-- and every downstream gate stays exactly where it was: the 0.40 match
threshold, the subject-compatibility gate, the figure requirement.

⚠️ A GENERATED ROW THAT CANNOT CARRY FIGURES IS NOT RUNWAY. `has_figures` is
the same gate selection applies, so a row failing it can never be picked. Such
rows are counted and discarded rather than appended, because appending them
would inflate the runway number with rows the selector will always skip --
which is the one number this script exists to report honestly.

  python3 scripts/generate_keywords.py            # report only, writes nothing
  python3 scripts/generate_keywords.py --write
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import destinations as D
from src import remap as R
from src import workorders as WO
from src.limits import QUANTITATIVE_ARCHETYPES, card_archetype

QUEUE = ROOT / "data" / "pinterest-keyword-queue.json"
CORPUS = ROOT / "data" / "corpus-index.json"

# Runway thresholds. Warn early, halt before the queue is actually dry --
# never by lowering the threshold or the repost floor, which is the failure
# that produced the 11,200-impression baseline.
PINS_PER_WEEK = 14
WARN_WEEKS = 3.0
HALT_WEEKS = 1.0

# A title is not a search phrase. Strip the publisher's furniture.
_SUBTITLE = re.compile(r"\s*[:|–—]\s*.*$")
_BRACKETS = re.compile(r"[\(\[].*?[\)\]]")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_NOISE = re.compile(
    r"\b(?:the ultimate|ultimate|complete|definitive|a |an |the )\b", re.I)
_EDGE = re.compile(r"^(?:guide|guides|blog|home|best)\b\s*|\s*\b(?:guide|guides)$", re.I)
_WS = re.compile(r"\s+")

# Phrases that are navigation, not a question anyone searches for.
_REJECT = re.compile(
    r"\b(?:privacy|terms|policy|contact|about us|cart|checkout|account|login|"
    r"shipping|returns|faq|sitemap|search|collections?|products?|page \d+|"
    r"author|category|tag|archive|subscribe|newsletter)\b", re.I)

MIN_WORDS, MAX_WORDS = 3, 7

# ── WHY THIS IS NARROW ON PURPOSE ───────────────────────────────────────────
# The unfiltered first version produced 542 rows and reported 43 weeks of
# runway. All three of its properties were disqualifying:
#
#   * median match score 1.000 -- the keyword IS the article title, so it
#     matches its own source perfectly and the 0.40 threshold does no work at
#     all. A gate that cannot fail is not a gate.
#   * INH share 12.3% against the 40% floor, because 1,753 of the 1,908 corpus
#     pages are satellites.
#   * ~90 of them were one programmatic template: "cold plunge cost in
#     albuquerque, nm", "... in anaheim, ca", "... in anchorage, ak". Ninety
#     near-identical pins is the 75-blank-pins failure wearing a new costume.
#
# So generated rows are INH-only (which also defends the floor), de-templated,
# and must carry real figures. That yields far fewer rows and an honest number.
TEMPLATE_MAX = 2          # at most N rows sharing one title template
_PLACE = re.compile(r"\b(?:in|for|near)\s+[a-z .'-]+,\s*[a-z]{2}\b", re.I)
_NUM = re.compile(r"\d+")


def template_key(kw):
    """Collapse a programmatic family to one key.

    "cold plunge cost in austin, tx" and "... in anaheim, ca" are one template
    and belong in the queue at most a couple of times, not ninety.
    """
    k = _PLACE.sub(" <place> ", kw)
    k = _NUM.sub("<n>", k)
    return _WS.sub(" ", k).strip()


def phrase_from(title, slug):
    """A search-shaped phrase, or None.

    Titles carry a headline and a subtitle; the headline is the part a person
    would type. Slugs are the fallback where a title is a brand name.
    """
    for raw in (title or "", (slug or "").replace("-", " ")):
        s = _SUBTITLE.sub("", raw)
        s = _BRACKETS.sub(" ", s)
        s = _YEAR.sub(" ", s)
        s = _NOISE.sub(" ", s)
        s = _EDGE.sub(" ", s)
        s = _WS.sub(" ", s).strip(" -–—:|,.").lower()
        if not s or _REJECT.search(s):
            continue
        if not (MIN_WORDS <= len(s.split()) <= MAX_WORDS):
            continue
        # It must be about something we sell or study, or it is not our row.
        if not R.subjects(s):
            continue
        return s
    return None


def infer_archetype(kw):
    """Archetype decides which figures a card needs. Inferred from the phrase,
    deterministically -- the model is never asked."""
    if re.search(r"\bvs\b|\bversus\b|\bor\b.*\b(sauna|plunge|tub)\b", kw):
        return "comparison"
    if re.search(r"\bcost|price|cheap|budget|worth\b", kw):
        return "cost"
    if re.search(r"\bdimension|size|sizes|width|depth|height|fit|space\b", kw):
        return "spec_table"
    if re.search(r"\bhow to|how do|steps|routine|use a\b", kw):
        return "reality_check"
    if re.search(r"\bemf|safe|safety|risk|danger\b", kw):
        return "correction"
    return "reality_check"


def next_id(existing):
    n = 0
    for r in existing:
        m = re.match(r"pin-g(\d+)$", str(r.get("id") or ""))
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def eligible_signatures(rows, state, today):
    """Distinct keyword signatures the selector could actually pick today.

    SIGNATURES, not rows: week-wide dedup collapses near-duplicates, so two
    rows with the same signature are one week-slot, not two. Counting rows
    overstates the runway -- 74 eligible rows are only 62 usable slots.
    """
    sigs = set()
    for r in rows:
        ok, _ = WO.eligible(r, "pinterest", state, today)
        if ok:
            sigs.add(WO.keyword_signature(r.get("keyword")))
    return sigs


def runway_report(rows, state=None, today=None):
    state = state if state is not None else WO.load_state()
    today = today or dt.date.today().isoformat()
    sigs = eligible_signatures(rows, state, today)
    weeks = len(sigs) / PINS_PER_WEEK
    return {"eligible_signatures": len(sigs), "weeks": round(weeks, 1),
            "pins_per_week": PINS_PER_WEEK,
            "level": ("halt" if weeks < HALT_WEEKS
                      else "warn" if weeks < WARN_WEEKS else "ok")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="cap appended rows")
    a = ap.parse_args()

    queue = json.loads(QUEUE.read_text())
    rows = queue["items"]
    corpus = json.loads(CORPUS.read_text())["articles"]
    idf = R.build_idf(corpus)

    before = runway_report(rows)
    print(f"runway BEFORE: {before['eligible_signatures']} eligible signatures "
          f"= {before['weeks']} weeks at {PINS_PER_WEEK}/week  [{before['level']}]")

    known = {WO.keyword_signature(r.get("keyword")) for r in rows}
    known_templates = {}
    for r in rows:
        known_templates[template_key(r.get("keyword") or "")] = \
            known_templates.get(template_key(r.get("keyword") or ""), 0) + 1

    # INH pages only. Generated rows are the tail of the queue, and the tail is
    # where the INH floor is easiest to defend -- the researched rows already
    # skew satellite (INH is 29% of the live week).
    inh_pages = [p for p in corpus if p.get("is_inh")]
    seen_new, cand, dropped_template, untitled = set(), [], 0, 0
    for page in inh_pages:
        title, slug = page.get("title"), page.get("slug")
        if not (title or slug):
            # A page with neither is a corpus defect, not a silent skip: if the
            # sitemap sweep starts returning bare rows, this number moves and
            # someone can see it.
            untitled += 1
            continue
        kw = phrase_from(title, slug)
        if not kw:
            continue
        sig = WO.keyword_signature(kw)
        if sig in known or sig in seen_new:
            continue
        tk = template_key(kw)
        if known_templates.get(tk, 0) >= TEMPLATE_MAX:
            dropped_template += 1
            continue
        known_templates[tk] = known_templates.get(tk, 0) + 1
        seen_new.add(sig)
        cand.append(kw)
    print(f"\ncorpus {len(corpus)} pages, {len(inh_pages)} of them INH")
    print(f"candidates: {len(cand)} new signatures "
          f"({dropped_template} dropped as repeats of one template, "
          f"{untitled} pages carried neither title nor slug)")

    nid = next_id(rows)
    appended, rejected = [], {"no match": 0, "not quantitative": 0,
                              "no figures": 0, "no destination": 0}
    for kw in sorted(cand):
        # match_row -> (score, article, verdict, reason). "blocked" means no
        # subject-compatible article cleared 0.40; the threshold is NOT relaxed
        # for generated rows, which would defeat the point of generating them.
        sc, art, vd, _reason = R.match_row(kw, corpus, idf)
        if vd == "blocked" or art is None:
            rejected["no match"] += 1
            continue
        link = art.get("url")
        if not link:
            rejected["no destination"] += 1
            continue
        arch = infer_archetype(kw)
        row = {
            "keyword": kw, "volume": None, "cpc": None, "difficulty": None,
            # Generated rows have no search volume, so they sort BELOW every
            # researched row. They fill the tail; they do not displace.
            "priority": 1.0,
            "archetype": arch, "card_archetype": card_archetype(arch),
            "board": "The Sauna Shop", "board_id": "902690387751719051",
            "source_article": link, "source_title": art.get("title"),
            "link": link, "link_domain": D.domain_of(link),
            "source_domain": D.domain_of(link),
            "evidence_tier": "moderate", "dimensions": "1000x1500",
            "reuse_class": "evergreen", "min_repost_days": 120,
            "status": "queued", "id": f"pin-g{nid:04d}",
            "match_score": round(sc, 4), "match_confidence": vd,
            "cluster": art.get("blog") or "generated",
            "destination_reason": "generated: best corpus match",
            "source_data": None, "generated_at": dt.date.today().isoformat(),
        }
        # A card must SAY something. has_figures passes any non-quantitative
        # archetype trivially, so requiring figures means requiring the
        # archetype to be one that carries them -- otherwise the generator
        # refills the queue with cards that carry no numbers, undoing Round 9.
        if row["card_archetype"] not in QUANTITATIVE_ARCHETYPES:
            rejected["not quantitative"] += 1
            continue
        ok, _why = WO.has_figures(row)
        if not ok:
            rejected["no figures"] += 1
            continue
        appended.append(row)
        nid += 1
        if a.limit and len(appended) >= a.limit:
            break

    print(f"  appended    : {len(appended)}")
    for k, v in rejected.items():
        print(f"  rejected {k:15}: {v}")

    after = runway_report(rows + appended)
    print(f"\nrunway AFTER : {after['eligible_signatures']} eligible signatures "
          f"= {after['weeks']} weeks  [{after['level']}]")

    if a.write and appended:
        queue["items"] = rows + appended
        queue["count"] = len(queue["items"])
        queue["queued"] = sum(1 for r in queue["items"] if r["status"] == "queued")
        queue["blocked"] = sum(1 for r in queue["items"] if r["status"] == "blocked")
        queue["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        tmp = QUEUE.with_suffix(".tmp")
        tmp.write_text(json.dumps(queue, indent=1))
        tmp.replace(QUEUE)
        print(f"\nwrote {len(appended)} rows -> {QUEUE}")
    elif a.write:
        print("\nnothing to write")
    else:
        print("\n(report only — pass --write to append)")

    if after["level"] == "halt":
        print(f"\n🔴 BLOCKED: runway {after['weeks']} weeks is below {HALT_WEEKS}. "
              f"Refill the queue. Do NOT lower the match threshold or the "
              f"repost floor to manufacture rows.")
        return 2
    if after["level"] == "warn":
        print(f"\n⚠️  runway {after['weeks']} weeks is below {WARN_WEEKS}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
