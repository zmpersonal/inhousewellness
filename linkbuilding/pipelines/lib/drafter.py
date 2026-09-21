#!/usr/bin/env python3
"""
The drafter. Produces pitch drafts for HUMAN REVIEW. It cannot send, and
there is no code path in this module that touches a mailbox.

THE RULE THAT SHAPES EVERYTHING HERE: no novel claims. A draft may assert only
what an approved source already says. When answering an item well would need
something outside the approved sets, the item is flagged `needs_expert_input`
and NO DRAFT IS WRITTEN — not a hedged draft, not a draft with a gap in it.

That is not conservatism for its own sake. The whole project exists because the
previous system published things nobody had checked, and a drafter that
improvises around a missing claim is that failure with better prose.

SOURCES OF TRUTH, in order:
  data/claims.json            cited regime — every sentence traceable to a claim
  experts.json experience_set experience regime — his own practice, no citation
Anything else is not a source and cannot support a draft.
"""

import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
AFFILIATION = "InHouse Wellness (inhousewellness.com)"
WORD_LIMIT = 300


class DraftError(Exception):
    pass


# --------------------------------------------------------------------------
# §3 — read past the opening clause
# --------------------------------------------------------------------------
# Three of the corpus's tier-B items were never expert requests: a fertility
# forum that reads as a medical panel for one sentence and then asks for gift
# bags, and a listing seeking a plastic-surgery practice to host a writer for a
# free procedure. Both would have been drafted against on their first line.
#
# So the test is not "does this look medical" — it is "does this ask a person
# to say something". Solicitation vocabulary anywhere in the body disqualifies
# it, however the item opens.
_SOLICIT_PATTERNS = [
    (re.compile(r"\bgift\s+bag", re.I), "asks for gift bags"),
    (re.compile(r"\bgift\s+guide", re.I), "gift guide — asks for products"),
    (re.compile(r"\bseeking\s+(?:products|brands|companies|items|samples|"
                r"contributions|donations|sponsors)", re.I), "asks for products or sponsorship"),
    (re.compile(r"\b(?:product|sample)s?\s+for\s+(?:hands[- ]on\s+)?review", re.I),
     "asks for products to review"),
    (re.compile(r"\bhost(?:ed|ing)?\s+(?:a\s+)?(?:stay|writer|experience)", re.I),
     "asks to host a writer"),
    (re.compile(r"\bwilling\s+to\s+host\b", re.I), "asks a business to host"),
    (re.compile(r"\bcomplimentary\b", re.I), "offers or requests something complimentary"),
    (re.compile(r"\bsend\s+(?:us\s+)?(?:your\s+)?products?\b", re.I), "asks for products"),
    (re.compile(r"\bpress\s+kit", re.I), "asks for a press kit"),
    # Round 13: "looking to connect with fitness and wellness BRANDS interested
    # in having their PRODUCTS FEATURED" — a product solicitation that opens
    # like an editorial request and matched the experience set on "recovery".
    (re.compile(r"\bbrands?\s+interested\s+in", re.I), "solicits brands"),
    (re.compile(r"\b(?:products?|items?)\s+(?:to\s+be\s+)?featur(?:ed|ing)", re.I),
     "asks for products to feature"),
    (re.compile(r"\bhaving\s+their\s+products?\b", re.I), "asks brands for products"),
    (re.compile(r"\bno\s+cost\s+coverage\b", re.I), "offers coverage for product"),
]
# Evidence that a human is being asked to SAY something.
_COMMENT_PATTERNS = [
    re.compile(r"\b(?:looking|seeking|searching)\s+(?:for|to\s+(?:speak|talk|hear|interview))", re.I),
    re.compile(r"\b(?:comment|commentary|quote|quotes|insight|insights|perspective|"
               r"expertise|expert\s+input|weigh\s+in)\b", re.I),
    re.compile(r"\b(?:answer|respond\s+to)\s+(?:the\s+)?(?:following|below|these)?\s*questions?\b", re.I),
    re.compile(r"\bquestions?\s+(?:include|below|are)\b", re.I),
    re.compile(r"\b(?:interview|podcast\s+guest)\b", re.I),
]


def classify_query(text):
    """(is_query, reason). `not_a_query` items are never drafted against.

    DISQUALIFICATION REQUIRES POSITIVE EVIDENCE. The first version of this also
    demanded positive evidence that comment was being requested, and dropped
    four real requests for want of a phrase it recognised — including "I want
    to talk to experts about how common this is", which is as plain a request
    as the corpus contains. Absence of expected vocabulary is not evidence that
    the request is not there; it is the same missing-value failure this project
    keeps paying for, one layer up.

    So: solicitation vocabulary disqualifies. Everything else is a query, and
    an item with no recognisable comment phrasing is passed through flagged
    rather than dropped — a human reading one extra item costs nothing, and a
    silently discarded request costs the thing the project is for.
    """
    t = " ".join((text or "").split())
    for pattern, why in _SOLICIT_PATTERNS:
        if pattern.search(t):
            return False, why
    if not any(p.search(t) for p in _COMMENT_PATTERNS):
        return True, ("no standard comment phrasing found — passed through for "
                      "human reading rather than dropped")
    return True, "requests expert commentary"


# --------------------------------------------------------------------------
# source resolution — what may this draft stand on?
# --------------------------------------------------------------------------
def covering_claims(item_text, bank, modality_terms, outcome_terms):
    """Claim ids that actually cover the SUBJECT of the item.

    Coverage is deliberately strict and is NOT the same test as the filter's.
    A claim in this bank is a statement about a modality — sauna, heat, cold —
    and its outcome. An item it can source must therefore be ABOUT that
    modality. Matching on a claim's incidental vocabulary (`benefit`,
    `response`, `condition`, `improve`) would let a head-lice piece cite a
    Finnish sauna cohort, which is how a bank gets stretched.
    """
    hay = " ".join((item_text or "").split()).lower()
    if not any(t in hay for t in modality_terms):
        return []
    out = []
    for c in bank["claims"]:
        words = set(re.findall(r"[a-z]+", (c["claim"] + " " + c["hedge"]).lower()))
        if any(t in hay for t in modality_terms) and (
                {w for w in words if len(w) > 5} & set(re.findall(r"[a-z]{6,}", hay))):
            out.append(c["id"])
    return out


def covering_experience(item_text, experience_set):
    """Experience topics that cover the item. Empty set -> no coverage."""
    hay = " ".join((item_text or "").split()).lower()
    return [t for t in (experience_set or []) if t.lower() in hay]


# --------------------------------------------------------------------------
# draft assembly
# --------------------------------------------------------------------------
def _word_count(s):
    return len(re.findall(r"\S+", s or ""))


def assemble(body, credential_line, affiliation=AFFILIATION):
    """Journalists paste what they are given, so the answer comes FIRST and the
    credential line sits directly under it. Nothing is prefixed to it."""
    text = "%s\n\n— %s, %s" % (body.strip(), credential_line, affiliation)
    if _word_count(text) > WORD_LIMIT:
        raise DraftError("draft is %d words, over the %d-word limit the "
                         "platforms impose" % (_word_count(text), WORD_LIMIT))
    return text


def build(item, bank, experts, modality_terms, outcome_terms, body_writer=None):
    """Return a draft record. NEVER returns prose it cannot source.

    `body_writer(item, claims, topics)` supplies the answer text. It is passed
    only material already resolved from an approved source, so it has nothing
    to improvise from.
    """
    expert = experts["alptunaer"]
    text = item.get("query_text") or ""
    rec = {"source_key": item.get("source_key") or item.get("idx"),
           "outlet": item.get("outlet"), "deadline": item.get("deadline"),
           "platform": item.get("platform"),
           "reply_path": item.get("journalist_email"),
           "requires_manual": bool(item.get("requires_manual")),
           "requirement_mismatch": bool(item.get("journalist_restriction")),
           "requested_profession": item.get("journalist_restriction"),
           "source_claim_ids": [], "source_experience_topics": [],
           "framing": None, "draft": None, "needs_expert_input": False,
           "not_a_query": False, "reason": ""}

    is_query, why = classify_query(text)
    if not is_query:
        rec["not_a_query"] = True
        rec["reason"] = why
        return rec

    claim_ids = covering_claims(text, bank, modality_terms, outcome_terms)
    exp_topics = covering_experience(text, expert.get("experience_set"))
    rec["source_claim_ids"] = claim_ids
    rec["source_experience_topics"] = exp_topics

    if not claim_ids and not exp_topics:
        rec["needs_expert_input"] = True
        rec["reason"] = (
            "no approved source covers this. The claim bank is about sauna, "
            "heat and cold exposure; this item is not, and %s has no approved "
            "experience set to draw on instead. Answering would require a "
            "claim nobody has signed."
            % expert.get("name", "the expert"))
        return rec

    rec["framing"] = "published-evidence" if claim_ids else "clinical-experience"
    if body_writer is None:
        rec["needs_expert_input"] = True
        rec["reason"] = "sources resolved but no body writer supplied"
        return rec
    rec["draft"] = assemble(body_writer(item, claim_ids, exp_topics),
                            expert["credential_line"])
    return rec


def default_body_writer(item, claim_ids, exp_topics, bank=None):
    """Compose an answer from APPROVED MATERIAL ONLY.

    Every sentence below comes out of a claim's own fields — its statement, the
    hedge that must travel with it, and a citation that was verified against
    the live literature index. Nothing is generated about the medicine. That is
    why this is a template and not a paragraph someone wrote from knowledge:
    a writer with latitude is a writer who can add a sentence no one signed.
    """
    if not claim_ids:
        return ("Speaking from clinical practice rather than published work: "
                + "; ".join(exp_topics) + ".")
    by_id = {c["id"]: c for c in (bank or {}).get("claims", [])}
    parts = []
    for cid in claim_ids[:2]:
        c = by_id.get(cid)
        if not c:
            raise DraftError("claim %r is not in the bank" % cid)
        cite = (c.get("citations") or [{}])[0]
        stamp = ", ".join(x for x in (
            str(cite.get("year") or ""),
            "PMID %s" % cite["pmid"] if cite.get("pmid") else "") if x)
        parts.append("%s. %s%s" % (
            c["claim"].rstrip("."),
            c["hedge"].rstrip("."),
            " (%s)" % stamp if stamp else ""))
    return (". ".join(p.rstrip(".") for p in parts) + ".").replace("..", ".")


# ==========================================================================
# Round 13 — three regimes
# ==========================================================================
# claim bank        cited, pre-approved, signature pending
# experience        uncited BY DESIGN, approved by relayed confirmation
# verified_at_draft cited, but the citation is retrieved and checked WHEN THE
#                   DRAFT IS WRITTEN, because the bank cannot cover general
#                   medicine and the drafter's own knowledge is not a source
#
# His condition on the third is "accurate with modern medical advice". A model
# asserting something it believes does not satisfy that, however confident it
# sounds, so the enforcement is mechanical: an assertion without a resolved
# PMID or DOI and an exact stored title is DROPPED, not softened. Softening is
# how an unsourced claim survives review.
REGIMES = ("claim_bank", "experience", "verified_at_draft")
FRAMING_BY_REGIME = {"claim_bank": "published-evidence",
                     "experience": "clinical-experience",
                     "verified_at_draft": "verified-guideline"}
# Sources that carry more weight than a single study, preferred where they
# exist and recorded so a reviewer can see which kind was used.
GUIDELINE_BODIES = ("CDC", "AHA", "ACEP", "USPSTF", "NICE", "WHO", "FDA",
                    "Endocrine Society", "AACE", "AAD", "ACC", "IDSA")
_PMID_RE = re.compile(r"^\d{6,9}$")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


class UnverifiedAssertion(DraftError):
    pass


def assert_citation_resolved(cit):
    """Same gate claims.json uses: a resolved id and the EXACT returned title.

    `verified_at` is required and is the point of the regime — a citation
    carried over from a previous round was not verified at THIS draft time.
    """
    for field in ("title", "verified_at", "retrieved_via"):
        if not cit.get(field):
            raise UnverifiedAssertion("citation missing %r: %r" % (field, cit))
    pmid, doi = str(cit.get("pmid") or ""), str(cit.get("doi") or "")
    if not (_PMID_RE.match(pmid) or _DOI_RE.match(doi)):
        raise UnverifiedAssertion(
            "citation resolves to neither a PMID nor a DOI: %r. A citation "
            "that cannot be resolved is not a citation." % cit)
    if cit.get("source_type") not in ("guideline", "study"):
        raise UnverifiedAssertion(
            "citation %r must record source_type 'guideline' or 'study' — the "
            "regime prefers guidance and consensus statements over individual "
            "studies, and which was used is part of the record." % cit.get("title"))
    return True


def assert_assertions_verified(assertions, citations):
    """Every factual assertion maps to at least one verified citation."""
    by_id = {c["id"]: c for c in citations}
    for c in citations:
        assert_citation_resolved(c)
    for a in assertions:
        ids = a.get("citation_ids") or []
        if not ids:
            raise UnverifiedAssertion(
                "assertion has no citation and must be DROPPED, not softened: "
                "%r" % a.get("text", "")[:120])
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise UnverifiedAssertion("assertion cites unknown citation(s) %s"
                                      % missing)
    return True


def render_verified_body(assertions, citations):
    """Assertions in order, each trailing its resolved identifier."""
    by_id = {c["id"]: c for c in citations}
    out = []
    for a in assertions:
        marks = []
        for i in a["citation_ids"]:
            c = by_id[i]
            marks.append("PMID %s" % c["pmid"] if c.get("pmid")
                         else "doi:%s" % c["doi"])
        out.append("%s (%s)." % (a["text"].rstrip("."), "; ".join(marks)))
    return " ".join(out)


def load_experience(path=None):
    path = path or os.path.join(ROOT, "linkbuilding", "data", "experience.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if not doc.get("approved"):
        raise DraftError("experience set is not approved; it cannot source a draft")
    return doc


def experience_topics_for(item_text, experience):
    hay = " ".join((item_text or "").split()).lower()
    return [t for t in experience["topics"] if t in hay]


_EVIDENCE_QUESTION_RE = re.compile(
    r"\b(?:real\s+evidence|the\s+evidence|what\s+does\s+(?:the\s+)?"
    r"(?:current\s+)?research|studies\s+show|is\s+there\s+(?:any\s+)?evidence|"
    r"research\s+suggest|clinical\s+trials?|peer[- ]reviewed)\b", re.I)


def needs_citation(item_text):
    """True when the item asks an EVIDENCE question.

    This decides regime precedence in the one place it is genuinely ambiguous.
    The experience set is uncited by design and must never be presented as
    literature — so an item asking "is there real evidence" cannot be answered
    from it, even when its topic words match. Precedence is claim bank →
    experience → verified_at_draft, EXCEPT here, where an evidence question
    skips experience rather than dressing practice up as research.
    """
    return bool(_EVIDENCE_QUESTION_RE.search(item_text or ""))
