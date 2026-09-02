"""Destination routing across INH + the satellite network.

Every post on every platform carries a destination. The split is a QUOTA to
fill, not an exception to permit:

    INH        >= 70% of destinations over a rolling 30-day window
    satellites ~30%, round-robin with a per-domain cooldown

The 70% floor exists because the Pinterest account is under Verified Merchant
Program review, and an account spraying links across ten related domains is a
recognisable spam pattern. The ratio is asserted in code; drift below the floor
fails the build.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .limits import INH_HOST as INH, SATELLITE_HOSTS

# Cluster -> PREFERRED domain. Retired as a hard mapping 2026-09-02 (Round 6).
#
# This was a thin-satellite shape: it assumed each domain was a single-purpose
# page, so one cluster could own one domain. Reality: healthresearchdatabase has
# 842 indexed pages, infinitesauna 197, saunasfactorydirect 173. Matching should
# search all 11 domains and merely PREFER the cluster's domain -- a weight, not a
# gate. `CLUSTER_PREFERENCE_BONUS` is that weight.
CLUSTER_PREFERRED_DOMAIN = {
    "commercial_intent": INH,                       # buying, product -- default
    "evidence":          "healthresearchdatabase.com",
    "cold_plunge":       "arcticsoak.com",
    "infrared_compare":  "besthomeinfraredsauna.com",
    "cost":              "saunasfactorydirect.com",
    "outdoor_steam":     "outdoorsteamsauna.com",
    "hot_tub":           "tubsandsaunas.com",
    "brands":            "saunaimport.com",
    "commercial_install":"commercialinfraredsauna.com",
    "home_wellness":     "homenhealthy.com",
    "home_wellness_alt": "infinitesauna.com",
}

# Kept under the old name for the few call sites that only want the domain list.
CLUSTERS = CLUSTER_PREFERRED_DOMAIN

SATELLITES = SATELLITE_HOSTS   # single source of truth, shared with the validator

# A cluster's preferred domain gets this added to its match score. Small on
# purpose: it breaks ties toward the topically-right property without ever
# letting a weak match on the "correct" domain beat a strong match elsewhere.
CLUSTER_PREFERENCE_BONUS = 0.06

# Quota rules. Revised 2026-09-02 (Round 3).
#
# The original 70% floor assumed the satellites were thin link pages and that
# spreading links across them looked like a spam pattern under Verified Merchant
# Program review. That assumption was wrong: the full-network sweep found 1,908
# indexed pages across the ten domains -- real content properties with their own
# data, methodologies and tools. Forcing 70% now would mean sending pins to INH
# pages that do not answer the keyword, which is the exact failure the matcher
# was built to eliminate.
#
# MATCH QUALITY OUTRANKS THE RATIO. If honouring the floor requires a
# sub-threshold match, the row is blocked instead. Never degrade a match to fill
# a quota.
# Lowered 0.60 -> 0.40 on 2026-09-02. 41.2% was the measured CEILING, not a
# routing preference: only 14 of 34 queued rows have any INH destination scoring
# >= 0.40, and reaching 60% would have meant either sending pins to INH pages
# that do not answer the keyword, or blocking 11 rows to satisfy a ratio.
# Re-raise this as INH-side content grows -- it is the durable fix.
INH_MIN_SHARE = 0.40
ROLLING_WINDOW_DAYS = 30

# --- The domain cap was measuring the wrong thing (revised 2026-09-02) --------
#
# The risk was never "too many pins to besthomeinfraredsauna.com". A 90-model
# spec database with published methodology is not a spam destination. The real
# risk is many pins pointing at the SAME URL, which Pinterest downranks.
#
# So the domain cap loosens and a URL cap does the actual work. This forces the
# right behaviour: batch 02 cannot dump 25 rows on /emf/, and rows spread onto
# deeper pages -- individual models, /methodology/, the 120V list, /electrical/.
SATELLITE_MAX_SHARE = 0.35          # was 0.15
PER_URL_MAX_PINS = 4                # per destination URL per rolling 30 days

# A cap is only meaningful once the sample can express it: below 1/cap items a
# single post is arithmetically over. Derived, not hardcoded -- the old value of
# 25 was computed against the 8% cap and silently outlived it.
MIN_N_FOR_DOMAIN_CAP = int(round(1 / SATELLITE_MAX_SHARE)) + 1

# Keyword signals -> cluster. Deterministic, ordered: first match wins, so the
# more specific clusters are listed before the general ones.
_CLUSTER_SIGNALS = [
    ("cold_plunge",        r"\bcold\s*plunge|ice\s*bath|cold\s*water|cold\s*exposure|contrast\s*therapy|chiller\b"),
    ("hot_tub",            r"\bhot\s*tub|jacuzzi|swim\s*spa\b"),
    ("commercial_install", r"\bcommercial|gym|spa\s+business|hotel|clinic|studio\b"),
    # infrared_compare must precede outdoor_steam: "infrared vs steam sauna" is a
    # comparison, not an outdoor-steam topic.
    ("infrared_compare",   r"\binfrared\s+vs|vs\s+infrared|near\s*infrared|far\s*infrared|emf|full\s*spectrum|dry\s+vs\s+wet|traditional\s+vs\b"),
    ("outdoor_steam",      r"\boutdoor|barrel|steam\s*(?:room|sauna)|garden|backyard\b"),
    ("brands",             r"\bdynamic|golden\s*designs|finnmark|therasage|heavenly\s*heat|maxxus|almost\s*heaven|clearlight|sunlighten|brand|review\b"),
    ("cost",              r"\bcost|price|pricing|cheap|budget|electricity|kwh|bill|expensive|worth\s+it|factory\s*direct\b"),
    ("evidence",           r"\bstudy|studies|research|evidence|science|scientific|trial|benefits?\s+of|does\s+.*\s+(?:help|work)\b"),
    ("home_wellness",      r"\bwellness|routine|habit|recovery|sleep|stress|relax\b"),
]
_CLUSTER_SIGNALS = [(c, re.compile(p, re.I)) for c, p in _CLUSTER_SIGNALS]


def classify(*texts):
    """Return the cluster for a keyword/title. Defaults to commercial_intent."""
    blob = " ".join(t for t in texts if t)
    for cluster, rx in _CLUSTER_SIGNALS:
        if rx.search(blob):
            return cluster
    return "commercial_intent"


def canonical_url(url):
    """Normalise a URL for cap accounting.

    /emf and /emf/ are the same page. Counted separately they let 6 pins land on
    a destination capped at 4 -- defeating the cap that exists precisely to stop
    that. Also strips the fragment: /#finder and / are one page to Pinterest.
    """
    u = (url or "").strip()
    u = u.split("#")[0]
    scheme, _, rest = u.partition("://")
    if not rest:
        return u.rstrip("/").lower()
    host, _, path = rest.partition("/")
    return f"{scheme.lower()}://{host.lower()}/{path}".rstrip("/")


def domain_of(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def is_inh(url):
    return domain_of(url) == INH


@dataclass
class QuotaReport:
    total: int
    inh: int
    per_domain: dict

    @property
    def inh_share(self):
        return (self.inh / self.total) if self.total else 1.0

    def worst_satellite(self):
        sats = {d: n for d, n in self.per_domain.items() if d != INH}
        if not sats:
            return None, 0.0
        d = max(sats, key=sats.get)
        return d, (sats[d] / self.total if self.total else 0.0)

    def url_violations(self, urls):
        """Per-URL cap: more than PER_URL_MAX_PINS pins at one destination."""
        c = Counter(canonical_url(u) for u in urls if u)
        return [f"{u} has {n} pins, above the {PER_URL_MAX_PINS}-per-URL cap"
                for u, n in c.most_common() if n > PER_URL_MAX_PINS]

    def violations(self):
        """Hard violations only -- these fail the build."""
        out = []
        if self.total and self.inh_share < INH_MIN_SHARE:
            out.append(f"INH share {self.inh_share:.1%} is below the {INH_MIN_SHARE:.0%} floor "
                       f"({self.inh}/{self.total})")
        d, share = self.worst_satellite()
        if d and share > SATELLITE_MAX_SHARE and self.total >= MIN_N_FOR_DOMAIN_CAP:
            out.append(f"satellite {d} is {share:.1%} of the window, above the "
                       f"{SATELLITE_MAX_SHARE:.0%} per-domain cap")
        return out

    def notices(self):
        """Soft signals -- reported, not fatal."""
        out = []
        d, share = self.worst_satellite()
        if d and share > SATELLITE_MAX_SHARE and self.total < MIN_N_FOR_DOMAIN_CAP:
            out.append(f"{d} is {share:.1%} of only {self.total} destinations — under the "
                       f"{MIN_N_FOR_DOMAIN_CAP}-post minimum, so the "
                       f"{SATELLITE_MAX_SHARE:.0%} cap is not asserted yet")
        return out

    def summary(self):
        lines = [f"destinations: {self.total} | INH {self.inh} ({self.inh_share:.1%})"]
        for dom, n in sorted(self.per_domain.items(), key=lambda kv: -kv[1]):
            lines.append(f"    {n:4d}  {n/self.total:6.1%}  {dom}")
        return "\n".join(lines)


def audit(urls):
    per = {}
    inh = 0
    for u in urls:
        d = domain_of(u)
        if not d:
            continue
        per[d] = per.get(d, 0) + 1
        if d == INH:
            inh += 1
    return QuotaReport(total=sum(per.values()), inh=inh, per_domain=per)


# NOTE: SatelliteRotator and plan_destinations were removed 2026-09-02. Both were
# round-robin machinery built for the thin-satellite era, when the goal was to
# spread links thinly across domains. route() supersedes them: it fills the INH
# floor, then places each row on the best destination inside the domain and URL
# caps. The per-domain cooldown went with them -- the per-URL cap is the correct
# expression of that intent.

# ---------------------------------------------------------------------------
# Interactive assets (Round 3, item 4)
#
# Three tools in the network have the highest save-and-share potential and
# nothing currently routes to them. An asset only wins a row when its keyword
# rule matches -- it is a routing preference, never a fallback for a row that
# has no honest destination.
# ---------------------------------------------------------------------------

# Expanded 3 -> 12 on 2026-09-02. The 3-asset list was a thin-satellite
# artifact: it assumed the satellites held a handful of useful pages. The sweep
# found calculators and indexes on five domains. More save-worthy destinations
# is the whole point -- these are the pages a 40-60 buyer actually bookmarks.
INTERACTIVE_ASSETS = [
    {"name": "BHIS EMF index",
     "url": "https://besthomeinfraredsauna.com/emf",
     "keywords": re.compile(r"\b(?:emf|electromagnetic|low\s*emf|near\s*zero|"
                            r"radiation|gauss|shield\w*|transparen\w*)\b", re.I),
     "platforms": None},
    {"name": "BHIS electrical checker",
     "url": "https://besthomeinfraredsauna.com/electrical",
     "keywords": re.compile(r"\b(?:electrical|circuit|breaker|amp|amps|amperage|"
                            r"volt|volts|voltage|120v|240v|outlet|panel|wiring)\b", re.I),
     "platforms": None},
    {"name": "BHIS home-fit finder",
     "url": "https://besthomeinfraredsauna.com/best/small-spaces",
     "keywords": re.compile(r"\b(?:dimension\w*|size|sizing|fit|fits|ceiling|"
                            r"clearance|space|spaces|small|compact|corner|room|"
                            r"footprint|how\s+big|will\s+it\s+fit)\b", re.I),
     "platforms": None},
    {"name": "BHIS 120V list",
     "url": "https://besthomeinfraredsauna.com/best/120v",
     "keywords": re.compile(r"\b(?:120v|plug[-\s]?in|standard\s+outlet|"
                            r"no\s+electrician|single\s+circuit)\b", re.I),
     "platforms": None},
    {"name": "ArcticSoak chiller sizing calculator",
     "url": "https://arcticsoak.com/calculators/chiller",
     "keywords": re.compile(r"\bchiller|cool\w*\s+(?:system|unit)|"
                            r"(?:cold\s*plunge|plunge).*(?:size|sizing|temperature)\b", re.I),
     "platforms": None},
    {"name": "ArcticSoak ice calculator",
     "url": "https://arcticsoak.com/calculators/ice",
     "keywords": re.compile(r"\bice\b|how\s+much\s+ice|ice\s*bath\b", re.I),
     "platforms": None},
    {"name": "ArcticSoak cold plunge cost calculator",
     "url": "https://arcticsoak.com/calculators/cost",
     "keywords": re.compile(r"\bcold\s*plunge\b.*\b(?:cost|electricity|run|running)\b|"
                            r"\b(?:cost|electricity)\b.*\bcold\s*plunge\b", re.I),
     "platforms": None},
    {"name": "Outdoor sauna climate index",
     "url": "https://outdoorsteamsauna.com/climate-index",
     "keywords": re.compile(r"\b(?:outdoor|winter|cold\s+climate|snow|freeze|"
                            r"year[-\s]?round|climate)\b", re.I),
     "platforms": None},
    {"name": "Outdoor sauna heater sizing",
     "url": "https://outdoorsteamsauna.com/heater-sizing",
     "keywords": re.compile(r"\bheater\s*(?:siz\w+|kw|wattage)|\bkw\b|"
                            r"what\s+size\s+heater\b", re.I),
     "platforms": None},
    {"name": "Commercial sauna ROI calculator",
     "url": "https://commercialinfraredsauna.com/calculators/roi",
     "keywords": re.compile(r"\b(?:roi|payback|revenue|commercial|gym|spa\s+business|"
                            r"studio|hotel)\b", re.I),
     "platforms": None},
    {"name": "Tubs & Saunas cost calculator",
     "url": "https://tubsandsaunas.com/cost-calculator",
     "keywords": re.compile(r"\bhot\s*tub\b.*\bcost\b|\bcost\b.*\bhot\s*tub\b|"
                            r"\bswim\s*spa\b", re.I),
     "platforms": None},
    {"name": "Healthspan Habits Score",
     "url": "https://healthresearchdatabase.com/healthspan",
     "keywords": re.compile(r"\b(?:benefit|benefits|health|healthy|research|study|"
                            r"studies|evidence|science|longevity|aging|ageing|"
                            r"good\s+for|help|helps|effect|effects)\b", re.I),
     # Built-in challenge-a-friend mechanic -- a share loop. Sharing is native on
     # IG and FB; Pinterest is a search surface, so prefer the feeds.
     "platforms": ("instagram", "facebook"),
     "archetypes": ("evidence_read",),
     "archetype_is_optional": True},
]


def interactive_asset_for(keyword, archetype=None, platform=None):
    """Return (name, url) when an interactive asset genuinely fits, else None."""
    for a in INTERACTIVE_ASSETS:
        if not a["keywords"].search(keyword or ""):
            continue
        if a.get("platforms") and platform and platform not in a["platforms"]:
            continue
        if (a.get("archetypes") and archetype
                and archetype not in a["archetypes"]
                and not a.get("archetype_is_optional")):
            continue
        return a["name"], a["url"]
    return None


def preference_bonus(cluster, domain):
    """Weight, not a gate. Returns the bonus this domain earns for this cluster."""
    if not cluster or not domain:
        return 0.0
    return CLUSTER_PREFERENCE_BONUS if CLUSTER_PREFERRED_DOMAIN.get(cluster) == domain else 0.0


def asset_name_for_url(url):
    """Reverse-lookup an interactive asset by its URL, for pre-set links."""
    for a in INTERACTIVE_ASSETS:
        if a["url"].rstrip("/") == (url or "").rstrip("/"):
            return a["name"]
    return None


def route(rows, *, inh_min_share=INH_MIN_SHARE, sat_max_share=SATELLITE_MAX_SHARE,
          per_url_max=PER_URL_MAX_PINS, preassigned_domains=(), preassigned_urls=(),
          total_rows=None):
    """Assign a destination to every row, honouring the floor and BOTH caps
    without ever degrading a match.

    Each row must arrive carrying:
        best_url / best_score / best_domain   -- best match anywhere in the corpus
        inh_url  / inh_score                  -- best INH match, or None
        locked_url                            -- a pre-set destination, optional
        alt_urls                              -- deeper same-domain candidates, optional
        keyword, archetype

    A locked URL is a FIRST CHOICE, not an absolute: once it hits the per-URL cap
    the row falls through to a deeper page on the same domain. That is the whole
    point of the URL cap -- it pushes batch 02 off /emf/ and onto model pages.

    A row with no candidate inside both caps is BLOCKED, never redirected to a
    weaker match.
    """
    pre_dom = Counter(preassigned_domains)
    pre_url = Counter(canonical_url(u) for u in preassigned_urls)
    n = total_rows if total_rows is not None else len(rows)
    target_inh = max(0, int(round(n * inh_min_share)) - pre_dom.get(INH, 0))
    dom_cap = max(1, int(n * sat_max_share))

    # 1. Rows that CAN go to INH, best INH match first -- these fill the floor.
    inh_capable = sorted(
        [i for i, r in enumerate(rows) if r.get("inh_url")],
        key=lambda i: -(rows[i].get("inh_score") or 0))

    per_domain, per_url = Counter(pre_dom), Counter(pre_url)
    assigned, blocked = {}, []

    for rank, i in enumerate(inh_capable):
        if rank >= target_inh:
            break
        u = rows[i]["inh_url"]
        cu = canonical_url(u)
        if per_url[cu] >= per_url_max:
            continue                      # even INH respects the per-URL cap
        assigned[i] = {"link": u, "domain": INH,
                       "reason": "INH match (fills the >=40% floor)"}
        per_domain[INH] += 1
        per_url[cu] += 1

    # 2. Everything else, in candidate order.
    for i, r in enumerate(rows):
        if i in assigned:
            continue
        cand = []
        if r.get("locked_url"):
            cand.append((r["locked_url"], domain_of(r["locked_url"]),
                         "pre-set interactive asset"))
        asset = interactive_asset_for(r.get("keyword"), r.get("archetype"))
        if asset:
            cand.append((asset[1], domain_of(asset[1]), f"interactive: {asset[0]}"))
        if r.get("best_url"):
            cand.append((r["best_url"], r.get("best_domain") or domain_of(r["best_url"]),
                         "best corpus match"))
        for alt in (r.get("alt_urls") or []):
            cand.append((alt["url"], domain_of(alt["url"]),
                         f"deeper page on the same domain ({alt.get('score', 0):.2f})"))
        if r.get("inh_url"):
            cand.append((r["inh_url"], INH, "INH match"))

        placed = False
        for url, dom, why in cand:
            cu = canonical_url(url)
            if per_url[cu] >= per_url_max:
                continue
            if dom != INH and per_domain[dom] >= dom_cap:
                continue
            assigned[i] = {"link": url, "domain": dom, "reason": why}
            per_domain[dom] += 1
            per_url[cu] += 1
            placed = True
            break
        if not placed:
            over_url = [u for u, _, _ in cand
                        if per_url[canonical_url(u)] >= per_url_max]
            blocked.append((i, (
                f"no destination inside the caps: "
                f"{len(over_url)} candidate URL(s) at the {per_url_max}-per-URL cap"
                if over_url else
                "every candidate destination is over its domain cap")
                + "; blocked rather than degraded to a weaker match"))

    out_dom = Counter(v["domain"] for v in assigned.values())
    out_dom.update(pre_dom)
    return assigned, dict(blocked), out_dom
