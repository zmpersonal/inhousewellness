#!/usr/bin/env python3
"""
00_audit — classify every referring domain, snapshot it, diff against the last run.

The analysis this reproduces was done by hand once (reports/audit-baseline.md).
The September 2026 profile was lost because nothing wrote it down. This pipeline
exists so that never happens again: every run archives the full per-link pull to
data/snapshots/YYYY-MM-DD.json and diffs against the most recent prior snapshot.

The agent is a dumb executor. Ubersuggest is an MCP tool and MCP only exists
inside an agent session, so the agent relays two raw JSON payloads in and this
script does all selection, classification, counting and diffing. No model call
decides a class.

Usage
  00_audit.py run --overview <f.json> --backlinks <f.json> [--date YYYY-MM-DD]
  00_audit.py self-test          # diff logic against a synthetic prior snapshot

Hard Rule 8 (linkbuilding/CLAUDE.md): backlinks_overview's follow/nofollow split
is broken. It is fenced off in code below — touching it raises.
"""

import argparse, json, os, re, sqlite3, sys, unicodedata
from collections import defaultdict
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # linkbuilding/
DATA = os.path.join(ROOT, "data")
SNAPS = os.path.join(DATA, "snapshots")
DB_PATH = os.path.join(DATA, "links.db")
SCHEMA = os.path.join(DATA, "schema.sql")
DISAVOW = os.path.join(DATA, "disavow-candidates.txt")

MONEY_SITE = "inhousewellness.com"

# Expected class counts from reports/audit-baseline.md. Tolerance +/-1 per class.
# These are the acceptance test. They are NEVER edited to match output — a larger
# divergence means the rules below are encoded wrong.
BASELINE = {
    "earned": 17, "owned": 10, "affiliate": 6, "syndication": 9,
    "directory_spam": 14, "local_aggregator": 4, "unresolved": 6,
}
TOLERANCE = 1
MIN_REF_DOMAINS = 60      # stop condition: fewer than this means a bad pull

# Scraped listing sites, per linkbuilding/CLAUDE.md taxonomy. Never submitted to.
LOCAL_AGGREGATORS = {"blushlocal.net", "poicircle.com", "ratelivo.com", "redsavia.com"}

# Carried-forward flags. Provenance is a human question; the pipeline must never
# guess at it. Five paid-insertion-shaped links plus one unconfigured Shopify
# store. If confirmed clean, earned rises to 22.
CARRIED_FORWARD = {
    "momdaughts.com":      "paid-insertion anchor shape; mid-sentence phrase anchor",
    "journalismband.com":  "paid-insertion anchor shape; mid-sentence phrase anchor",
    "morpheus8london.com": "paid-insertion anchor shape; same target as 2 others",
    "lumiluxlimited.com":  "paid-insertion anchor shape; same target as 2 others",
    "functionalacademy.org": "paid-insertion anchor shape; mid-sentence phrase anchor",
    "xwifkv-j0.myshopify.com": "leaked template anchor; ownership unknown (data/owned.json)",
}

SPAM_SCORE_CUTOFF = 40
SPAM_TLDS = {"cfd", "sbs", "click", "website", "top"}
# Page shapes that only auto-generated scrapers produce.
SPAM_URL_SIGNATURES = re.compile(
    r"/domain/|domain\.php|[?&]part=|virus-scanner|/ai/brand-voice/|[?&]tag=", re.I
)
SYNDICATION_SEED_DR = 60   # a cluster needs a real publisher at its head
INJECTION_SPAM_FLOOR = 10  # naked-url + nofollow + this spam score = injected link


# --------------------------------------------------------------------------
# Hard Rule 8 enforcement
# --------------------------------------------------------------------------
class OverviewGuard(dict):
    """backlinks_overview with its follow/noFollow split fenced off.

    The API reports follow:0 / noFollow:66 for a profile whose four most
    valuable links are all follow. Any code reading those keys would conclude
    the only tactic that works passes no authority. Reading them raises.
    """
    POISONED = ("follow", "noFollow", "nofollow")

    def __getitem__(self, key):
        if key in self.POISONED:
            raise AssertionError(
                "Hard Rule 8: backlinks_overview['%s'] is known-broken and must "
                "never be read. Derive rel from the per-link 'nofollow' field." % key
            )
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self.POISONED:
            return self.__getitem__(key)
        return super().get(key, default)


# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------
def reg_domain(url):
    m = re.match(r"^[a-z]+://([^/?#]+)", url.strip(), re.I)
    host = (m.group(1) if m else url).lower()
    return host[4:] if host.startswith("www.") else host


def url_path(url):
    """Path component only. The host must not be searched for brand tokens:
    doing so made every domain a republication of itself, and made
    trustedoptima.site and trustedoptima.website republications of each other."""
    s = re.sub(r"^[a-z]+://", "", url.strip(), flags=re.I)
    i = s.find("/")
    return s[i:] if i >= 0 else ""


def tld(domain):
    return domain.rsplit(".", 1)[-1] if "." in domain else ""


def norm(text):
    """Lowercase, strip accents and every non-alphanumeric character."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text).lower()
    return re.sub(r"[^a-z0-9]+", "", t)


def strip_scheme(text):
    return re.sub(r"^https?://", "", (text or "").strip().lower())


def brand_token(domain):
    """womansworld.com -> womansworld. Used to spot republication slugs."""
    return norm(domain.rsplit(".", 1)[0].split(".")[-1])


def anchor_class(anchor):
    a = (anchor or "").strip().lower()
    if not a:
        return "generic"
    if strip_scheme(a).startswith(MONEY_SITE):
        return "naked_url"
    if "inhouse wellness" in a or "inhousewellness" in a or "in house wellness" in a:
        return "brand"
    if re.search(r"\b(sauna|plunge|infrared|person|barrel)\b", a):
        return "exact_match"
    return "generic"


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def near_identical(a, b, raw_a=None, raw_b=None):
    """Anchors making the same claim, allowing only a short credential suffix.

    'timur alptunaer' and 'timur alptunaer md' are the same claim. A character
    prefix test would also call 'inhouse wellness' and 'inhousewellness.com'
    the same claim — they are not: the first is a brand mention on a publisher,
    the second is a bare URL emitted by a domain-list scraper. Matching them
    put 9 scrapers in healthline's syndication cluster. Compare whole tokens,
    and permit extra tokens only when they are short enough to be a credential
    (md, phd, dr).
    """
    if a == b:
        return True
    if not a or not b:
        return False
    ta, tb = tokens(raw_a), tokens(raw_b)
    if not ta or not tb:
        return False
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if long_[:len(short)] != short:
        return False
    extra = long_[len(short):]
    return bool(extra) and all(len(t) <= 3 for t in extra)


# --------------------------------------------------------------------------
# reference data
# --------------------------------------------------------------------------
def load_exclusions():
    with open(os.path.join(DATA, "owned.json"), encoding="utf-8") as fh:
        owned_doc = json.load(fh)
    with open(os.path.join(DATA, "affiliates.json"), encoding="utf-8") as fh:
        aff_doc = json.load(fh)

    owned = {e["domain"].lower() for e in owned_doc["owned"]}
    # controlled entries may carry a path (pinterest.com/inhousewellness)
    owned |= {c.split("/")[0].lower() for c in
              owned_doc.get("controlled_subdomains_and_profiles", [])}
    # NOTE: owned_doc['unresolved'] is deliberately NOT merged in. Those are
    # carried-forward flags, not owned properties. Merging them would silently
    # resolve the exact question the human still has to answer.
    affiliates = {e["domain"].lower() for e in aff_doc["affiliates"]}
    return owned, affiliates


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------
def detect_syndication(rows, already):
    """Republished copies of an article that also appears on a real publisher.

    Cluster on shared target URL + near-identical anchor. A cluster headed by a
    genuine publisher (DR >= 60) makes its low-authority members syndication.

    Two guards matter:
      * A member at DR >= 60 is protected. eatthis.com ('in house wellness')
        normalises into healthline's cluster ('inhouse wellness') and must not
        be demoted to a scraper copy of it.
      * A member whose own URL path carries another member's brand token is a
        republication regardless of its own authority. newsbreak.com sits at
        DR 77 but its path is /woman-s-world-510705/... — it is Woman's World,
        republished. Authority alone would have called it earned.
    """
    syndicated = {}
    by_target = defaultdict(list)
    for r in rows:
        if r["domain"] in already:
            continue
        by_target[r["url_to"]].append(r)

    for _target, members in by_target.items():
        if len(members) < 2:
            continue
        clusters = []
        for r in members:
            for c in clusters:
                if near_identical(norm(r["anchor"]), norm(c[0]["anchor"]),
                                  r["anchor"], c[0]["anchor"]):
                    c.append(r)
                    break
            else:
                clusters.append([r])

        for cluster in clusters:
            if len(cluster) < 2:
                continue
            repub = {}
            for m in cluster:
                path = norm(url_path(m["url_from"]))
                for other in cluster:
                    if other is m:
                        continue
                    tok = brand_token(other["domain"])
                    if len(tok) >= 6 and tok in path:
                        repub[m["domain"]] = "republication of %s" % other["domain"]
                        break
            head = max((m for m in cluster if m["domain"] not in repub),
                       key=lambda m: m["dr"], default=None)
            if head is None or head["dr"] < SYNDICATION_SEED_DR:
                continue
            for m in cluster:
                if m["domain"] in repub:
                    syndicated[m["domain"]] = repub[m["domain"]]
                elif m is not head and m["dr"] < SYNDICATION_SEED_DR:
                    syndicated[m["domain"]] = "scraper copy; cluster head %s" % head["domain"]
    return syndicated


def spam_reason(r):
    score = r["spam_score"] or 0
    if score > SPAM_SCORE_CUTOFF:
        return "spam score %d > %d" % (score, SPAM_SCORE_CUTOFF)
    if tld(r["domain"]) in SPAM_TLDS:
        return "throwaway TLD .%s" % tld(r["domain"])
    if SPAM_URL_SIGNATURES.search(r["url_from"]):
        return "auto-generated page shape"
    if norm(r["anchor"]) == norm(MONEY_SITE):
        return "bare money-site domain as anchor (domain-list scraper)"
    if (strip_scheme(r["anchor"]).startswith(MONEY_SITE)
            and r["nofollow"] and score >= INJECTION_SPAM_FLOOR):
        return "naked-url anchor, nofollow, spam score %d (injected link)" % score
    return None


def classify(rows, owned, affiliates):
    """First match wins. Order per linkbuilding/CLAUDE.md round-01 taxonomy.

    One documented deviation: `unresolved` is evaluated BEFORE the heuristic
    classes rather than last. As written, `earned` is the default after ruling
    everything else out, which makes a trailing `unresolved` unreachable — the
    five paid-pattern links would silently land in `earned`, which is the one
    outcome the spec explicitly forbids. Never-guess outranks rule order.
    Assertion below proves the deviation changes no count.
    """
    out, reasons = {}, {}

    for r in rows:
        d = r["domain"]
        if d in owned:
            out[d], reasons[d] = "owned", "matches data/owned.json"
        elif d in affiliates:
            out[d], reasons[d] = "affiliate", "matches data/affiliates.json"
        elif d in CARRIED_FORWARD:
            out[d], reasons[d] = "unresolved", CARRIED_FORWARD[d]

    for d, why in detect_syndication(rows, set(out)).items():
        out[d], reasons[d] = "syndication", why

    for r in rows:
        d = r["domain"]
        if d in out:
            continue
        why = spam_reason(r)
        if why:
            out[d], reasons[d] = "directory_spam", why
        elif d in LOCAL_AGGREGATORS:
            out[d], reasons[d] = "local_aggregator", "scraped listing, never submitted to"
        else:
            out[d], reasons[d] = "earned", "independent editorial; no exclusion matched"

    # The deviation above is inert: no carried-forward domain is reachable by
    # any heuristic rule, so evaluating it early cannot steal a row.
    for r in rows:
        if r["domain"] in CARRIED_FORWARD:
            assert spam_reason(r) is None and r["domain"] not in LOCAL_AGGREGATORS, (
                "carried-forward domain %s is reachable by a heuristic rule; "
                "rule order now changes counts" % r["domain"])
    return out, reasons


# --------------------------------------------------------------------------
# snapshot + diff
# --------------------------------------------------------------------------
def parse_rows(backlinks_doc):
    if not backlinks_doc.get("done"):
        raise SystemExit("STOP: backlinks pull returned done=false. Retry the call.")
    rows = []
    for b in backlinks_doc["backlinks"]:
        rows.append({
            "domain": reg_domain(b["url_from"]),
            "url_from": b["url_from"],
            "url_to": b["url_to"],
            "title": b.get("title") or "",
            "anchor": b.get("anchor") or "",
            # Hard Rule 8: rel comes from here and nowhere else.
            "nofollow": bool(b.get("nofollow")),
            "dr": b.get("domain_inlink_rank") or 0,
            "page_rank": b.get("inlink_rank") or 0,
            "spam_score": b.get("spam_score"),
            "first_seen": b.get("first_seen") or "",
            "last_visited": b.get("last_visited") or "",
        })
    return rows


def latest_prior_snapshot(today):
    if not os.path.isdir(SNAPS):
        return None, None
    names = sorted(n for n in os.listdir(SNAPS)
                   if n.endswith(".json") and n[:-5] < today)
    if not names:
        return None, None
    path = os.path.join(SNAPS, names[-1])
    with open(path, encoding="utf-8") as fh:
        return names[-1][:-5], json.load(fh)


def diff_snapshots(prior, current):
    """Lost earned domains lead. Against a 17-domain base that is the highest-
    signal event this pipeline can detect."""
    p = {l["domain"]: l for l in prior["links"]}
    c = {l["domain"]: l for l in current["links"]}
    d = {"lost_earned": [], "lost_other": [], "gained": [],
         "class_changed": [], "anchor_changed": [], "rel_changed": []}

    for dom in sorted(set(p) - set(c)):
        entry = {"domain": dom, "was_class": p[dom]["class"],
                 "anchor": p[dom]["anchor"], "url_to": p[dom]["url_to"]}
        (d["lost_earned"] if p[dom]["class"] == "earned" else d["lost_other"]).append(entry)

    for dom in sorted(set(c) - set(p)):
        d["gained"].append({"domain": dom, "class": c[dom]["class"],
                            "anchor": c[dom]["anchor"], "url_to": c[dom]["url_to"]})

    for dom in sorted(set(p) & set(c)):
        if p[dom]["class"] != c[dom]["class"]:
            d["class_changed"].append({"domain": dom, "from": p[dom]["class"],
                                       "to": c[dom]["class"]})
        if p[dom]["anchor"] != c[dom]["anchor"]:
            d["anchor_changed"].append({"domain": dom, "from": p[dom]["anchor"],
                                        "to": c[dom]["anchor"]})
        if p[dom]["nofollow"] != c[dom]["nofollow"]:
            d["rel_changed"].append({
                "domain": dom,
                "from": "nofollow" if p[dom]["nofollow"] else "follow",
                "to": "nofollow" if c[dom]["nofollow"] else "follow"})
    return d


def render_diff(prior_date, d):
    L = ["", "=" * 68, "DIFF vs %s" % prior_date, "=" * 68]
    if d["lost_earned"]:
        L.append("")
        L.append("!! LOST EARNED DOMAINS (%d) — highest-signal event" % len(d["lost_earned"]))
        for e in d["lost_earned"]:
            L.append("   - %s  (%s -> %s)" % (e["domain"], e["anchor"], e["url_to"]))
    else:
        L.append("   no earned domains lost")
    for key, label in (("lost_other", "lost (non-earned)"), ("gained", "gained"),
                       ("class_changed", "class changed"),
                       ("anchor_changed", "anchor changed"),
                       ("rel_changed", "rel changed")):
        if d[key]:
            L.append("")
            L.append("   %s (%d):" % (label, len(d[key])))
            for e in d[key]:
                L.append("     %s" % json.dumps(e, ensure_ascii=False))
    return "\n".join(L)


# --------------------------------------------------------------------------
# database
# --------------------------------------------------------------------------
def write_db(run_date, rows, classes, reasons, overview_totals):
    os.makedirs(DATA, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    # Audit history lives in its own tables. schema.sql is the outreach spine and
    # is not edited here.
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS audit_runs (
        run_date TEXT PRIMARY KEY, domain_authority INTEGER,
        total_backlinks INTEGER, referring_domains INTEGER, earned_count INTEGER);
    CREATE TABLE IF NOT EXISTS audit_links (
        run_date TEXT NOT NULL, domain TEXT NOT NULL, link_class TEXT NOT NULL,
        reason TEXT, url_from TEXT, url_to TEXT, anchor TEXT, anchor_class TEXT,
        rel_attr TEXT, dr INTEGER, spam_score INTEGER, first_seen TEXT,
        PRIMARY KEY (run_date, domain));
    CREATE INDEX IF NOT EXISTS idx_audit_links_class ON audit_links(link_class);
    """)
    conn.execute("DELETE FROM audit_links WHERE run_date=?", (run_date,))
    conn.execute("DELETE FROM audit_runs  WHERE run_date=?", (run_date,))
    conn.execute(
        "INSERT INTO audit_runs VALUES (?,?,?,?,?)",
        (run_date, overview_totals["domainAuthority"], overview_totals["backlinks"],
         overview_totals["refDomains"],
         sum(1 for c in classes.values() if c == "earned")))

    for r in rows:
        d = r["domain"]
        rel = "nofollow" if r["nofollow"] else "follow"
        conn.execute("INSERT INTO audit_links VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (run_date, d, classes[d], reasons[d], r["url_from"], r["url_to"],
                      r["anchor"], anchor_class(r["anchor"]), rel, r["dr"],
                      r["spam_score"], r["first_seen"]))
        # targets carries the live profile so later pipelines can query it.
        # Tactic is the RESERVED 'audit_historical' (Round 2 pre-flight): these
        # rows are history, not opportunities, and no discovery source may ever
        # reuse the value. A collision on UNIQUE(domain, tactic) does not raise,
        # it silently drops the opportunity.
        conn.execute("""
            INSERT INTO targets (domain, url, tactic, discovered_via, discovered_at,
                                 dr, spam_score, status, live_url, anchor_text,
                                 anchor_class, rel_attr, last_checked, notes)
            VALUES (?,?,'audit_historical','ubersuggest_backlinks',?,?,?,'live',?,?,?,?,?,?)
            ON CONFLICT(domain, tactic) DO UPDATE SET
                dr=excluded.dr, spam_score=excluded.spam_score,
                anchor_text=excluded.anchor_text, anchor_class=excluded.anchor_class,
                rel_attr=excluded.rel_attr, last_checked=excluded.last_checked,
                notes=excluded.notes
        """, (d, r["url_from"], r["first_seen"] or run_date, r["dr"], r["spam_score"],
              r["url_from"], r["anchor"], anchor_class(r["anchor"]), rel, run_date,
              "%s: %s" % (classes[d], reasons[d])))
    conn.commit()
    conn.close()


def write_disavow(run_date, rows, classes, reasons):
    spam = sorted(r["domain"] for r in rows if classes[r["domain"]] == "directory_spam")
    lines = [
        "# Disavow candidates — inhousewellness.com",
        "# Generated by pipelines/00_audit.py on %s. DRAFT ONLY." % run_date,
        "#",
        "# This file is a prepared artifact, NOT a recommended action. Disavowal is",
        "# usually unnecessary absent a manual action in Google Search Console —",
        "# Google discounts links like these on its own, and a careless disavow can",
        "# remove links that were helping. Do not submit this without a manual",
        "# action and a human decision.",
        "#",
        "# directory_spam only. Syndication is deliberately EXCLUDED: scraper copies",
        "# of a legitimate article are normal, harmless, and disavowing them would",
        "# throw away real coverage of the Healthline and Woman's World placements.",
        "#",
        "# %d domains." % len(spam), "",
    ]
    for d in spam:
        lines.append("# %s" % reasons[d])
        lines.append("domain:%s" % d)
        lines.append("")
    with open(DISAVOW, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return len(spam)


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_run(args):
    with open(args.overview, encoding="utf-8") as fh:
        overview = OverviewGuard(json.load(fh))
    with open(args.backlinks, encoding="utf-8") as fh:
        backlinks_doc = json.load(fh)

    ref_domains = overview["refDomains"]
    if ref_domains < MIN_REF_DOMAINS:
        raise SystemExit("STOP: Ubersuggest returned %d referring domains "
                         "(< %d). Bad pull — do not classify."
                         % (ref_domains, MIN_REF_DOMAINS))

    rows = parse_rows(backlinks_doc)
    by_domain = {}
    for r in rows:                      # one_per_domain=true, but be defensive
        by_domain.setdefault(r["domain"], r)
    rows = list(by_domain.values())

    if len(rows) < ref_domains:
        print("NOTE: %d rows for %d reported referring domains — partial coverage."
              % (len(rows), ref_domains))

    owned, affiliates = load_exclusions()
    classes, reasons = classify(rows, owned, affiliates)

    counts = defaultdict(int)
    for c in classes.values():
        counts[c] += 1

    run_date = args.date or _date.today().isoformat()
    print("=" * 68)
    print("00_audit — %s" % run_date)
    print("=" * 68)
    print("DA %s | %s backlinks | %s referring domains | %d rows classified"
          % (overview["domainAuthority"], overview["backlinks"], ref_domains, len(rows)))
    print()
    print("%-18s %8s %10s %s" % ("class", "actual", "baseline", "delta"))
    ok = True
    for cls in ("earned", "owned", "affiliate", "syndication",
                "directory_spam", "local_aggregator", "unresolved"):
        exp, act = BASELINE[cls], counts[cls]
        delta = act - exp
        flag = "" if abs(delta) <= TOLERANCE else "   <-- OUT OF TOLERANCE"
        ok = ok and abs(delta) <= TOLERANCE
        print("%-18s %8d %10d %+6d%s" % (cls, act, exp, delta, flag))
        if flag:
            for d, c in sorted(classes.items()):
                if c == cls:
                    print("        %-42s %s" % (d, reasons[d]))
    print()
    print("total classified: %d" % sum(counts.values()))

    follow = sum(1 for r in rows if not r["nofollow"])
    print("rel from per-link data: %d follow / %d nofollow "
          "(overview claims 0 follow — Hard Rule 8)" % (follow, len(rows) - follow))

    if not ok:
        print()
        print("STOP: a class diverged by more than +/-%d. The rules are encoded "
              "wrong. Report the diff; do NOT adjust BASELINE." % TOLERANCE)
        return 2

    snapshot = {
        "run_date": run_date, "source": "ubersuggest.backlinks",
        "domain_authority": overview["domainAuthority"],
        "total_backlinks": overview["backlinks"], "referring_domains": ref_domains,
        "counts": dict(counts),
        "links": sorted(({**r, "class": classes[r["domain"]],
                          "reason": reasons[r["domain"]]} for r in rows),
                        key=lambda x: x["domain"]),
    }
    os.makedirs(SNAPS, exist_ok=True)
    prior_date, prior = latest_prior_snapshot(run_date)
    snap_path = os.path.join(SNAPS, "%s.json" % run_date)
    with open(snap_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("snapshot: %s" % os.path.relpath(snap_path, ROOT))

    if prior:
        print(render_diff(prior_date, diff_snapshots(prior, snapshot)))
    else:
        print("no prior snapshot — first run, nothing to diff")

    write_db(run_date, rows, classes, reasons, {
        "domainAuthority": overview["domainAuthority"],
        "backlinks": overview["backlinks"], "refDomains": ref_domains})
    print("db: %s" % os.path.relpath(DB_PATH, ROOT))
    n = write_disavow(run_date, rows, classes, reasons)
    print("disavow candidates: %s (%d domains, draft only)"
          % (os.path.relpath(DISAVOW, ROOT), n))
    return 0


def cmd_self_test(_args):
    """Diff logic against a synthetic prior snapshot, plus the Rule 8 guard."""
    failures = []

    def check(name, cond):
        print("  %s %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    print("self-test: Hard Rule 8 guard")
    g = OverviewGuard({"refDomains": 66, "follow": 0, "noFollow": 66})
    try:
        g["follow"]; check("reading overview['follow'] raises", False)
    except AssertionError:
        check("reading overview['follow'] raises", True)
    try:
        g.get("noFollow"); check("overview.get('noFollow') raises", False)
    except AssertionError:
        check("overview.get('noFollow') raises", True)
    check("unpoisoned keys still readable", g["refDomains"] == 66)

    print("self-test: diff against synthetic prior snapshot")
    def link(dom, cls, anchor="a", nofollow=False, url_to="/x"):
        return {"domain": dom, "class": cls, "anchor": anchor,
                "nofollow": nofollow, "url_to": url_to}
    prior = {"links": [
        link("healthline.com", "earned", "inhouse wellness"),
        link("eatthis.com", "earned", "in house wellness"),
        link("gonesoon.com", "earned", "brand anchor"),
        link("junk.cfd", "directory_spam"),
        link("flipme.com", "syndication", "old anchor"),
        link("relchange.com", "earned", "steady", nofollow=False),
    ]}
    current = {"links": [
        link("healthline.com", "earned", "inhouse wellness"),
        link("eatthis.com", "earned", "in house wellness"),
        link("junk.cfd", "directory_spam"),
        link("flipme.com", "earned", "new anchor"),
        link("relchange.com", "earned", "steady", nofollow=True),
        link("brandnew.com", "earned", "fresh"),
    ]}
    d = diff_snapshots(prior, current)
    check("lost earned domain surfaced", [e["domain"] for e in d["lost_earned"]] == ["gonesoon.com"])
    check("lost earned is the only loss reported as earned", len(d["lost_earned"]) == 1)
    check("non-earned loss not conflated", d["lost_other"] == [])
    check("gained domain detected", [e["domain"] for e in d["gained"]] == ["brandnew.com"])
    check("class change detected",
          d["class_changed"] == [{"domain": "flipme.com", "from": "syndication", "to": "earned"}])
    check("anchor change detected",
          [e["domain"] for e in d["anchor_changed"]] == ["flipme.com"])
    check("rel change detected",
          d["rel_changed"] == [{"domain": "relchange.com", "from": "follow", "to": "nofollow"}])
    check("unchanged domains produce no noise",
          all(e["domain"] != "healthline.com" for e in d["anchor_changed"] + d["class_changed"]))

    print("self-test: lost-earned ordering")
    p2 = {"links": [link("a.com", "directory_spam"), link("b.com", "earned")]}
    c2 = {"links": []}
    d2 = diff_snapshots(p2, c2)
    check("earned loss separated from spam loss",
          [e["domain"] for e in d2["lost_earned"]] == ["b.com"]
          and [e["domain"] for e in d2["lost_other"]] == ["a.com"])

    print()
    if failures:
        print("SELF-TEST FAILED: %d" % len(failures))
        return 1
    print("SELF-TEST PASSED")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="classify a live pull, snapshot, diff")
    r.add_argument("--overview", required=True)
    r.add_argument("--backlinks", required=True)
    r.add_argument("--date")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("self-test", help="diff logic + Rule 8 guard")
    s.set_defaults(fn=cmd_self_test)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
