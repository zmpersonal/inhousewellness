#!/usr/bin/env python3
"""
claims.py — load, validate, query and drift-check the claim bank.

The bank is the set of claims Dr. Timur Alptunaer has approved for attribution
in his name. `01_source` may assemble a pitch ONLY from these records. A claim
that is not in the bank cannot be pitched.

WHY THIS FILE RAISES INSTEAD OF WARNING
  His standing approval is conditional on claims being backed by medical
  science. A hallucinated citation attributed to a named physician in national
  health media is worse than producing nothing at all, and it is not
  recoverable by a correction. So every integrity check here is an exception,
  not a log line. There is no "clean it up and use it anyway" path.

  The verification gate was proven before the bank was built: a plausible but
  fabricated DOI (10.1001/jamainternmed.2031.99187) returns 404 from
  firecrawl_research_inspect_paper rather than a near-match. Fabrication is
  therefore detectable, which is what makes `revalidate` meaningful.

DRIFT CHECK
  Every citation stores the EXACT title returned by inspect_paper. revalidate()
  re-resolves each stored ID and compares. A mismatch means the stored record
  no longer describes the paper the ID points at — a retraction, a correction,
  a transcription error, or a swapped ID — and raises. This is the reason the
  bank stores structured citations rather than prose with a citation appended:
  prose cannot be re-checked automatically.

Usage
  claims.py validate                     # structural + citation integrity
  claims.py stats                        # tier and topic distribution
  claims.py query --topic sleep [--confidence strong]
  claims.py revalidate --resolved <f.json>   # drift check against re-resolved titles
  claims.py self-test
"""

import argparse, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # linkbuilding/
BANK = os.path.join(ROOT, "data", "claims.json")

CONFIDENCE = ("strong", "moderate", "preliminary")
EVIDENCE = ("prospective cohort", "RCT", "meta-analysis", "systematic review",
            "mechanistic", "animal", "case series", "review")
REQUIRED = ("id", "claim", "confidence", "evidence_type", "citations",
            "hedge", "do_not_say", "topics")

PMID_RE = re.compile(r"^\d{1,8}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


class ClaimBankError(Exception):
    """Any integrity failure. Never caught inside this module."""


def load(path=BANK):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate(doc)
    return doc


def _check_citation(claim_id, i, c):
    pmid, doi = (c.get("pmid") or "").strip(), (c.get("doi") or "").strip()
    if not pmid and not doi:
        raise ClaimBankError(
            "%s citation[%d]: no PMID and no DOI. A citation that cannot be "
            "resolved cannot be verified, and an unverifiable citation under a "
            "physician's name is the exact failure this bank exists to prevent."
            % (claim_id, i))
    if pmid and not PMID_RE.match(pmid):
        raise ClaimBankError("%s citation[%d]: malformed PMID %r" % (claim_id, i, pmid))
    if doi and not DOI_RE.match(doi):
        raise ClaimBankError("%s citation[%d]: malformed DOI %r" % (claim_id, i, doi))
    if not (c.get("title") or "").strip():
        raise ClaimBankError(
            "%s citation[%d]: no stored title. The title is what the drift "
            "check compares against; without it the citation can never be "
            "re-verified." % (claim_id, i))
    if c.get("verified_via") != "inspect_paper":
        raise ClaimBankError(
            "%s citation[%d]: verified_via is %r, not 'inspect_paper'. Every "
            "citation must have had its metadata retrieved, never written from "
            "memory." % (claim_id, i, c.get("verified_via")))
    if not (c.get("verified_at") or "").strip():
        raise ClaimBankError("%s citation[%d]: no verified_at date" % (claim_id, i))
    if "n" in c:
        n = c["n"]
        if n is not None and (not isinstance(n, int) or isinstance(n, bool) or n <= 0):
            raise ClaimBankError(
                "%s citation[%d]: n is %r. Sample size must be a positive integer "
                "or null. A literal 0 reads as '0 participants' to a clinician and "
                "would be silently formatted or filtered on downstream — use null "
                "for 'not stated'." % (claim_id, i, n))
    if "journal_source" in c:
        raise ClaimBankError(
            "%s citation[%d]: journal_source is retired. A journal name that needs "
            "a provenance caveat should not be displayed at all — set journal to "
            "null instead. DOI prefix 10.1001 covers JAMA, JAMA Internal Medicine, "
            "JAMA Cardiology and others, so deriving from it can name a journal the "
            "paper was never published in." % (claim_id, i))


def validate(doc):
    claims = doc.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ClaimBankError("bank contains no claims")
    seen = set()
    for c in claims:
        cid = c.get("id", "<no id>")
        for k in REQUIRED:
            if k not in c:
                raise ClaimBankError("%s: missing required field %r" % (cid, k))
        if cid in seen:
            raise ClaimBankError("duplicate claim id %r" % cid)
        seen.add(cid)
        if c["confidence"] not in CONFIDENCE:
            raise ClaimBankError("%s: confidence %r not in %s" % (cid, c["confidence"], CONFIDENCE))
        if c["evidence_type"] not in EVIDENCE:
            raise ClaimBankError("%s: evidence_type %r not in %s" % (cid, c["evidence_type"], EVIDENCE))
        if not c["citations"]:
            raise ClaimBankError("%s: no citations. Every claim needs at least one." % cid)
        if not (c.get("hedge") or "").strip():
            raise ClaimBankError(
                "%s: no hedge. The hedge travels with the claim; a claim "
                "without one is an unqualified medical assertion." % cid)
        if not c.get("do_not_say"):
            raise ClaimBankError(
                "%s: no do_not_say. The overclaim boundary is the part a "
                "physician's name most needs attached to it." % cid)
        if not c.get("topics"):
            raise ClaimBankError("%s: no topics" % cid)
        for i, cit in enumerate(c["citations"]):
            _check_citation(cid, i, cit)
    return True


def stats(doc):
    claims = doc["claims"]
    tiers, topics, evidence = Counter(), Counter(), Counter()
    for c in claims:
        tiers[c["confidence"]] += 1
        evidence[c["evidence_type"]] += 1
        for t in c["topics"]:
            topics[t] += 1
    total = len(claims)
    dominant = tiers.most_common(1)[0] if tiers else ("", 0)
    return {"total": total, "tiers": dict(tiers), "topics": dict(topics),
            "evidence": dict(evidence),
            "citations": sum(len(c["citations"]) for c in claims),
            "topic_areas": len(topics),
            "dominant_tier": dominant[0],
            "dominant_share": dominant[1] / total if total else 0}


def query(doc, topic=None, confidence=None, exclude_preliminary=False):
    out = []
    for c in doc["claims"]:
        if topic and topic not in c["topics"]:
            continue
        if confidence and c["confidence"] != confidence:
            continue
        if exclude_preliminary and c["confidence"] == "preliminary":
            continue
        out.append(c)
    return out


def _norm_title(t):
    """Compare titles on substance: case, punctuation and trailing periods
    vary between sources and are not drift."""
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def revalidate(doc, resolved):
    """Drift check.

    `resolved` maps a stored id (pmid:NNN or doi:...) to the title the research
    tool returns for it TODAY. Any stored citation whose title no longer
    matches raises. An id that resolves to nothing also raises — a citation
    that has stopped resolving is exactly as unusable as one that never did.
    """
    problems = []
    for c in doc["claims"]:
        for i, cit in enumerate(c["citations"]):
            keys = []
            if cit.get("pmid"):
                keys.append("pmid:%s" % cit["pmid"])
            if cit.get("doi"):
                keys.append("doi:%s" % cit["doi"])
            hit = next((k for k in keys if k in resolved), None)
            if hit is None:
                problems.append("%s citation[%d]: none of %s could be re-resolved"
                                % (c["id"], i, keys))
                continue
            now = resolved[hit]
            if now is None:
                problems.append("%s citation[%d]: %s no longer resolves"
                                % (c["id"], i, hit))
            elif _norm_title(now) != _norm_title(cit["title"]):
                problems.append(
                    "%s citation[%d]: TITLE DRIFT on %s\n    stored: %s\n    now:    %s"
                    % (c["id"], i, hit, cit["title"], now))
    if problems:
        raise ClaimBankError("drift check failed (%d):\n  %s"
                             % (len(problems), "\n  ".join(problems)))
    return True


def resolution_worklist(doc):
    """Every id the drift check needs re-resolved, for the agent to feed to
    inspect_paper. The library never calls the network itself."""
    ids = []
    for c in doc["claims"]:
        for cit in c["citations"]:
            if cit.get("pmid"):
                ids.append("pmid:%s" % cit["pmid"])
            elif cit.get("doi"):
                ids.append("doi:%s" % cit["doi"])
    return sorted(set(ids))


# --------------------------------------------------------------------------

# ==========================================================================
# Round 10 — the filter's vocabulary must be derived FROM the bank
# ==========================================================================
# Round 9 found the pipeline printing "modality ['infrared'] named; the claim
# bank covers this directly" for a term appearing in zero of 30 claims. The
# filter's term lists and the bank were maintained independently and nothing
# reconciled them, so the filter could — and did — promise coverage that did
# not exist. Had the bank been signed and a drafter existed, that row would
# have been pitched under a physician's name with nothing to say.
#
# The fix is structural: a term is valid ONLY if some claim backs it, and
# backing is derived from the claim's own words rather than asserted
# elsewhere.
#
# WHAT COUNTS AS BACKING, and what deliberately does not:
#
#   claim text + hedge + citation titles   YES — what the claim asserts
#   do_not_say                             NO  — what it FORBIDS. `cold plunge`
#                                                appears in the bank only here
#                                                ("Cold plunges improve insulin
#                                                sensitivity" is a do-not-say).
#                                                Matching on it would route an
#                                                item to a claim that exists to
#                                                stop that sentence being said.
#   topics                                 NO  — an index label, not a
#                                                statement. `hydration` is a
#                                                topic on two claims whose text
#                                                never mentions hydration.
#
# Both exclusions were found by measurement, not guessed: counting them as
# backing hid 6 orphans.

# Research-methodology vocabulary. Excluded from derived concepts because it
# appears in every claim and would match every query. This is a stoplist of
# words about HOW evidence was gathered — it is deliberately not a domain
# term list, because a domain term list maintained here is the bug.
_METHOD_WORDS = {
    "study", "studies", "trial", "trials", "randomised", "randomized",
    "participants", "participant", "evidence", "small", "large", "adults",
    "adult", "men", "women", "people", "person", "cohort", "prospective",
    "observational", "review", "meta", "analysis", "systematic", "crossover",
    "controlled", "sham", "measured", "measuring", "measures", "found",
    "findings", "finding", "showed", "shown", "association", "associated",
    "compared", "comparison", "effect", "effects", "outcome", "outcomes",
    "single", "session", "sessions", "week", "weeks", "year", "years",
    "month", "months", "hour", "hours", "minute", "minutes", "significant",
    "results", "result", "data", "reported", "report", "among", "versus",
    "following", "during", "after", "before", "within", "between", "across",
    "would", "could", "which", "their", "there", "these", "those", "than",
    "that", "this", "with", "from", "have", "been", "were", "was", "not",
    "and", "the", "for", "one", "two", "does", "did", "has", "had", "its",
    "into", "onto", "over", "under", "more", "most", "less", "least", "same",
    "other", "others", "also", "only", "very", "much", "many", "some", "any",
    "first", "second", "third", "nine", "eight", "seven", "six", "five",
    "four", "three", "conclusion", "conclusions", "concluded", "suggest",
    "suggests", "suggested", "indicate", "indicates", "appears", "appear",
    "clinical", "clinically", "medical", "health", "healthy", "patients",
    "patient", "population", "populations",
}
# Prefixes that REVERSE meaning. `dehydration` is not a variant of
# `hydration`; it is the opposite state, and a claim about staying hydrated
# does not back a query about dehydration.
_REVERSING_PREFIXES = ("de", "non", "un", "anti", "dis", "counter")
# Function words. A blanket minimum length was tried first and was WRONG: it
# silently dropped `brown fat`, because "fat" is three characters and is also
# the entire concept. Length is not a proxy for meaning.
_FUNCTION_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "for",
    "from", "had", "has", "have", "her", "his", "how", "in", "is", "it", "its",
    "may", "might", "no", "nor", "not", "of", "on", "or", "our", "out", "per",
    "she", "so", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "to", "up", "was", "way", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "you", "your", "if", "into", "onto", "over",
    "under", "about", "above", "below", "again", "all", "also", "any", "both",
    "each", "few", "more", "most", "much", "only", "other", "own", "same",
    "some", "very", "just", "one", "two",
}


def _positive_text(claim):
    """What the claim ASSERTS. Never do_not_say, never topics."""
    return " ".join([claim.get("claim", ""), claim.get("hedge", "")] +
                    [c.get("title", "") for c in claim.get("citations") or []]).lower()


def _stem(word):
    """Conservative stem: enough to tie inflammation/inflammatory,
    depression/depressive, cognition/cognitive. Never shorter than 5 chars, so
    it cannot collapse unrelated words."""
    w = word.lower().strip("-")
    # "-atory" and "-ory" are here because inflammation/inflammatory is exactly
    # the tie this exists to make, and the first version missed it.
    for suf in ("atory", "ational", "ations", "ation", "ives", "ive", "ory",
                "ing", "ions", "ion", "ies", "ers", "er", "ed", "es", "s",
                "al", "ic", "ity"):
        if w.endswith(suf) and len(w) - len(suf) >= 5:
            return w[:-len(suf)]
    return w


def _canon(phrase):
    """Canonical form: hyphens and whitespace are the same separator.

    Generating hyphen permutations was tried first and fails on partially
    hyphenated phrases — 'cold-water immersion' has one hyphen and one space,
    which no whole-string swap produces, so a term the bank uses verbatim read
    as an orphan. Normalising both sides is smaller and cannot miss a case.
    """
    return re.sub(r"[-\s]+", " ", (phrase or "").lower()).strip()


def _variants(phrase):
    """A claim's phrase plus its plural/singular partner, canonicalised."""
    p = _canon(phrase)
    out = {p}
    if not p.endswith("s"):
        out.add(p + "s")
    elif len(p) > 4:
        out.add(p[:-1])
    return {v for v in out if v}


def derive_synonyms(claim, max_n=3):
    """The concept set a claim supports, derived from its own words.

    n-grams of its assertion text, minus methodology vocabulary, plus
    orthographic variants. Nothing semantic is invented here: if the claim
    never mentions light, no amount of derivation reaches `infrared`.
    """
    text = _positive_text(claim)
    # Hyphenated compounds are tokenised BOTH ways. "heat acclimation-induced"
    # gives one token under a naive split, so the bigram "heat acclimation"
    # never forms and a backed term reads as an orphan. That is how this
    # round's first orphan count came out at 39% instead of the truth.
    text = text.replace("-", " - ")
    toks = [t for t in re.findall(r"[a-z][a-z]*", text)]
    concepts = set()
    for n in range(1, max_n + 1):
        for i in range(len(toks) - n + 1):
            gram = toks[i:i + n]
            if any(t in _METHOD_WORDS or t in _FUNCTION_WORDS for t in gram):
                continue
            concepts |= _variants(" ".join(gram))
    return sorted(concepts)


def claim_stems(claim):
    """Stems of every content word the claim asserts. Used for the
    morphological tie only — inflammation to inflammatory, and no further."""
    return {_stem(t) for t in re.findall(r"[a-z][a-z]*",
                                        _positive_text(claim).replace("-", " "))
            if t not in _METHOD_WORDS and t not in _FUNCTION_WORDS}


def _reversed_form(term, stems):
    """True if `term` is a reversing-prefix form of a concept the claim uses.

    The bare prefix test was wrong: it flagged `depression` because the word
    starts with "de", and blocked a legitimate tie to `depressive`. A prefix
    only reverses something if the something is actually there — so the
    remainder has to be a stem the claim itself uses. `dehydration` minus "de"
    is `hydration`, and is a reversal only in a claim that talks about
    hydration.
    """
    head = term.split()[0]
    for pfx in _REVERSING_PREFIXES:
        if head.startswith(pfx) and len(head) - len(pfx) >= 5:
            if _stem(head[len(pfx):]) in stems:
                return True
    return False


def backing_claims(term, doc):
    """Claim ids that back `term`, and HOW. Returns (ids, how)."""
    t = _canon(term)
    exact, morph = [], []
    for c in doc["claims"]:
        syns = set(derive_synonyms(c))
        if t in syns:
            exact.append(c["id"])
            continue
        # single-word morphological tie only; multi-word terms must be exact.
        if " " not in t:
            stems = claim_stems(c)
            if _stem(t) in stems and not _reversed_form(t, stems):
                morph.append(c["id"])
    if exact:
        return exact, "exact"
    if morph:
        return morph, "morphological"
    return [], "none"


def reconcile(terms, doc):
    """{term: {'claims': [...], 'how': ...}} plus the orphan list."""
    out, orphans = {}, []
    for t in sorted(terms):
        ids, how = backing_claims(t, doc)
        out[t] = {"claims": ids, "how": how}
        if not ids:
            # why it is an orphan, which decides what the human has to do
            neg = [c["id"] for c in doc["claims"]
                   if t in " ".join(c.get("do_not_say") or []).lower()]
            top = [c["id"] for c in doc["claims"]
                   if t in " ".join(c.get("topics") or []).lower()]
            out[t]["do_not_say_only"] = neg
            out[t]["topic_label_only"] = top
            orphans.append(t)
    return out, orphans


def assert_no_orphans(terms, doc):
    """RAISES on any clinical term with no backing claim.

    This is the Round 10 gate. It does not warn: a filter term with no claim
    behind it is a promise the bank cannot keep, and the pipeline printed
    exactly that promise for four days.
    """
    table, orphans = reconcile(terms, doc)
    if orphans:
        lines = []
        for t in orphans:
            why = "no claim mentions it"
            if table[t]["do_not_say_only"]:
                why = ("appears ONLY in do_not_say on %s — matching it would "
                       "route to a claim that forbids saying it"
                       % table[t]["do_not_say_only"])
            elif table[t]["topic_label_only"]:
                why = ("appears ONLY as a topic label on %s — an index entry, "
                       "not a statement" % table[t]["topic_label_only"])
            lines.append("  %-22s %s" % (t, why))
        raise ClaimBankError(
            "ORPHANED CLINICAL TERMS (%d of %d) — every match term must resolve "
            "to a claim:\n%s\nThese are removed from the filter, not fixed by "
            "adding claims: the bank is a reviewed artifact and writing into it "
            "outside the physician's process defeats its purpose."
            % (len(orphans), len(terms), "\n".join(lines)))
    return table


def synonym_index(doc):
    """{claim_id: [concepts]} — the sidecar written to disk.

    Kept BESIDE claims.json rather than inside it: the bank is out for
    signature and its rendered PDF must keep matching the file that was sent.
    Every entry is keyed to a live claim id and regenerated from claim text, so
    it cannot drift into holding a term no claim supports — which is the whole
    bug this closes.
    """
    return {c["id"]: derive_synonyms(c) for c in doc["claims"]}


def cmd_synonyms(_a):
    """Reconcile the pipeline's clinical vocabulary against the bank."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE)))
    doc = load()
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "src01", os.path.join(os.path.dirname(HERE), "01_source.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    terms = mod.CANDIDATE_MODALITY_TERMS | mod.CANDIDATE_OUTCOME_TERMS
    table, orphans = reconcile(terms, doc)
    print("%d candidate clinical terms | %d backed | %d ORPHANED"
          % (len(terms), len(terms) - len(orphans), len(orphans)))
    for t in orphans:
        r = table[t]
        why = ("ONLY in do_not_say (%s)" % ",".join(r["do_not_say_only"])
               if r["do_not_say_only"] else
               "ONLY a topic label (%s)" % ",".join(r["topic_label_only"])
               if r["topic_label_only"] else "no claim mentions it")
        print("  ORPHAN  %-22s %s" % (t, why))
    try:
        assert_no_orphans(terms, doc)
    except ClaimBankError as e:
        print("\n%s" % e, file=sys.stderr)
        return 3
    return 0


def cmd_validate(_a):
    doc = load()
    s = stats(doc)
    print("bank valid: %d claims, %d citations, %d topic areas"
          % (s["total"], s["citations"], s["topic_areas"]))
    return 0


def cmd_stats(_a):
    doc = load()
    s = stats(doc)
    print("claims: %d   citations: %d   topic areas: %d" % (s["total"], s["citations"], s["topic_areas"]))
    print("\nconfidence tiers:")
    for t in CONFIDENCE:
        n = s["tiers"].get(t, 0)
        print("  %-12s %2d  %5.1f%%" % (t, n, 100.0 * n / s["total"]))
    if s["dominant_share"] > 0.8:
        print("\nSTOP CONDITION: %.0f%% of claims are '%s' (>80%%). A bank where "
              "everything is one tier is a bank nobody checked."
              % (100 * s["dominant_share"], s["dominant_tier"]))
        return 3
    print("\nevidence types:")
    for k, v in sorted(s["evidence"].items(), key=lambda x: -x[1]):
        print("  %-20s %d" % (k, v))
    print("\ntopics:")
    for k, v in sorted(s["topics"].items(), key=lambda x: -x[1]):
        print("  %-24s %d" % (k, v))
    return 0


def cmd_query(a):
    doc = load()
    for c in query(doc, a.topic, a.confidence, a.exclude_preliminary):
        print("[%s] %s" % (c["confidence"], c["id"]))
        print("   %s" % c["claim"])
        print("   hedge: %s" % c["hedge"])
    return 0


def cmd_revalidate(a):
    doc = load()
    with open(a.resolved, encoding="utf-8") as fh:
        resolved = json.load(fh)
    revalidate(doc, resolved)
    print("drift check passed: %d citations still resolve to their stored titles"
          % sum(len(c["citations"]) for c in doc["claims"]))
    return 0


def cmd_worklist(_a):
    print("\n".join(resolution_worklist(load())))
    return 0


REVIEW = os.path.join(ROOT, "reports", "claim-bank-review.md")

TOPIC_GROUPS = [
    ("Heat and cardiovascular outcomes", ["cardiovascular", "blood-pressure", "vascular-function"]),
    ("Heat and mortality", ["mortality"]),
    ("Heat and cognition", ["cognition"]),
    ("Heat and sleep", ["sleep"]),
    ("Heat shock response", ["heat-shock"]),
    ("Heat and mood", ["mood"]),
    ("Cold and metabolic markers", ["metabolic"]),
    ("Cold, recovery and its limits", ["recovery", "hypertrophy", "contrast"]),
    ("Hydration and body mass", ["hydration", "weight"]),
    ("Safety, contraindications and who should not", ["safety", "contraindications", "pregnancy", "alcohol", "children"]),
]


def _cite_line(c):
    """Journal is shown only when the research index actually supplied it.
    It does not, for this corpus, so the DOI stands alone as the identifier —
    absent beats wrong. Sample size renders as 'not stated' rather than 0."""
    bits = []
    if c.get("journal"):
        bits.append("*%s*" % c["journal"])
    if c.get("year"):
        bits.append(str(c["year"]))
    bits.append("n=%d" % c["n"] if c.get("n") else "sample size not stated")
    ident = "PMID %s" % c["pmid"] if c.get("pmid") else ""
    if c.get("doi"):
        ident += (", " if ident else "") + "doi:%s" % c["doi"]
    return "%s — %s (%s)" % (c["title"], ", ".join(bits), ident)


def render_review(doc):
    claims = doc["claims"]
    s = stats(doc)
    prelim = [c for c in claims if c["confidence"] == "preliminary"]
    L = []
    A = L.append
    A("# Claim bank — for review by Timur Alptunaer, MD")
    A("")
    A("Prepared %s · %d claims · %d citations · version %s"
      % (doc["created"], s["total"], s["citations"], doc["version"]))
    A("")
    A("## What you are being asked to approve")
    A("")
    A("These are the only claims that may be attributed to you in journalist")
    A("pitches. A claim that is not on this list cannot be pitched — that is")
    A("enforced in code, not by anyone remembering.")
    A("")
    A("Approving this bank means: **standing attribution of these specific claims,")
    A("with their hedges attached, without you reviewing each individual pitch.**")
    A("You are not approving a topic area or a general endorsement of sauna and")
    A("cold exposure. You are approving these sentences.")
    A("")
    A("Each claim carries a **hedge** that must travel with it, and a")
    A("**do-not-say** list of overclaims it must never be stretched into. If you")
    A("strike a claim, it leaves the bank. If you rewrite a hedge, the new wording")
    A("is what ships.")
    A("")
    A("**Every citation below was retrieved from the live literature index, not")
    A("written from memory.** Titles are stored exactly as returned and are")
    A("re-checked automatically; if a stored citation stops matching its")
    A("identifier, the bank fails closed rather than pitching it.")
    A("")
    A("| | |")
    A("|---|---|")
    for t in CONFIDENCE:
        n = s["tiers"].get(t, 0)
        A("| %s | %d (%.0f%%) |" % (t, n, 100.0 * n / s["total"]))
    A("")
    A("---")
    A("")
    A("## Read this first — the %d `preliminary` claims" % len(prelim))
    A("")
    A("These rest on mechanistic, small or single-study evidence. They are")
    A("grouped here so you can **strike the whole tier in one decision** if you")
    A("would rather not have early-stage findings attributed to you at all.")
    A("")
    for c in prelim:
        A("- **`%s`** — %s" % (c["id"], c["claim"]))
        A("  - *Hedge:* %s" % c["hedge"])
        A("  - *Evidence:* %s" % c["evidence_type"])
    A("")
    A("Strike the tier: ☐   Keep with hedges: ☐   Decide individually below: ☐")
    A("")
    A("---")
    A("")
    seen = set()
    for heading, keys in TOPIC_GROUPS:
        group = [c for c in claims
                 if any(k in c["topics"] for k in keys) and c["id"] not in seen]
        if not group:
            continue
        for c in group:
            seen.add(c["id"])
        A("## %s" % heading)
        A("")
        for c in group:
            A("### `%s` · %s · %s" % (c["id"], c["confidence"], c["evidence_type"]))
            A("")
            A("> %s" % c["claim"])
            A("")
            A("**Hedge that must travel with it.** %s" % c["hedge"])
            A("")
            A("**Must never be stretched into:**")
            for d in c["do_not_say"]:
                A("- \u201c%s\u201d" % d)
            A("")
            A("**Citations**")
            for cit in c["citations"]:
                A("- %s" % _cite_line(cit))
            A("")
            A("Approve ☐   Approve with edits ☐   Strike ☐")
            A("")
        A("---")
        A("")
    left = [c for c in claims if c["id"] not in seen]
    if left:
        A("## Other")
        A("")
        for c in left:
            A("### `%s` · %s" % (c["id"], c["confidence"]))
            A("> %s" % c["claim"])
            A("")
    A("## Gaps — deliberately not filled")
    A("")
    A("These were searched and left empty rather than supported with weaker")
    A("evidence relabelled as strong:")
    A("")
    A("- **Sauna and sleep specifically.** The usable pooled evidence is for warm")
    A("  baths and showers before bed, not saunas. The sleep claims say so.")
    A("- **Cold exposure and immune function.** Popular topic, no human evidence")
    A("  found at a standard worth attaching a physician's name to.")
    A("- **Sauna and detoxification.** Supportable only from marketing material.")
    A("  Left out entirely, and named in the do-not-say lists.")
    A("- **Product comparisons.** No head-to-head trials exist between the")
    A("  equipment categories the store sells, so no comparative claim is offered.")
    A("")
    A("## What this document cannot tell you")
    A("")
    A("**Sample size is missing for most citations, and journal name for all of")
    A("them.** This is a limitation of the source, not an oversight.")
    A("")
    A("The research index returns title, authors, identifiers, dates and abstract.")
    A("It returns no journal field, and full text was unavailable for every paper")
    A("in this bank, so sample sizes could not be read out of article bodies. The")
    A("%d citations showing a count are those where the figure appears verbatim in" % sum(
        1 for c in doc["claims"] for cit in c["citations"] if cit.get("n")))
    A("the retrieved abstract. The rest read *sample size not stated* — that means")
    A("not stated, not zero, and it was not inferred, summed from subgroups, or")
    A("recalled from memory.")
    A("")
    A("Journal name was deliberately dropped rather than derived from the DOI")
    A("prefix: prefix `10.1001` covers JAMA, JAMA Internal Medicine and JAMA")
    A("Cardiology alike, so deriving it risks naming a journal a paper was never")
    A("published in. Every DOI below resolves to the paper of record — please use")
    A("it where the venue matters to your judgement.")
    A("")
    A("## Where the evidence genuinely disagrees")
    A("")
    A("`safety-pregnancy-01` and `safety-pregnancy-02` point in different")
    A("directions, and both are in the bank on purpose. The conservative reading")
    A("governs in both hedges. If you would rather drop the second entirely,")
    A("striking it loses nothing the first does not already cover.")
    A("")
    A("`heat-vascular-limits-01` records a **null** randomised result in coronary")
    A("artery disease alongside the positive observational findings. It is")
    A("included because a source who volunteers the trial that did not work is")
    A("more credible than one who does not.")
    A("")
    A("---")
    A("")
    A("## Sign-off")
    A("")
    A("I approve the claims marked above for standing attribution to me in media")
    A("pitches, with their hedges intact, without per-pitch review. Claims I have")
    A("struck are removed from the bank and cannot be pitched.")
    A("")
    A("Name: ______________________  Date: ____________")
    A("")
    A("Signature: _________________________________")
    A("")
    A("_Re-approval is required if any claim text or hedge changes. The bank")
    A("records approval status; until it is signed it reads `awaiting_review`._")
    return "\n".join(L) + "\n"


def cmd_report(_a):
    doc = load()
    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    with open(REVIEW, "w", encoding="utf-8") as fh:
        fh.write(render_review(doc))
    print("wrote %s" % os.path.relpath(REVIEW, ROOT))
    return 0


def cmd_self_test(_a):
    failures = []

    def check(name, cond):
        print("  %s %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    def raises(fn):
        try:
            fn(); return False
        except ClaimBankError:
            return True

    good = {"id": "t-1", "claim": "c", "confidence": "strong",
            "evidence_type": "prospective cohort",
            "citations": [{"pmid": "25705824", "doi": "10.1001/jamainternmed.2014.8187",
                           "title": "Association between sauna bathing and fatal cardiovascular and all-cause mortality events.",
                           "year": 2015, "verified_via": "inspect_paper",
                           "verified_at": "2026-09-14"}],
            "hedge": "h", "do_not_say": ["x"], "topics": ["heat"]}
    check("valid claim passes", validate({"claims": [good]}))

    print("self-test: citation integrity raises")
    def drop(field, from_citation=True):
        import copy
        c = copy.deepcopy(good)
        (c["citations"][0] if from_citation else c).pop(field, None)
        return lambda: validate({"claims": [c]})
    def blank_ids():
        import copy
        c = copy.deepcopy(good)
        c["citations"][0]["pmid"] = ""; c["citations"][0]["doi"] = ""
        return lambda: validate({"claims": [c]})
    check("no PMID and no DOI raises", raises(blank_ids()))
    check("missing title raises", raises(drop("title")))
    check("missing verified_at raises", raises(drop("verified_at")))
    check("missing hedge raises", raises(drop("hedge", False)))
    check("missing do_not_say raises", raises(drop("do_not_say", False)))

    def bad(field, value, in_cit=False):
        import copy
        c = copy.deepcopy(good)
        (c["citations"][0] if in_cit else c)[field] = value
        return lambda: validate({"claims": [c]})
    check("malformed DOI raises", raises(bad("doi", "not-a-doi", True)))
    check("malformed PMID raises", raises(bad("pmid", "abc123", True)))
    check("verified_via other than inspect_paper raises",
          raises(bad("verified_via", "from_memory", True)))
    check("unknown confidence tier raises", raises(bad("confidence", "certain")))
    check("empty citations raises", raises(bad("citations", [])))

    print("self-test: n and journal provenance")
    check("n=0 sentinel raises", raises(bad("n", 0, True)))
    check("negative n raises", raises(bad("n", -5, True)))
    check("n as string raises", raises(bad("n", "2315", True)))
    check("n=null accepted (not stated)", validate({"claims": [dict(good,
          citations=[dict(good["citations"][0], n=None)])]}))
    check("positive n accepted", validate({"claims": [dict(good,
          citations=[dict(good["citations"][0], n=2315)])]}))
    check("retired journal_source raises", raises(bad("journal_source", "derived_from_doi_prefix", True)))
    print("  -- rendering --")
    check("null journal is omitted, not printed as 'None'",
          "None" not in _cite_line({"title": "T", "year": 2015, "journal": None,
                                    "n": None, "doi": "10.1/x"}))
    check("null n renders as 'not stated', never 0",
          "not stated" in _cite_line({"title": "T", "year": 2015, "journal": None,
                                      "n": None, "doi": "10.1/x"}))
    check("real n renders as a count",
          "n=16" in _cite_line({"title": "T", "year": 2019, "journal": None,
                                "n": 16, "doi": "10.1/x"}))

    print("self-test: drift check")
    doc = {"claims": [good]}
    title = good["citations"][0]["title"]
    check("matching title passes",
          revalidate(doc, {"pmid:25705824": title}))
    check("title differing only by case/punctuation is NOT drift",
          revalidate(doc, {"pmid:25705824": title.upper().replace(".", "")}))
    corrupted = "Association between sauna bathing and fatal respiratory disease events."
    check("CORRUPTED title raises drift",
          raises(lambda: revalidate(doc, {"pmid:25705824": corrupted})))
    check("id that no longer resolves raises",
          raises(lambda: revalidate(doc, {"pmid:25705824": None})))
    check("id absent from resolution set raises",
          raises(lambda: revalidate(doc, {})))
    check("worklist lists the id once",
          resolution_worklist(doc) == ["pmid:25705824"])

    print()
    if failures:
        print("SELF-TEST FAILED: %d" % len(failures)); return 1
    print("SELF-TEST PASSED"); return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("synonyms").set_defaults(fn=cmd_synonyms)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    q = sub.add_parser("query"); q.add_argument("--topic"); q.add_argument("--confidence")
    q.add_argument("--exclude-preliminary", action="store_true"); q.set_defaults(fn=cmd_query)
    r = sub.add_parser("revalidate"); r.add_argument("--resolved", required=True)
    r.set_defaults(fn=cmd_revalidate)
    sub.add_parser("worklist").set_defaults(fn=cmd_worklist)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("self-test").set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()


def _stem_tokens(phrase):
    return tuple(_stem(t) for t in _canon(phrase).split() if t)


def expand_terms(terms, doc):
    """Surface forms the BANK actually uses for each backed term.

    This is the "match on concept, not keyword" step, and it is deliberately
    anchored rather than open. A claim's raw derived concept set contains
    `actual`, `days` and `damages`; matching on those would fire on anything.
    So a claim phrase is admitted only when it CONTAINS every stem of a term
    that is already backed:

        sauna              -> finnish sauna, sauna bathing, ...
        hyperthermia       -> whole body hyperthermia
        heat exposure      -> (a phrase must carry both heat AND exposure)

    `passive heating` therefore does NOT enter via `heat exposure`, and
    `light-based skin treatments` does not enter at all, because no claim
    mentions light. Widening stops where the bank stops.

    Returns {surface_form: {"term": canonical curated term, "claims": [...]}}.
    """
    out = {}
    backed = {t: backing_claims(t, doc)[0] for t in terms}
    backed = {t: ids for t, ids in backed.items() if ids}
    per_claim = {c["id"]: set(derive_synonyms(c)) for c in doc["claims"]}
    # Redundancy is tested against EVERY backed anchor, not just the one that
    # produced the phrase. `sauna bathing` was generated via the plural anchor
    # `saunas`, does not contain that string, and so survived a naive check —
    # while being unable to match any text the singular `sauna` would miss.
    anchors = {_canon(t) for t in backed}
    for term, ids in backed.items():
        want = _stem_tokens(term)
        out.setdefault(_canon(term), {"term": _canon(term), "claims": ids})
        for cid in ids:
            for phrase in per_claim[cid]:
                ptoks = _stem_tokens(phrase)
                if not all(w in ptoks for w in want):
                    continue
                # Drop forms that merely CONTAIN the anchor. "finnish sauna"
                # cannot match text that "sauna" would not already match, so
                # keeping it inflates the index without changing one verdict.
                # What survives is the forms the anchor would MISS —
                # `cognitive` for `cognition`, `depressive` for `depression`,
                # `inflammatory` for `inflammation`. That is the whole yield of
                # this step, and it is three concepts, not two hundred.
                if any(a in phrase for a in anchors):
                    continue
                e = out.setdefault(phrase, {"term": _canon(term), "claims": []})
                if cid not in e["claims"]:
                    e["claims"].append(cid)
    return out
