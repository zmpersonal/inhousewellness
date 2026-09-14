#!/usr/bin/env python3
"""
03_discover — turn raw source payloads into candidate rows in `targets`.

Four sources: competitor gap, SERP roundups/resource pages, unlinked mentions,
and six manually seeded dealer applications.

Hard Rule 1 is enforced at the top of every source: owned.json and
affiliates.json are loaded once and matches are dropped SILENTLY, before
anything else happens. The failure this prevents is a pipeline that surfaces
your own ten sites as fresh opportunities and emails your own affiliates.

Domains that already link to us are also dropped. They are not opportunities —
00_audit already tracks all 66 of them.

PRE-FLIGHT / tactic collision
  targets carries UNIQUE(domain, tactic). 00_audit wrote 66 rows at
  tactic='audit'. This round writes gap / roundup / resource_page / mention /
  dealer, which are disjoint, so no row can collide. The reserved tactic
  'audit_historical' is nonetheless applied by migrate_audit_tactic() so that
  'audit' is never a value a working pipeline writes, and a future discovery
  source named 'audit' cannot silently drop a rediscovered domain. A collision
  here would not raise — it would quietly lose an opportunity.

Usage
  03_discover.py run --gap <f.json> --serp <f.json> --mentions <f.json>
  03_discover.py self-test
"""

import argparse, json, os, re, sqlite3, sys
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "links.db")
SCHEMA = os.path.join(DATA, "schema.sql")

MONEY_SITE = "inhousewellness.com"
RESERVED_AUDIT_TACTIC = "audit_historical"

# Competitors and marketplaces. A competitor's own store page is not a link
# opportunity — nobody links out to a rival from their product collection.
COMPETITOR_HOSTS = {
    "havenofheat.com", "sunvalleysaunas.com", "sisulifestyle.com",
    "dynamicsaunasdirect.com", "nurecover.com", "peakprimalwellness.com",
    "goldendesigninc.com", "sunhomesaunas.com", "mysaunaworld.com",
    "jnhlifestyles.com", "selectsaunas.com", "almostheaven.com",
    "saunaplace.com", "finnishsaunabuilders.com", "thesaunaheater.com",
    "redwoodoutdoors.com", "desertplunge.com", "plunge.com", "renutherapy.com",
    "thecoldplungestore.com", "olisaunas.com", "backyardescapism.com",
    "cedar-sense.com", "inlandsauna.com", "warehouserunner.com",
}
MARKETPLACE_HOSTS = {
    "amazon.com", "homedepot.com", "costco.com", "walmart.com", "ebay.com",
    "youtube.com", "reddit.com", "instagram.com", "facebook.com",
    "pinterest.com", "trustpilot.com", "x.com", "twitter.com", "tiktok.com",
    "linkedin.com", "wikipedia.org", "grokipedia.com",
}

# Dealer applications. Six corporate entities, not eight brands — Golden
# Designs is the parent of both Dynamic Saunas and Maxxus Saunas. These are
# human applications; they sit in targets so they are tracked, not so a
# pipeline works them.
DEALERS = [
    ("goldendesigninc.com", "https://goldendesigninc.com/pages/become-a-dealer",
     "Golden Designs — covers Golden Designs, Dynamic and Maxxus. One application, three brands."),
    ("harviasauna.com", "https://harviasauna.com/dealer-application/",
     "Harvia — Nasdaq Helsinki listed, also owns Almost Heaven and ThermaSol. Formal, gated, slow. Separate motion."),
    ("finnmarksauna.com", "https://finnmarksauna.com/pages/dealer-enquiry",
     "Finnmark Designs — dealer enquiry."),
    ("scandiamfg.com", "https://scandiamfg.com/pages/dealer-inquiry",
     "Scandia — manufacturer dealer inquiry."),
    ("leisurecraft.com", "https://leisurecraft.com/become-a-dealer/",
     "Leisurecraft — already carried; formalise the dealer listing."),
    ("ripavi.com", "https://ripavi.com/pages/wholesale",
     "Ripavi — VERIFY the dealer program exists before building the application."),
]

ROUNDUP_RE = re.compile(
    r"\b(best|top|guide|review|vs|compare|comparison|roundup|buyer)\b", re.I)
RESOURCE_RE = re.compile(
    r"\b(resources?|links?|directory|recommend|tools?|where to buy)\b", re.I)


def reg_domain(url):
    s = re.sub(r"^[a-z]+://", "", (url or "").strip(), flags=re.I)
    host = s.split("/")[0].split("?")[0].lower()
    return host[4:] if host.startswith("www.") else host


def load_exclusions():
    with open(os.path.join(DATA, "owned.json"), encoding="utf-8") as fh:
        od = json.load(fh)
    with open(os.path.join(DATA, "affiliates.json"), encoding="utf-8") as fh:
        ad = json.load(fh)
    owned = {e["domain"].lower() for e in od["owned"]}
    owned |= {c.split("/")[0].lower() for c in
              od.get("controlled_subdomains_and_profiles", [])}
    owned |= {u["domain"].lower() for u in od.get("unresolved", [])}
    owned.add(MONEY_SITE)
    affiliates = {e["domain"].lower() for e in ad["affiliates"]}
    return owned, affiliates


def existing_link_domains(conn):
    try:
        return {r[0] for r in conn.execute("SELECT domain FROM audit_links")}
    except sqlite3.OperationalError:
        return set()


class Sink:
    """Collects candidates, dropping excluded domains silently (Hard Rule 1)."""

    def __init__(self, owned, affiliates, already_linking):
        self.owned, self.affiliates = owned, affiliates
        self.already = already_linking
        self.rows = {}
        self.dropped = {"owned": 0, "affiliate": 0, "already_links": 0,
                        "competitor": 0, "marketplace": 0, "self": 0}

    def add(self, domain, url, tactic, via, note):
        d = (domain or "").lower()
        if not d or "." not in d:
            return
        if d == MONEY_SITE or d.endswith("." + MONEY_SITE):
            self.dropped["self"] += 1; return
        if d in self.owned:
            self.dropped["owned"] += 1; return          # silent, Hard Rule 1
        if d in self.affiliates:
            self.dropped["affiliate"] += 1; return      # silent, Hard Rule 1
        if d in self.already:
            self.dropped["already_links"] += 1; return
        # Competitor/marketplace screens apply to CRAWLED candidates only.
        # Dealer rows are deliberate manual seeds: Golden Designs is both a
        # manufacturer we want a dealer page from and an organic competitor,
        # and the competitor screen silently ate it. Hard Rule 1 above still
        # applies to seeds — an owned domain is never seeded.
        if tactic != "dealer":
            if d in COMPETITOR_HOSTS:
                self.dropped["competitor"] += 1; return
            if d in MARKETPLACE_HOSTS or any(d.endswith("." + m) for m in MARKETPLACE_HOSTS):
                self.dropped["marketplace"] += 1; return
        key = (d, tactic)
        if key in self.rows:            # dedup across sources
            return
        self.rows[key] = {"domain": d, "url": url, "tactic": tactic,
                          "discovered_via": via, "note": note}


def source_gap(doc, sink):
    for r in doc["rows"]:
        url = r["backlink"]
        if not url.startswith("http"):
            url = "https://" + url
        sink.add(reg_domain(url), url, "gap",
                 "ubersuggest.backlink_opportunity:%s" % doc.get("competitor", "?"),
                 "links to %s (DA %s), not to us" % (doc.get("competitor"),
                                                     r.get("domain_authority")))
        sink.rows.get((reg_domain(url), "gap"), {}).update(
            {"dr": r.get("domain_authority"), "page_authority": r.get("page_authority")})


def source_serp(doc, sink):
    for kw in doc["keywords"]:
        for e in kw["entries"]:
            d = reg_domain(e["url"])
            title = e.get("title") or ""
            if ROUNDUP_RE.search(title):
                tactic = "roundup"
            elif RESOURCE_RE.search(title):
                tactic = "resource_page"
            else:
                continue          # a plain collection page is not an opportunity
            sink.add(d, e["url"], tactic,
                     "ubersuggest.serp_analysis:%s" % kw["keyword"],
                     "ranks #%s for '%s'" % (e.get("position"), kw["keyword"]))
            row = sink.rows.get((d, tactic))
            if row is not None:
                row.setdefault("dr", e.get("domainAuthority"))
                row.setdefault("keyword", kw["keyword"])


def source_mentions(doc, sink):
    for r in doc["rows"]:
        desc = (r.get("description") or "").lower()
        if "false positive" in desc or "own social" in desc or "owned network" in desc:
            continue
        if "affiliate" in desc or "already links" in desc:
            continue
        sink.add(reg_domain(r["url"]), r["url"], "mention",
                 "firecrawl.search:unlinked_mention",
                 "mentions the brand: %s" % (r.get("title") or "")[:80])


def source_dealers(sink):
    for domain, url, note in DEALERS:
        sink.add(domain, url, "dealer", "manual_seed", note)


def migrate_audit_tactic(conn):
    n = conn.execute("UPDATE targets SET tactic=? WHERE tactic='audit'",
                     (RESERVED_AUDIT_TACTIC,)).rowcount
    return n


def write_targets(conn, rows, run_date):
    inserted = updated = 0
    for r in rows:
        cur = conn.execute("""
            INSERT INTO targets (domain, url, tactic, discovered_via, discovered_at,
                                 dr, status, notes)
            VALUES (?,?,?,?,?,?, 'new', ?)
            ON CONFLICT(domain, tactic) DO UPDATE SET
                url=excluded.url, dr=COALESCE(excluded.dr, targets.dr),
                notes=excluded.notes
        """, (r["domain"], r["url"], r["tactic"], r["discovered_via"], run_date,
              r.get("dr"), r["note"]))
        if cur.rowcount == 1:
            inserted += 1
        else:
            updated += 1
    # Dealer rows are human applications, tracked not worked.
    conn.execute("UPDATE targets SET status='queued' WHERE tactic='dealer'")
    return inserted, updated


def cmd_run(args):
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA, encoding="utf-8") as fh:
        conn.executescript(fh.read())

    migrated = migrate_audit_tactic(conn)
    print("pre-flight: %d historical rows moved to tactic='%s'"
          % (migrated, RESERVED_AUDIT_TACTIC))
    collide = conn.execute(
        "SELECT COUNT(*) FROM targets WHERE tactic IN "
        "('gap','roundup','resource_page','mention','dealer')").fetchone()[0]
    print("pre-flight: %d pre-existing rows on discovery tactics (expect 0 on "
          "first run)" % collide)

    owned, affiliates = load_exclusions()
    sink = Sink(owned, affiliates, existing_link_domains(conn))

    per_source = {}
    for name, fn, path in (("gap", source_gap, args.gap),
                           ("serp", source_serp, args.serp),
                           ("mentions", source_mentions, args.mentions)):
        before = len(sink.rows)
        with open(path, encoding="utf-8") as fh:
            fn(json.load(fh), sink)
        per_source[name] = len(sink.rows) - before
    before = len(sink.rows)
    source_dealers(sink)
    per_source["dealer"] = len(sink.rows) - before

    run_date = args.date or _date.today().isoformat()
    ins, upd = write_targets(conn, list(sink.rows.values()), run_date)
    conn.commit()

    print()
    print("discovered per source:")
    for k, v in per_source.items():
        print("  %-10s %d%s" % (k, v, "   <-- ZERO, explain" if v == 0 else ""))
    print()
    print("dropped before scoring (Hard Rule 1 and relevance):")
    for k, v in sink.dropped.items():
        print("  %-16s %d" % (k, v))
    print()
    print("targets written: %d new, %d updated" % (ins, upd))

    assert not (set(r["domain"] for r in sink.rows.values()) & (owned | affiliates)), \
        "Hard Rule 1 violated: an owned or affiliate domain reached targets"
    print("assert: zero owned/affiliate domains in discovery output — OK")

    empty = [k for k, v in per_source.items() if v == 0]
    if empty:
        print()
        print("STOP CONDITION: source(s) returned zero rows: %s" % ", ".join(empty))
        return 3
    conn.close()
    return 0


def cmd_self_test(_args):
    failures = []

    def check(name, cond):
        print("  %s %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    print("self-test: Hard Rule 1 exclusion")
    owned = {"besthomeinfraredsauna.com", "healthresearchdatabase.com"}
    aff = {"eliterecoverywellness.com"}
    s = Sink(owned, aff, {"healthline.com"})
    s.add("besthomeinfraredsauna.com", "u", "gap", "v", "n")
    s.add("eliterecoverywellness.com", "u", "gap", "v", "n")
    s.add("healthline.com", "u", "gap", "v", "n")
    s.add("inhousewellness.com", "u", "gap", "v", "n")
    s.add("forbes.com", "u", "gap", "v", "n")
    check("owned domain dropped", s.dropped["owned"] == 1)
    check("affiliate domain dropped", s.dropped["affiliate"] == 1)
    check("already-linking domain dropped", s.dropped["already_links"] == 1)
    check("money site dropped", s.dropped["self"] == 1)
    check("only the real candidate survives", list(s.rows) == [("forbes.com", "gap")])
    check("no owned/affiliate leaked",
          not (set(d for d, _ in s.rows) & (owned | aff)))

    print("self-test: dedup and tactic separation")
    s2 = Sink(set(), set(), set())
    s2.add("forbes.com", "u1", "gap", "v", "n")
    s2.add("forbes.com", "u2", "gap", "v", "n")
    s2.add("forbes.com", "u3", "roundup", "v", "n")
    check("same domain+tactic deduped", len(s2.rows) == 2)
    check("first url wins on dedup", s2.rows[("forbes.com", "gap")]["url"] == "u1")

    print("self-test: reg_domain")
    check("strips www", reg_domain("https://www.forbes.com/x") == "forbes.com")
    check("handles missing scheme", reg_domain("cvillico.com/all/1") == "cvillico.com")
    check("handles subdomain", reg_domain("http://smart.dhgate.com/a") == "smart.dhgate.com")

    print("self-test: SERP tactic routing")
    s3 = Sink(set(), set(), set())
    source_serp({"keywords": [{"keyword": "k", "entries": [
        {"url": "https://a.com/x", "title": "Best Home Saunas 2026", "position": 1, "domainAuthority": 90},
        {"url": "https://b.com/x", "title": "Infrared Saunas | Full Spectrum", "position": 2, "domainAuthority": 20},
        {"url": "https://c.com/x", "title": "Sauna Resources and Links", "position": 3, "domainAuthority": 30},
    ]}]}, s3)
    check("listicle -> roundup", ("a.com", "roundup") in s3.rows)
    check("plain collection page skipped", not any(d == "b.com" for d, _ in s3.rows))
    check("resource page -> resource_page", ("c.com", "resource_page") in s3.rows)

    print("self-test: dealer seeding")
    s4 = Sink(set(), set(), set())
    source_dealers(s4)
    check("six dealer entities seeded", len(s4.rows) == 6)
    check("all tactic=dealer", all(t == "dealer" for _, t in s4.rows))

    print()
    if failures:
        print("SELF-TEST FAILED: %d" % len(failures)); return 1
    print("SELF-TEST PASSED"); return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--gap", required=True); r.add_argument("--serp", required=True)
    r.add_argument("--mentions", required=True); r.add_argument("--date")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("self-test"); s.set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
