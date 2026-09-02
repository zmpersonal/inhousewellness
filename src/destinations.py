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

# Cluster -> satellite domain. Order matters only for reporting.
CLUSTERS = {
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

SATELLITES = SATELLITE_HOSTS   # single source of truth, shared with the validator

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
SATELLITE_MAX_SHARE = 0.15          # no single satellite above 15% of the window
ROLLING_WINDOW_DAYS = 30
PER_DOMAIN_COOLDOWN_POSTS = 6       # posts that must pass before a domain repeats

# The per-domain cap is a property of the rolling 30-day PUBLISHED window, not of
# whatever batch happens to be in hand. Below this sample size a single post
# arithmetically exceeds an 8% cap (1/13 = 7.7%), so enforcing it on a small
# batch produces a false violation. Same principle as the loop's 30-post minimum:
# do not act on noise.
MIN_N_FOR_DOMAIN_CAP = 25

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


class SatelliteRotator:
    """Round-robin across satellites with a per-domain cooldown, so no single
    domain dominates. Cluster preference wins when its domain is off cooldown."""

    def __init__(self, order=SATELLITES, cooldown=PER_DOMAIN_COOLDOWN_POSTS):
        self.order = list(order)
        self.cooldown = cooldown
        self._i = 0
        self._last_used = {}      # domain -> position counter
        self._n = 0

    def _available(self, domain):
        last = self._last_used.get(domain)
        return last is None or (self._n - last) >= self.cooldown

    def next(self, preferred=None):
        self._n += 1
        if preferred and preferred != INH and preferred in self.order and self._available(preferred):
            self._last_used[preferred] = self._n
            return preferred
        for _ in range(len(self.order)):
            d = self.order[self._i % len(self.order)]
            self._i += 1
            if self._available(d):
                self._last_used[d] = self._n
                return d
        d = self.order[self._i % len(self.order)]
        self._i += 1
        self._last_used[d] = self._n
        return d


def plan_destinations(rows, inh_share=INH_MIN_SHARE):
    """Assign a destination DOMAIN to each row, filling the INH quota first.

    Deterministic: rows are ordered by priority, the top `inh_share` fraction
    goes to INH, and the remainder is rotated across satellites with the
    cluster preference honoured where the cooldown allows.
    """
    n = len(rows)
    n_inh = max(0, min(n, round(n * inh_share + 1e-9)))
    # Highest-priority rows keep the INH destination -- commercial intent first.
    ordered = sorted(range(n), key=lambda i: (
        0 if rows[i].get("cluster") == "commercial_intent" else 1,
        -float(rows[i].get("priority") or 0),
    ))
    assigned = {}
    for rank, idx in enumerate(ordered):
        assigned[idx] = INH if rank < n_inh else None
    rot = SatelliteRotator()
    for idx in ordered:
        if assigned[idx] is None:
            assigned[idx] = rot.next(preferred=CLUSTERS.get(rows[idx].get("cluster")))
    return [assigned[i] for i in range(n)]


# ---------------------------------------------------------------------------
# Interactive assets (Round 3, item 4)
#
# Three tools in the network have the highest save-and-share potential and
# nothing currently routes to them. An asset only wins a row when its keyword
# rule matches -- it is a routing preference, never a fallback for a row that
# has no honest destination.
# ---------------------------------------------------------------------------

INTERACTIVE_ASSETS = [
    {
        "name": "BHIS home-fit finder",
        "url": "https://besthomeinfraredsauna.com/best/small-spaces",
        "keywords": re.compile(
            r"\b(?:dimension|size|sizing|fit|fits|ceiling|clearance|space|spaces|"
            r"small|compact|corner|room|footprint|how\s+big|will\s+it\s+fit|"
            r"2\s*person|two\s*person|1\s*person)\b", re.I),
        "platforms": None,                    # any platform
    },
    {
        "name": "BHIS EMF index",
        "url": "https://besthomeinfraredsauna.com/emf",
        "keywords": re.compile(
            r"\b(?:emf|electromagnetic|low\s*emf|near\s*zero|radiation|"
            r"safe|safety|transparen\w*|claim\w*)\b", re.I),
        "platforms": None,
    },
    {
        "name": "Healthspan Habits Score",
        "url": "https://healthresearchdatabase.com/healthspan",
        "keywords": re.compile(
            r"\b(?:benefit|benefits|health|healthy|research|study|studies|evidence|"
            r"science|longevity|aging|ageing|good\s+for|help|helps|effect|effects)\b",
            re.I),
        # Built-in challenge-a-friend mechanic -- a share loop. Sharing is native
        # on IG and FB; Pinterest is a search surface, so prefer the feeds.
        "platforms": ("instagram", "facebook"),
        # evidence-read archetype OR a health-curiosity keyword -- two signals for
        # the same asset, not a conjunction. Requiring both matched nothing.
        "archetypes": ("evidence_read",),
        "archetype_is_optional": True,
    },
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


def asset_name_for_url(url):
    """Reverse-lookup an interactive asset by its URL, for pre-set links."""
    for a in INTERACTIVE_ASSETS:
        if a["url"].rstrip("/") == (url or "").rstrip("/"):
            return a["name"]
    return None


def route(rows, *, inh_min_share=INH_MIN_SHARE, sat_max_share=SATELLITE_MAX_SHARE,
          preassigned_domains=(), total_rows=None):
    """Assign a destination to every row, honouring the floor WITHOUT degrading
    a match.

    Each row must arrive carrying:
        best_url / best_score / best_domain   -- best match anywhere in the corpus
        inh_url  / inh_score                  -- best INH match, or None
        keyword, archetype

    Rows whose only above-threshold destination is a satellite that has hit its
    cap are blocked, not redirected somewhere weaker.
    """
    # Rows whose destination is already fixed (link_locked) do not pass through
    # the router but DO count toward both the INH floor and the per-domain caps.
    pre = Counter(preassigned_domains)
    n = total_rows if total_rows is not None else len(rows)
    target_inh = max(0, int(round(n * inh_min_share)) - pre.get(INH, 0))
    cap = max(1, int(n * sat_max_share))

    # 1. Rows that CAN go to INH, best INH match first -- these fill the floor.
    inh_capable = sorted(
        [i for i, r in enumerate(rows) if r.get("inh_url")],
        key=lambda i: -(rows[i].get("inh_score") or 0))

    assigned = {}
    for rank, i in enumerate(inh_capable):
        if rank < target_inh:
            assigned[i] = {"link": rows[i]["inh_url"], "domain": INH,
                           "reason": "INH match (fills the >=60% floor)"}

    # 2. Everything else: interactive asset if it fits, else the best match.
    per_domain = Counter(v["domain"] for v in assigned.values())
    per_domain.update(pre)
    blocked = []
    for i, r in enumerate(rows):
        if i in assigned:
            continue
        asset = interactive_asset_for(r.get("keyword"), r.get("archetype"))
        cand = []
        if asset:
            cand.append((asset[1], domain_of(asset[1]), f"interactive: {asset[0]}"))
        if r.get("best_url"):
            cand.append((r["best_url"], r.get("best_domain") or domain_of(r["best_url"]),
                         "best corpus match"))
        if r.get("inh_url"):
            cand.append((r["inh_url"], INH, "INH match"))

        placed = False
        for url, dom, why in cand:
            if dom != INH and per_domain[dom] >= cap:
                continue
            assigned[i] = {"link": url, "domain": dom, "reason": why}
            per_domain[dom] += 1
            placed = True
            break
        if not placed:
            blocked.append((i, "every candidate destination is over its domain cap; "
                               "blocked rather than degraded to a weaker match"))

    out = Counter(v["domain"] for v in assigned.values())
    out.update(pre)
    return assigned, dict(blocked), out
