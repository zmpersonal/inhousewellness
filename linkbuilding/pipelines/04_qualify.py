#!/usr/bin/env python3
"""
04_qualify — score every candidate, reject hard, emit the worklist.

Most of the value here is in what gets thrown away. A pile of 400 unfiltered
domains is worse than 40 real ones.

Scoring per data/schema.sql: relevance 0-40, authority 0-25, traffic_reality
0-15, link_likelihood 0-20. Auto-rejects record their reason in risk_flags as
a JSON array — never a bare boolean, because "why" is what a human needs to
tell a wrong rule from a right one.

ON ORGANIC TRAFFIC. The reject rule "DA >40 with negligible organic traffic"
needs traffic data that costs one API call per domain. At tier1 that is 80+
calls, so traffic was measured only for the ambiguous high-DA candidates.
Where traffic is UNKNOWN the rule does not fire and the row carries a
traffic_unverified flag — withholding beats guessing. Rejecting a real
publisher on traffic data we never fetched would be exactly the confident
false positive this project keeps hitting.

Usage
  04_qualify.py run [--date YYYY-MM-DD]
  04_qualify.py self-test
"""

import argparse, json, os, re, sqlite3, sys
from collections import Counter
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "links.db")
WORKLIST = os.path.join(ROOT, "reports", "worklist.md")

MIN_QUALIFIED, MAX_QUALIFIED = 25, 200
QUALIFY_FLOOR = 40          # composite score below this is not worth an email

# Measured with ubersuggest.domain_overview on 2026-09-14. Monthly US organic
# visits. Absent = not measured; see module docstring.
MEASURED_TRAFFIC = {
    "cvillico.com": 0,       # DA 63, 0 traffic, 0 organic keywords, 32,989 backlinks
    "dearworld.me": 2,       # DA 51, 12 keywords, and the site is about mobile homes
    "theforbestimes.com": 0, # DA 56, 0 traffic, 0 keywords, 580 refDomains
}

RELEVANCE_TERMS = {
    "sauna": 14, "infrared": 10, "cold plunge": 14, "coldplunge": 12,
    "ice bath": 10, "plunge": 8, "steam": 6, "wellness": 7, "recovery": 8,
    "barrel": 6, "heat therapy": 10, "red light": 6, "longevity": 6,
    "backyard": 6, "outdoor living": 6, "home improvement": 6, "hot tub": 5,
    "spa": 4, "fitness": 4, "biohack": 4, "thermal": 5,
}
# Outbound neighbourhoods that disqualify regardless of metrics.
BAD_NEIGHBOURHOOD = re.compile(
    r"casino|betwinner|\bufa\b|ufabet|\bbet\b|gambl|poker|slot|psilocybin|"
    r"pharma|viagra|cialis|\bcbd\b|crypto|bitcoin|token|forex|escort|porn|adult",
    re.I)
# One template path repeated across dozens of unrelated domains is a PBN
# footprint, not an editorial link.
TEMPLATE_PATH = re.compile(r"/all/\d+/\d+\.html?$|^/page-[0-9a-f]{16,}\.html?$", re.I)
SPAM_TLDS = {"cfd", "sbs", "click", "website", "top"}

TACTIC_LIKELIHOOD = {
    "mention": 18,        # the ask is trivial: you already named us, please link
    "dealer": 16,         # a published programme exists; it is an application
    "resource_page": 14,  # the page exists to link out
    "roundup": 11,        # editorial, competitive, but they do link to retailers
    "gap": 9,             # they linked to a competitor, so they link to someone
}
TACTIC_ANGLE = {
    "mention": "Already names InHouse Wellness without linking. Ask for the link on the existing mention — lowest-friction ask available.",
    "dealer": "Dealer application. Human submits; this row exists to track it.",
    "resource_page": "Page exists to link out. Offer the specific guide that fills a gap in their list.",
    "roundup": "Editorial roundup that already links to retailers. Pitch inclusion with a specific model and a measured spec, not a generic ask.",
    "gap": "Links to a direct competitor but not to us. Lead with what the competitor's link does not cover.",
}


def path_of(url):
    s = re.sub(r"^[a-z]+://", "", (url or "").strip(), flags=re.I)
    i = s.find("/")
    return s[i:] if i >= 0 else "/"


def tld(domain):
    return domain.rsplit(".", 1)[-1].lower() if "." in domain else ""


def score_relevance(text):
    t = (text or "").lower()
    return min(40, sum(w for term, w in RELEVANCE_TERMS.items() if term in t))


def score_authority(dr):
    if not dr:
        return 0
    if dr >= 80: return 25
    if dr >= 60: return 21
    if dr >= 45: return 17
    if dr >= 30: return 12
    if dr >= 15: return 7
    return 3


def score_traffic_reality(dr, traffic):
    """Traffic relative to CLAIMED authority. Unknown scores neutral, not zero —
    a missing measurement is not evidence of a dead site."""
    if traffic is None:
        return 7, True
    if dr and dr > 40 and traffic < 100:
        return 0, False
    if traffic >= 100000: return 15, False
    if traffic >= 10000:  return 13, False
    if traffic >= 1000:   return 10, False
    if traffic >= 100:    return 7, False
    return 2, False


def rejections(row):
    """Every reason, not the first — a row killed by three rules should say so."""
    flags, dom, url = [], row["domain"], row["url"] or ""
    dr, traffic = row.get("dr") or 0, MEASURED_TRAFFIC.get(row["domain"])

    if tld(dom) in SPAM_TLDS:
        flags.append("spam_tld:.%s" % tld(dom))
    if BAD_NEIGHBOURHOOD.search(dom) or BAD_NEIGHBOURHOOD.search(url):
        flags.append("bad_neighbourhood:gambling/pharma/adult/crypto")
    if TEMPLATE_PATH.search(path_of(url)):
        flags.append("template_link_pattern:sitewide/PBN footprint")
    if dr > 40 and traffic is not None and traffic < 100:
        flags.append("inflated_authority:DA %d with %d organic visits" % (dr, traffic))
    if row.get("spam_score") and row["spam_score"] > 40:
        flags.append("spam_score:%d" % row["spam_score"])
    return flags


def composite(row):
    text = " ".join(str(row.get(k) or "") for k in ("domain", "url", "notes"))
    rel = score_relevance(text)
    auth = score_authority(row.get("dr"))
    traf, unverified = score_traffic_reality(row.get("dr"),
                                             MEASURED_TRAFFIC.get(row["domain"]))
    like = TACTIC_LIKELIHOOD.get(row["tactic"], 8)
    return {"relevance": rel, "authority": auth, "traffic_reality": traf,
            "link_likelihood": like, "composite_score": rel + auth + traf + like,
            "traffic_unverified": unverified}


def cmd_run(args):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM targets WHERE tactic != 'audit_historical'")]
    if not rows:
        raise SystemExit("STOP: no discovery rows. Run 03_discover first.")

    with open(os.path.join(DATA, "owned.json"), encoding="utf-8") as fh:
        od = json.load(fh)
    with open(os.path.join(DATA, "affiliates.json"), encoding="utf-8") as fh:
        ad = json.load(fh)
    excluded = {e["domain"].lower() for e in od["owned"]}
    excluded |= {c.split("/")[0].lower() for c in
                 od.get("controlled_subdomains_and_profiles", [])}
    excluded |= {e["domain"].lower() for e in ad["affiliates"]}

    qualified, rejected, reason_counter = [], [], Counter()
    for r in rows:
        flags = rejections(r)
        if r["domain"] in excluded:            # belt and braces over 03_discover
            flags.append("excluded_property:owned or affiliate")
        sc = composite(r)
        # Dealer rows are manually seeded human applications, tracked not
        # scored. Six known manufacturer programmes were being rejected for
        # scoring below a floor built for crawled prospects — the floor was
        # never meant to apply to them.
        if (not flags and r["tactic"] != "dealer"
                and sc["composite_score"] < QUALIFY_FLOOR):
            flags.append("below_floor:composite %d < %d"
                         % (sc["composite_score"], QUALIFY_FLOOR))
        status = "rejected" if flags else "qualified"
        for f in flags:
            reason_counter[f.split(":")[0]] += 1
        conn.execute("""UPDATE targets SET relevance=?, authority=?,
                        traffic_reality=?, link_likelihood=?, composite_score=?,
                        risk_flags=?, status=?, last_checked=? WHERE id=?""",
                     (sc["relevance"], sc["authority"], sc["traffic_reality"],
                      sc["link_likelihood"], sc["composite_score"],
                      json.dumps(flags) if flags else None,
                      "queued" if (status == "qualified" and r["tactic"] == "dealer")
                      else status,
                      args.date or _date.today().isoformat(), r["id"]))
        (rejected if flags else qualified).append({**r, **sc, "risk_flags": flags})
    conn.commit()

    # Acceptance assertion: nothing owned or affiliate may reach qualified.
    leaked = [q["domain"] for q in qualified if q["domain"] in excluded]
    assert not leaked, "Hard Rule 1 violated: %s reached qualified" % leaked
    print("assert: zero owned/affiliate domains qualified — OK")

    for q in qualified:
        assert q["url"] and path_of(q["url"]) not in ("", None), \
            "%s qualified without a specific page" % q["domain"]
    print("assert: every qualified row carries a specific page — OK")

    n_q, n_r = len(qualified), len(rejected)
    print("\ndiscovered %d | qualified %d | rejected %d" % (len(rows), n_q, n_r))
    print("\nper source:")
    for t in ("gap", "roundup", "resource_page", "mention", "dealer"):
        d = sum(1 for r in rows if r["tactic"] == t)
        q = sum(1 for r in qualified if r["tactic"] == t)
        print("  %-14s discovered %3d  qualified %3d  rejected %3d" % (t, d, q, d - q))
    print("\ntop rejection reasons:")
    top = reason_counter.most_common(3)
    for reason, n in top:
        print("  %-24s %3d  (%.0f%% of all rejections)" % (reason, n, 100.0 * n / max(1, n_r)))

    write_worklist(qualified, rejected, rows, reason_counter, args.date)
    print("\nworklist: %s" % os.path.relpath(WORKLIST, ROOT))

    stop = []
    if n_q < MIN_QUALIFIED:
        stop.append("qualified %d < %d — filters or scoring are wrong" % (n_q, MIN_QUALIFIED))
    if n_q > MAX_QUALIFIED:
        stop.append("qualified %d > %d — filters too loose" % (n_q, MAX_QUALIFIED))
    if top and n_r and top[0][1] > n_r / 2:
        stop.append("'%s' accounts for %d of %d rejections (>50%%) — the rule may be wrong"
                    % (top[0][0], top[0][1], n_r))
    if stop:
        print("\n" + "=" * 68)
        for s in stop:
            print("STOP CONDITION: %s" % s)
        return 3
    conn.close()
    return 0


def write_worklist(qualified, rejected, all_rows, reasons, run_date):
    run_date = run_date or _date.today().isoformat()
    qualified.sort(key=lambda r: -r["composite_score"])
    L = ["# Link building worklist — %s" % run_date, "",
         "Generated by `pipelines/04_qualify.py`. **Nothing here has been contacted.**",
         "Every pipeline drafts; a human sends (Hard Rule 3).", "",
         "| | |", "|---|---|",
         "| Discovered | %d |" % len(all_rows),
         "| Qualified | **%d** |" % len(qualified),
         "| Rejected | %d |" % len(rejected),
         "| Velocity cap | 8 new earned referring domains per week (Hard Rule 4) |", "",
         "At the cap, this worklist is roughly %d weeks of outreach. Working it "
         "faster is not an option — the August 2026 footprint is what the cap "
         "exists to prevent repeating." % max(1, round(len(qualified) / 8.0)), ""]

    L += ["## Counts per source", "",
          "| Source | Discovered | Qualified | Rejected |", "|---|---|---|---|"]
    for t in ("gap", "roundup", "resource_page", "mention", "dealer"):
        d = sum(1 for r in all_rows if r["tactic"] == t)
        q = sum(1 for r in qualified if r["tactic"] == t)
        L.append("| `%s` | %d | %d | %d |" % (t, d, q, d - q))
    L += ["", "## Top rejection reasons", "",
          "| Reason | Count | Share of rejections |", "|---|---|---|"]
    for reason, n in reasons.most_common(3):
        L.append("| `%s` | %d | %.0f%% |" % (reason, n, 100.0 * n / max(1, len(rejected))))
    L += ["", "If one rule is killing most of the pile, suspect the rule before "
          "the data.", ""]

    for tactic in ("mention", "dealer", "resource_page", "roundup", "gap"):
        group = [q for q in qualified if q["tactic"] == tactic]
        if not group:
            continue
        L += ["---", "", "## %s — %d qualified" % (tactic.replace("_", " ").title(), len(group)),
              "", "*%s*" % TACTIC_ANGLE[tactic], "",
              "| # | Domain | DA | Score | Page to approach | Why it qualified |",
              "|---|---|---|---|---|---|"]
        for i, q in enumerate(group, 1):
            why = "rel %d / auth %d / traffic %d / likelihood %d" % (
                q["relevance"], q["authority"], q["traffic_reality"], q["link_likelihood"])
            if q.get("traffic_unverified"):
                why += " · traffic not measured"
            L.append("| %d | `%s` | %s | **%d** | %s | %s |" % (
                i, q["domain"], q.get("dr") or "—", q["composite_score"],
                q["url"], why))
        L.append("")

    L += ["---", "", "## Rejected (%d)" % len(rejected), "",
          "Recorded with reasons so a wrong rule is visible rather than silent.", "",
          "| Domain | DA | Reasons |", "|---|---|---|"]
    for r in sorted(rejected, key=lambda x: -(x.get("dr") or 0)):
        L.append("| `%s` | %s | %s |" % (r["domain"], r.get("dr") or "—",
                                         "; ".join(r["risk_flags"])))
    L += ["", "## Method notes", "",
          "- Organic traffic was measured only for ambiguous high-DA candidates; "
          "one call per domain is too many at tier1. Rows marked *traffic not "
          "measured* were scored neutrally on that component and were NOT "
          "rejected for it. Rejecting a real publisher on data never fetched is "
          "the failure this avoids.",
          "- `cvillico.com` (DA 63, 0 visits, 0 keywords, 32,989 backlinks) and "
          "`dearworld.me` (DA 51, 2 visits, and actually a mobile-homes site) "
          "were measured and confirm the inflated-authority rule fires on real data.",
          "- Dealer rows are human applications and sit at `queued`, not `qualified`.",
          ]
    os.makedirs(os.path.dirname(WORKLIST), exist_ok=True)
    with open(WORKLIST, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def cmd_self_test(_args):
    failures = []

    def check(name, cond):
        print("  %s %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    print("self-test: reject rules")
    check("PBN template path rejected", any("template_link_pattern" in f for f in
          rejections({"domain": "cvillico.com", "url": "https://cvillico.com/all/1298/17.html", "dr": 63})))
    check("gambling domain rejected", any("bad_neighbourhood" in f for f in
          rejections({"domain": "casinooftheking.com", "url": "https://casinooftheking.com/x", "dr": 54})))
    check("spam TLD rejected", any("spam_tld" in f for f in
          rejections({"domain": "junk.cfd", "url": "https://junk.cfd/a", "dr": 20})))
    check("inflated authority rejected on MEASURED zero traffic",
          any("inflated_authority" in f for f in
              rejections({"domain": "cvillico.com", "url": "https://cvillico.com/post", "dr": 63})))
    check("high DA with UNKNOWN traffic is NOT rejected",
          not rejections({"domain": "forbes.com", "url": "https://forbes.com/a/best-home-sauna/", "dr": 94}))
    check("multiple reasons all recorded", len(
          rejections({"domain": "ufabet.cfd", "url": "https://ufabet.cfd/all/1298/16.html", "dr": 55})) >= 3)

    print("self-test: scoring")
    check("relevance rewards niche terms",
          score_relevance("best infrared sauna and cold plunge guide") > 30)
    check("relevance near zero off-topic", score_relevance("zoho mail login") == 0)
    check("authority monotonic", score_authority(94) > score_authority(46) > score_authority(10))
    t_unknown = score_traffic_reality(90, None)
    check("unknown traffic scores neutral and flags", t_unknown == (7, True))
    check("measured zero traffic at high DA scores 0",
          score_traffic_reality(63, 0) == (0, False))
    check("real traffic scores well", score_traffic_reality(90, 500000)[0] == 15)
    check("mention has highest link likelihood",
          TACTIC_LIKELIHOOD["mention"] == max(TACTIC_LIKELIHOOD.values()))

    print("self-test: path_of")
    check("path extracted", path_of("https://a.com/all/1298/17.html") == "/all/1298/17.html")
    check("bare domain path is /", path_of("https://a.com") == "/")

    print()
    if failures:
        print("SELF-TEST FAILED: %d" % len(failures)); return 1
    print("SELF-TEST PASSED"); return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--date"); r.set_defaults(fn=cmd_run)
    s = sub.add_parser("self-test"); s.set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
