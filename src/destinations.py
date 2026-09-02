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
from dataclasses import dataclass

INH = "inhousewellness.com"

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

SATELLITES = tuple(d for d in dict.fromkeys(CLUSTERS.values()) if d != INH)

# Quota rules.
INH_MIN_SHARE = 0.70
SATELLITE_MAX_SHARE = 0.08          # no single satellite above 8% of the window
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
