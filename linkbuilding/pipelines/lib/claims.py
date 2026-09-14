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
    bits = []
    if c.get("journal"):
        bits.append("*%s*" % c["journal"])
    if c.get("year"):
        bits.append(str(c["year"]))
    if c.get("n"):
        bits.append("n=%d" % c["n"])
    ident = "PMID %s" % c["pmid"] if c.get("pmid") else ""
    if c.get("doi"):
        ident += (", " if ident else "") + "doi:%s" % c["doi"]
    return "%s — %s (%s)" % (c["title"], ", ".join(bits) or "—", ident)


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
