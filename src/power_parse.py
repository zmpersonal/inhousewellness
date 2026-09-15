"""Shared power/electrical parsing. ONE definition of the guards, imported by
every reader, so a new source cannot quietly bypass them.

This module exists because Round 1b adds a new source (manufacturer websites)
and the brief requires it to run through the same two guards that caught real
bugs in Round 1. Copying the regexes into the fetcher would satisfy that on the
day and drift apart by the next round. Importing them makes the guarantee
structural: `fetch_manufacturer_specs.py` and `build_cost_tables.py` cannot
disagree about what a valid rating is, because there is only one answer.

THE TWO GUARDS, AND THE BUGS THAT PRODUCED THEM

1. Thousands separators. `W_RX` must match "1,800 watts" as 1800, not 800.
   Without the comma alternative, three SKUs became 0.8, 0.75 and 0.2 kW. Each
   parsed cleanly and passed every structural check, and each would have gone
   straight into the running-cost line as a precise, confident, false number.

2. The plausibility band. A home sauna's rated draw sits between 0.8 and 30 kW.
   Anything outside it is a parse failure or a figure about something else, and
   is refused rather than emitted. This is the guard that catches the CLASS
   rather than the instance -- bug 1 would have been caught by it even before
   the regex was fixed.

THE ONE THING NEVER DONE
kW is never derived from volts x amps. 240V x 30A = 7.2kW is the BREAKER's
capacity; a heater is sized below its breaker. The arithmetic is always
available and is always wrong, so there is deliberately no function here that
performs it.
"""
import re

# Each pattern requires an explicit unit adjacent to the number.
KW_RX = re.compile(r"(\d{1,3}(?:\.\d{1,2})?)\s*k\.?\s*w\b", re.I)
W_RX = re.compile(r"(\d{1,2},\d{3}|\d{3,5})\s*(?:w\b|watts\b)", re.I)
V_RX = re.compile(r"(\d{3})\s*v\b", re.I)
A_RX = re.compile(r"(\d{1,3}(?:\.\d)?)\s*(?:a\b|amp|amps|amperage)", re.I)

# A requirement and a recommendation are different claims. Collapsing them into
# one boolean turns advice into a specification.
DED_REQ_RX = re.compile(r"dedicated[^.;]{0,40}(required|require)", re.I)
DED_REC_RX = re.compile(r"dedicated[^.;]{0,40}recommended", re.I)
DED_NOUN_RX = re.compile(r"dedicated\s+(?:\d{1,3}\s*-?\s*amp\s+)?(?:non-\w+\s+)?"
                         r"(?:circuit|receptacle|breaker|outlet)", re.I)

# Contexts where a wattage is NOT the cabin's rated draw.
W_EXCLUDE = re.compile(r"per panel|each panel|bulb|light|speaker|chromotherapy", re.I)

PLAUSIBLE_KW = (0.8, 30.0)

# Known-positive controls. A probe that has never fired has not been tested, so
# `self_test()` fires each one before any caller trusts a zero.
CONTROLS = {
    "kw": ("Harvia 8 kW electric heater", 8.0),
    "watts_plain": ("Power Consumption: 1750W", 1.75),
    "watts_comma": ("Operates at approximately 1,800 watts", 1.8),
    "volts": ("Voltage: 240V", 240.0),
    "amps": ("Amperage: 30 amps", 30.0),
}


def plausible(kw):
    """True when a rated draw is inside the band a home sauna occupies."""
    return kw is not None and PLAUSIBLE_KW[0] <= kw <= PLAUSIBLE_KW[1]


def span_around(text, match, pad=70):
    lo, hi = max(0, match.start() - pad), min(len(text), match.end() + pad)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def read_kw(text, field, url=None):
    """Stated heater kW. Returns every reading; never derives, never averages."""
    out = []
    for m in KW_RX.finditer(text):
        out.append({"kw": float(m.group(1)), "basis": "traditional_heater_kw",
                    "source_field": field, "source_url": url,
                    "span": span_around(text, m)})
    return out


def read_watts(text, field, url=None):
    """Stated rated draw in watts, comma-aware. Returns every reading."""
    out = []
    for m in W_RX.finditer(text):
        sp = span_around(text, m)
        if W_EXCLUDE.search(sp):
            continue
        out.append({"kw": round(float(m.group(1).replace(",", "")) / 1000.0, 3),
                    "basis": "infrared_rated_watts", "source_field": field,
                    "source_url": url, "span": sp})
    return out


def read_scalar(text, field, rx, key, url=None):
    out = []
    for m in rx.finditer(text):
        out.append({key: float(m.group(1)), "source_field": field,
                    "source_url": url, "span": span_around(text, m)})
    return out


def read_dedicated_circuit(text):
    """Returns (value, qualifier, span) or None. 'Recommended' is checked FIRST
    so advice is never promoted into a requirement."""
    m = DED_REQ_RX.search(text)
    if m:
        return True, None, span_around(text, m)
    m = DED_REC_RX.search(text)
    if m:
        return False, "recommended_not_required", span_around(text, m)
    m = DED_NOUN_RX.search(text)
    if m:
        return True, "stated_as_a_noun_phrase_not_the_word_required", span_around(text, m)
    return None


def self_test():
    """Fire every probe against its known-positive control, and assert the
    plausibility band rejects the exact values the comma bug produced.
    Returns a list of failures; empty means the parsers work."""
    fails = []
    got = read_kw(CONTROLS["kw"][0], "t")
    if not got or got[0]["kw"] != CONTROLS["kw"][1]:
        fails.append(f"kw probe: {got}")
    for key in ("watts_plain", "watts_comma"):
        text, want = CONTROLS[key]
        got = read_watts(text, "t")
        if not got or got[0]["kw"] != want:
            fails.append(f"{key} probe: expected {want}, got {got}")
    for key, rx, field in (("volts", V_RX, "volts"), ("amps", A_RX, "amps")):
        text, want = CONTROLS[key]
        got = read_scalar(text, "t", rx, field)
        if not got or got[0][field] != want:
            fails.append(f"{key} probe: expected {want}, got {got}")
    # The band must reject what the comma bug produced, and accept real values.
    for bad in (0.2, 0.75, 0.8 - 0.01, 45.0):
        if plausible(bad):
            fails.append(f"band wrongly accepts {bad} kW")
    for good in (1.75, 1.8, 8.0, 2.2):
        if not plausible(good):
            fails.append(f"band wrongly rejects {good} kW")
    if read_dedicated_circuit("Dedicated circuit recommended")[0] is not False:
        fails.append("'recommended' was promoted to a requirement")
    if read_dedicated_circuit("120V / 20AMP dedicated circuit.")[0] is not True:
        fails.append("noun-phrase dedicated circuit not detected")
    return fails


if __name__ == "__main__":
    import sys
    f = self_test()
    print("\n".join(f) if f else "power_parse self-test: all probes fire as specified")
    sys.exit(1 if f else 0)
