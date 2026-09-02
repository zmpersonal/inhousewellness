"""Banned health-claim detection (adjustment A2).

This audience is 40-60, frequently managing blood pressure, cardiac risk,
joint pain or sleep issues, and the machine is unattended. Health claims are
gated in CODE, not in prose guidance to the model. Published captions that
motivated this list include "lifelong detox", "insane benefits" and
"your secret weapon".

Every rule returns a (code, matched_text) so a rejection can name the phrase.
"""
import re

# (code, pattern, human explanation)
_RULES = [
    # --- Disease treatment / cure claims -------------------------------
    ("DISEASE_TREATMENT", r"\b(?:cure[sd]?|curing|treat(?:s|ed|ing|ment)?|heal(?:s|ed|ing)?|reverse[sd]?|reversing|prevent(?:s|ed|ing)?)\b[^.!?\n]{0,40}\b(?:blood\s*pressure|hypertension|cardiovascular\s*disease|heart\s*disease|depression|insomnia|arthritis|diabetes|dementia|alzheimer'?s|cancer|stroke)\b",
     "claims to treat, cure, reverse or prevent a named disease"),
    ("DISEASE_TREATMENT", r"\b(?:blood\s*pressure|hypertension|cardiovascular\s*disease|heart\s*disease|depression|insomnia|arthritis|diabetes|dementia|alzheimer'?s|cancer|stroke)\b[^.!?\n]{0,40}\b(?:cured?|treated|reversed|eliminated|gone|fixed)\b",
     "claims a named disease is cured, reversed or eliminated"),
    ("DISEASE_TREATMENT", r"\b(?:lowers?|lowered|lowering|reduces?|reduced|reducing|drops?|dropped)\b[^.!?\n]{0,25}\b(?:your\s+)?blood\s*pressure\b",
     "unhedged claim about lowering blood pressure"),

    # --- Detox as a physiological mechanism ----------------------------
    # "detox" is only banned as a body-mechanism claim, not as a plain word.
    ("DETOX_MECHANISM", r"\b(?:detox(?:es|ed|ing|ify|ifies|ified|ification)?)\b[^.!?\n]{0,30}\b(?:your\s+)?(?:body|blood|cells?|liver|system|organs?|bloodstream)\b",
     "frames detox as a physiological mechanism"),
    ("DETOX_MECHANISM", r"\b(?:flush(?:es|ed|ing)?|purge[sd]?|purging|sweat(?:s|ed|ing)?\s+out|eliminate[sd]?|detox(?:es|ed|ing|ify|ifies|ified)?|clear(?:s|ed|ing)?|remove[sd]?|rid\s+(?:your|the)\s+body\s+of)\b[^.!?\n]{0,30}\b(?:toxins?|heavy\s*metals?|impurities|poisons?|pfas|microplastics)\b",
     "claims to flush, remove or detox toxins or heavy metals from the body"),
    ("DETOX_MECHANISM", r"\blifelong\s+detox\b", "'lifelong detox' -- a published caption that motivated this rule"),

    # --- Weight-loss claims -------------------------------------------
    ("WEIGHT_LOSS", r"\b(?:lose|losing|loses|lost|burn(?:s|ed|ing)?|shed(?:s|ding)?|melt(?:s|ed|ing)?|drop(?:s|ped|ping)?)\b[^.!?\n]{0,30}\b(?:weight|fat|calories|pounds?|lbs?|inches)\b",
     "makes a weight-loss or fat-burning claim"),
    ("WEIGHT_LOSS", r"\b(?:weight[-\s]?loss|fat[-\s]?burning|slimming)\b",
     "makes a weight-loss or fat-burning claim"),

    # --- Absolutes -----------------------------------------------------
    ("ABSOLUTE_CLAIM", r"\b(?:clinically\s+)?proven\b", "uses the absolute 'proven'"),
    ("ABSOLUTE_CLAIM", r"\bguarantee(?:s|d|ing)?\b", "uses the absolute 'guaranteed'"),
    ("ABSOLUTE_CLAIM", r"\beliminat(?:es?|ed|ing)\b", "uses the absolute 'eliminates'"),
    ("ABSOLUTE_CLAIM", r"\bcure[sd]?\b", "uses the absolute 'cures'"),
    ("ABSOLUTE_CLAIM", r"\b(?:100%|completely|totally|entirely)\s+(?:safe|effective|risk[-\s]?free)\b",
     "claims something is completely safe or effective"),
    ("ABSOLUTE_CLAIM", r"\bmiracle\b|\bmiraculous\b", "calls the effect a miracle"),

    # --- Medical advice / substitution for care ------------------------
    ("MEDICAL_ADVICE", r"\b(?:instead\s+of|replace[sd]?|no\s+need\s+for|skip|ditch|throw\s+out)\b[^.!?\n]{0,30}\b(?:medication|meds|prescription|your\s+doctor|medical\s+care|treatment)\b",
     "suggests substituting for medical care or medication"),
    ("MEDICAL_ADVICE", r"\b(?:doctors?\s+(?:don'?t|won'?t|hate)|big\s+pharma)\b",
     "uses medical-conspiracy framing"),

    # --- Hype register banned for this demographic (C5) ----------------
    ("HYPE_REGISTER", r"\binsane\b|\bcrazy\s+(?:benefits?|results?)\b", "hype register: 'insane'/'crazy'"),
    ("HYPE_REGISTER", r"\bsecret\s+weapon\b", "hype register: 'secret weapon'"),
    ("HYPE_REGISTER", r"\bgame[-\s]?chang(?:er|ing)\b", "hype register: 'game-changer'"),
    ("HYPE_REGISTER", r"\b(?:life[-\s]?changing|mind[-\s]?blowing|jaw[-\s]?dropping)\b", "hype register"),
]

_COMPILED = [(code, re.compile(pat, re.I), why) for code, pat, why in _RULES]

# Hedged framing that A2 requires on health-adjacent posts.
_HEDGES = re.compile(
    r"\b(?:may|might|can|could|appears?\s+to|suggests?|associated\s+with|linked\s+to|"
    r"some\s+evidence|limited\s+evidence|promising\s+but|preliminary|"
    r"we\s+still\s+don'?t\s+know|not\s+(?:well\s+)?established)\b", re.I)

# Topics that make a post health-adjacent and therefore require hedging.
_HEALTH_TOPIC = re.compile(
    r"\b(?:blood\s*pressure|cardiovascular|heart|cardiac|circulation|"
    r"depression|anxiety|mood|sleep|insomnia|arthritis|joint\s*pain|"
    r"inflammation|immune|recovery|longevity|cortisol|metabolic)\b", re.I)

# Topics where a contraindication note is warranted (cold plunge + cardiac).
_CONTRAINDICATION_TOPIC = re.compile(
    r"\b(?:cold\s*plunge|cold\s*water\s*immersion|ice\s*bath|contrast\s*therapy|"
    r"cold\s*exposure)\b", re.I)
_CONTRAINDICATION_NOTE = re.compile(
    r"\b(?:talk\s+to|check\s+with|consult|ask)\s+(?:your\s+)?(?:doctor|physician|cardiologist|gp)\b"
    r"|\bheart\s+condition\b|\bcardiac\s+(?:risk|condition)\b|\bmedical\s+(?:advice|clearance)\b"
    r"|\bif\s+you\s+have\s+(?:a\s+)?(?:heart|cardiac|blood\s*pressure)\b", re.I)


def find_banned_claims(text):
    """Return a list of (code, matched_text, why) for every banned claim found."""
    if not text:
        return []
    hits, seen = [], set()
    for code, rx, why in _COMPILED:
        m = rx.search(text)
        if m:
            key = (code, m.group(0).lower())
            if key not in seen:
                seen.add(key)
                hits.append((code, m.group(0), why))
    return hits


def is_health_adjacent(text):
    return bool(text and _HEALTH_TOPIC.search(text))


def has_hedge(text):
    return bool(text and _HEDGES.search(text))


def needs_contraindication(text):
    return bool(text and _CONTRAINDICATION_TOPIC.search(text))


def has_contraindication(text):
    return bool(text and _CONTRAINDICATION_NOTE.search(text))
