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

# Each pattern requires an explicit unit adjacent to the number, AND that the
# number is not the tail of a part number.
#
# `(?<![A-Za-z0-9])` is load-bearing. Without it, Dundalk's SKU "CTC2245W" parsed
# as 2245 W = 2.245 kW -- inside the plausibility band, so nothing caught it, and
# tier-1 precedence let that false value OVERRIDE a correct 6.0 kW metafield on
# leisurecraft-serenity. "CTC2345W" did the same on the Tranquility. A SKU is not
# a rating, and a plausible wrong number is worse than none.
KW_RX = re.compile(r"(?<![A-Za-z0-9])(\d{1,3}(?:\.\d{1,2})?)\s*k\.?\s*w\b", re.I)
W_RX = re.compile(r"(?<![A-Za-z0-9])(\d{1,2},\d{3}|\d{3,5})\s*(?:w\b|watts\b)", re.I)
V_RX = re.compile(r"(\d{3})\s*v\b", re.I)
A_RX = re.compile(r"(\d{1,3}(?:\.\d)?)\s*(?:a\b|amp|amps|amperage)", re.I)

# A requirement and a recommendation are different claims. Collapsing them into
# one boolean turns advice into a specification.
DED_REQ_RX = re.compile(r"dedicated[^.;]{0,40}(required|require)", re.I)
DED_REC_RX = re.compile(r"dedicated[^.;]{0,40}recommended", re.I)
DED_NOUN_RX = re.compile(r"dedicated\s+(?:\d{1,3}\s*-?\s*amp\s+)?(?:non-\w+\s+)?"
                         r"(?:circuit|receptacle|breaker|outlet)", re.I)

# Contexts where a wattage is NOT the cabin's rated draw.
# `option` and `selection required` were added after the full manual run: Dundalk's
# Luna parts list reads "Heater Option (Selection Required) ... Designer B Electric
# Heater - 6KW ... Huum Drop Heater - 6KW ... Harvia KIP 6KW". That is a menu of
# heaters the buyer picks from, not what this unit draws.
W_EXCLUDE = re.compile(
    r"per panel|each panel|bulb|light|speaker|chromotherapy|"
    r"\boptions?\b|selection required|choose your|select your|"
    # A WIRE-GAUGE TABLE STATES CIRCUIT CAPACITY, NEVER DRAW -- the same rule as
    # never deriving kW from volts x amps, applied to prose. SaunaLife G6's manual
    # reads "for powering heater 240V max. 11kW/46A, four wires 10AWG, 600V", and
    # that 11 kW became this cabin's rating even though the G6 ships WITHOUT a
    # heater at all. It is the largest heater the wiring supports.
    r"\bAWG\b|\bwires?\b|wire gauge|\bcable", re.I)

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
    return span_with_offset(text, match, pad)[0]


def span_with_offset(text, match, pad=70):
    """(span, where the matched number starts INSIDE that span).

    The offset exists so a later rule can say WHAT the number sits beside
    without re-searching the span and guessing which occurrence was the reading.
    `scripts/extract_manual_specs.py` binds a rating to the model number that
    precedes it, and a Golden Designs cover line carries two of each:
    "GDI-8503-01 - 240VAC 30AMP Circuit Required (6kW Heater) GDI-8506-01 -
    240VAC 40AMP Circuit Required (8kW Heater)". Which model owns which rating
    is decided by position, so position is recorded rather than re-derived.

    The whitespace collapse is applied to the prefix separately and lstripped,
    which reproduces exactly what `.strip()` does to the head of the full span --
    so the offset indexes the string that is stored, not the raw page text.
    """
    lo, hi = max(0, match.start() - pad), min(len(text), match.end() + pad)
    span = re.sub(r"\s+", " ", text[lo:hi]).strip()
    head = re.sub(r"\s+", " ", text[lo:match.start()]).lstrip()
    return span, len(head)


def read_kw(text, field, url=None):
    """Stated heater kW. Returns every reading; never derives, never averages.

    W_EXCLUDE applies here too. It used to guard only read_watts, so "6KW per
    panel" was rejected when written in watts and accepted when written in kW --
    one rule, two answers, decided by the unit the manufacturer happened to use.
    """
    out = []
    for m in KW_RX.finditer(text):
        sp, at = span_with_offset(text, m)
        if W_EXCLUDE.search(sp):
            continue
        out.append({"kw": float(m.group(1)), "basis": "traditional_heater_kw",
                    "source_field": field, "source_url": url, "span": sp, "at": at})
    return out


def read_watts(text, field, url=None):
    """Stated rated draw in watts, comma-aware. Returns every reading."""
    out = []
    for m in W_RX.finditer(text):
        sp, at = span_with_offset(text, m)
        if W_EXCLUDE.search(sp):
            continue
        out.append({"kw": round(float(m.group(1).replace(",", "")) / 1000.0, 3),
                    "basis": "infrared_rated_watts", "source_field": field,
                    "source_url": url, "span": sp, "at": at})
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
    # KNOWN-NEGATIVE controls, every one a real string from the 142-manual run.
    # Each was accepted before the fix, and two of them OVERRODE a correct 6.0 kW
    # metafield through tier-1 precedence. A guard that has only known-positive
    # controls has never been shown to refuse anything.
    for text, why in (
        ("CTC2245W Serenity Barrel Sauna", "a SKU is not a wattage"),
        ("CTC2345W Tranquility Barrel Sauna", "a SKU is not a wattage"),
        ("Product ID CTC2245W CT Serenity Barrel Sauna", "a SKU in a parts list"),
        ("Powering lights/vent 120V max. 1kW/9A, wires three 16AWG",
         "a lighting circuit is not the heater"),
        ("Heater Option (Selection Required) Designer B Electric Heater - 6KW",
         "a menu of heaters is not this unit's rating"),
        ("for powering heater 240V max. 11kW/46A, four wires 10AWG, 600V",
         "a wire-gauge table states circuit capacity, not draw"),
    ):
        got = read_kw(text, "t") + read_watts(text, "t")
        if got:
            fails.append(f"known-negative accepted ({why}): {text!r} -> "
                         f"{[g['kw'] for g in got]}")
    # ...and the fix must not have cost us the real readings beside them.
    for text, want, why in (
        ("Total power:1650W DYN-6225-02", 1.65, "a stated total"),
        ("Finnmark Designs Hybrid = 15a 120v 1750 watts", 1.75, "an FAQ table"),
        ("240VAC 30AMP Circuit Required (6kW Heater)", 6.0, "a variant table"),
    ):
        got = read_kw(text, "t") + read_watts(text, "t")
        if not got or got[0]["kw"] != want:
            fails.append(f"known-positive lost ({why}): {text!r} -> {got}")

    # The offset must index the STORED span, not the raw text. If these drift,
    # every model binding downstream reads the wrong neighbourhood.
    for text, want in (
        ("  \n\n  Rated   power:  1,800 watts  ", "1,800 watts"),
        ("GDI-8503-01 - 240VAC 30AMP Circuit Required (6kW Heater)", "6kW"),
    ):
        got = read_kw(text, "t") + read_watts(text, "t")
        if not got:
            fails.append(f"offset control did not parse: {text!r}")
            continue
        sp, at = got[0]["span"], got[0]["at"]
        if not sp[at:].startswith(want):
            fails.append(f"span offset does not point at the number: "
                         f"{sp!r}[{at}:] = {sp[at:at + 12]!r}, wanted {want!r}")

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
