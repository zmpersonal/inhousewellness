"""Platform limits and constants. Config, never hardcoded at call sites."""

# Hard character limits enforced by each platform's API.
PLATFORM_TEXT_LIMIT = {
    "pinterest": 500,    # pin description
    "instagram": 2200,
    "facebook": 63206,
}

# Practical ceilings we impose on ourselves, well inside the API limits.
# 39 historical Facebook posts were 25,000-51,000 char article dumps
# averaging ~3 impressions. The API allowed them; we do not.
PLATFORM_TEXT_SOFT_MAX = {
    "pinterest": 350,
    "instagram": 1200,
    "facebook": 1500,
}

MIN_TEXT_CHARS = 50

# Pinterest structured-field bounds (adjustment C4).
PIN_TITLE_MIN, PIN_TITLE_MAX = 40, 100
PIN_ALT_MIN, PIN_ALT_MAX = 50, 125

SUPPORTED_PLATFORMS = frozenset(PLATFORM_TEXT_LIMIT)

# Only these hosts may appear in a destination link.
#
# Round 1 allowed inhousewellness.com alone. Round 3 added the satellite network
# as a sanctioned, permanently-rotating destination set: every domain below was
# verified to return 200 AND to link back to inhousewellness.com
# (scripts/verify_destinations.py, which exits 1 on any failure).
#
# This is the gate's DATA, not its logic: an unknown host still fails
# PIN_LINK_OFFSITE. Do not add a domain here without running the verifier.
SATELLITE_HOSTS = (
    "healthresearchdatabase.com",
    "arcticsoak.com",
    "besthomeinfraredsauna.com",
    "saunasfactorydirect.com",
    "outdoorsteamsauna.com",
    "tubsandsaunas.com",
    "saunaimport.com",
    "commercialinfraredsauna.com",
    "homenhealthy.com",
    "infinitesauna.com",
)
INH_HOST = "inhousewellness.com"

ALLOWED_LINK_HOSTS = frozenset(
    [INH_HOST, f"www.{INH_HOST}"]
    + [h for d in SATELLITE_HOSTS for h in (d, f"www.{d}")])


# ---------------------------------------------------------------------------
# Archetype body schemas (Round 7).
#
# The live cycle rendered cards that were ~70% empty: a kicker, a headline, a
# one-line standfirst, then nothing. The comparison card had no comparison; the
# EMF card -- the strongest copy the system has produced -- dropped the
# 90/46/34/4 statistic entirely. The caption call must return the BODY, not just
# a headline.
# ---------------------------------------------------------------------------

ARCHETYPE_BODY = {
    "comparison": {"required": ("a", "b", "rows"), "rows_of": 3,
                   "desc": 'a/b column labels, rows[] of [label, aValue, bValue]'},
    "cost":       {"required": ("figure", "unit", "rows"), "rows_of": 2,
                   "desc": 'figure, unit, rows[] of [label, value], optional note'},
    "spec":       {"required": ("rows",), "rows_of": 2,
                   "desc": 'rows[] of [label, value]'},
    "checklist":  {"required": ("items",), "rows_of": None,
                   "desc": 'items[] of strings'},
    "evidence":   {"required": ("claim", "finding", "strength", "source"), "rows_of": None,
                   "desc": 'claim, finding, strength (strong|moderate|limited), source'},
    "chart":      {"required": ("chart",), "rows_of": None,
                   "desc": 'chart object from the probe: type plus its figures'},
    "correction": {"required": ("xLabel", "yLabel", "x", "y"), "rows_of": None,
                   "desc": 'xLabel/yLabel plus x[] (what buyers compare) and y[] (what decides it)'},
}

# Minimum body entries before a card is worth publishing.
MIN_BODY_ROWS = 3

# Queue archetypes that are not card archetypes map onto one that is.
ARCHETYPE_ALIAS = {
    "reality_check": "checklist",
    "evidence_read": "evidence",
    "explainer": "spec",
    "spec_table": "spec",
    "measured_number": "cost",
    "comparison": "comparison",
    "cost": "cost",
    "correction": "correction",
    "checklist": "checklist",
    "evidence": "evidence",
    "spec": "spec",
    "chart": "chart",
    "finding": "chart",
}


def card_archetype(name):
    return ARCHETYPE_ALIAS.get((name or "").strip().lower(), "spec")


# ---------------------------------------------------------------------------
# NO_FIGURE (Round 9)
#
# The brand's whole position is publishing measurements other sellers will not.
# The first two live Pinterest cards published adjectives instead:
#   "Low / High", "Lower / Higher", "Occasional / Regular", "Flexible / Limited"
# "Lower / Higher" is the vaguest comparison available.
#
# The approved reference, for contrast: 130-150F vs 110-115F, 5-15% vs 100%
# humidity, 15 min vs 35-45 min, 240V / 30 amps. A person planning a build can
# act on that.
# ---------------------------------------------------------------------------

# Archetypes that MUST quantify. checklist and evidence are legitimately
# qualitative and are exempt.
QUANTITATIVE_ARCHETYPES = frozenset({"comparison", "cost", "spec"})
MIN_NUMERIC_CELLS = 2

# A comparative adjective is not a value. If a cell's only content is one of
# these, it does not count toward the threshold.
COMPARATIVE_WORDS = frozenset("""
lower higher more less fewer greater smaller larger bigger better worse
flexible limited occasional regular required needed optional minimal moderate
high low medium mild strong weak fast slow quick short long shorter longer
faster slower cheaper pricier easy easier hard harder simple complex
yes no none some many few most least varies varied depends typical standard
common rare frequent infrequent significant slight
""".split())


# Headline patterns that describe the card instead of asserting anything.
# "Infrared vs steam: the build differences that matter" is a topic label; the
# voice that measurably worked on this audience makes a claim.
BANNED_HEADLINE_PATTERNS = (
    "what actually matters", "the differences that matter", "what you need to know",
    "a complete guide", "everything about", "what actually differs",
    "the real difference", "differences that matter", "what to know",
)


# Blotato account ids, verified live 2026-09-01 via blotato_list_accounts.
# Data, not logic: the publish path looks the platform up here rather than
# carrying an id at a call site, so adding a platform is a visible edit.
BLOTATO_ACCOUNTS = {
    "pinterest": {"accountId": "9630"},
    "facebook": {"accountId": "49743", "pageId": "472026422664772"},
    # Instagram account 68734 is authorized but OUT OF SCOPE -- deliberately
    # absent so the publish path refuses rather than quietly posting there.
}
