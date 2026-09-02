"""Deterministic keyword-row -> blog-article matcher. No model calls, ever.

Scoring is IDF-weighted cosine similarity between the keyword and an article's
title + slug (+ summary at lower weight). Cosine, not raw overlap, because raw
overlap rewards short keywords built from corpus-common words: "what is an
infrared sauna" reduces to {infrared, sauna}, both of which appear in most
titles, and scored 1.00 against a brand review.

Two gates keep a plausible-but-wrong match from passing:
  * the keyword's RAREST token must appear in the article, else the score is
    heavily discounted -- that token is the head noun that makes the query
    specific ("electrical", "hemlock", "pregnant");
  * a floor threshold below which the row is BLOCKED rather than matched.

A blocked row is a good outcome. An invented URL is not.
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOP = frozenset("""
a an the and or of for to in on at is are am be been was were do does did done
your you my me it its this that these those what how why when where which who
whom can could will would should may might must if then than as by from with
into about over under out up down off no not so such own same too very just
i s t re ve ll d
""".split())

# Tuned against the real 103-row queue and the 109-article corpus.
MATCH_THRESHOLD = 0.40      # below this -> blocked, never guessed
# Calibrated by inspection against the real 103-row queue, not tuned to a target
# count. Above 0.40 the matches are defensible ("home sauna cost" ->
# home-sauna-steam-room-lifetime-operating-costs at 0.413). Below it they
# degrade into product reviews standing in for explainers ("what to wear in a
# sauna" -> dynamic-saunas-review at 0.325, "how to use a sauna" ->
# sauna-alzheimers at 0.376).
STRONG_MATCH = 0.62
RARE_TOKEN_PENALTY = 0.45   # multiplier when the head noun is absent

W_TITLE, W_SLUG, W_SUMMARY = 1.0, 1.0, 0.30


def _stem(t):
    """Light suffix normalisation. Without it "cost" never matches "costs" and
    "sauna" never matches "saunas" -- both fatal in this corpus."""
    for suf, keep in (("ies", 3), ("ses", 2), ("xes", 2), ("ing", 4), ("ed", 3), ("s", 3)):
        if t.endswith(suf) and len(t) - len(suf) >= keep:
            base = t[: -len(suf)]
            if suf == "ies":
                base += "y"
            return base
    return t


def tokens(s):
    return [_stem(t) for t in re.split(r"[^a-z0-9]+", (s or "").lower())
            if t and t not in STOP and len(t) > 2]


class _IDF(dict):
    """IDF table where an UNSEEN token scores as maximally rare, not minimally.

    A plain dict with .get(t, 1.0) gave corpus-absent tokens the LOWEST weight,
    which inverted the rare-token gate on exactly the queries that most needed
    blocking: "wallet", "pregnant", "acne", "hemlock" are absent from the corpus,
    so they were treated as common and the query matched on its filler words
    instead ("is it safe to take wallet into sauna" -> are-infrared-saunas-safe,
    scored 0.641 "strong"). An unseen token is maximally rare by definition.
    """

    def __init__(self, mapping, unseen):
        super().__init__(mapping)
        self.unseen = unseen

    def get(self, key, default=None):        # default is deliberately ignored
        return self[key] if key in self else self.unseen

    def __missing__(self, key):
        return self.unseen


def build_idf(articles):
    n = len(articles) or 1
    df = Counter()
    for a in articles:
        for t in set(tokens(a.get("title")) + tokens(a.get("slug")) + tokens(a.get("summary"))):
            df[t] += 1
    table = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
    unseen = math.log((n + 1) / 1) + 1.0     # as if df == 0
    return _IDF(table, unseen)


def _vec(article, idf):
    v = {}
    for field, w in (("title", W_TITLE), ("slug", W_SLUG), ("summary", W_SUMMARY)):
        for t in tokens(article.get(field)):
            v[t] = v.get(t, 0.0) + w * idf.get(t, 1.0)
    return v


def _cos(a, b):
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(x * x for x in a.values()))
    nb = math.sqrt(sum(x * x for x in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def score(keyword, article, idf, _cache={}):
    kw = tokens(keyword)
    if not kw:
        return 0.0
    kvec = {}
    for t in kw:
        kvec[t] = kvec.get(t, 0.0) + idf.get(t, 1.0)

    key = article["url"]
    avec = _cache.get(key)
    if avec is None:
        avec = _cache[key] = _vec(article, idf)

    s = _cos(kvec, avec)

    art_tokens = set(tokens(article.get("title"))) | set(tokens(article.get("slug")))
    # The rarest keyword token is the one that makes the query specific.
    rarest = max(set(kw), key=lambda t: idf.get(t, 1.0))
    if rarest not in art_tokens:
        s *= RARE_TOKEN_PENALTY

    kl = (keyword or "").lower().strip()
    if kl and (kl in (article.get("title") or "").lower()
               or kl.replace(" ", "-") in article.get("slug", "")):
        s = min(1.0, s + 0.25)

    return round(s, 4)


def best_match(keyword, articles, idf, top_n=3):
    ranked = sorted(((score(keyword, a, idf), a) for a in articles),
                    key=lambda t: (-t[0], t[1]["url"]))
    if not ranked:
        return 0.0, None, []
    return ranked[0][0], ranked[0][1], ranked[1:1 + top_n]


def verdict(s):
    if s >= STRONG_MATCH:
        return "strong"
    if s >= MATCH_THRESHOLD:
        return "weak"
    return "blocked"


# ---------------------------------------------------------------------------
# Subject compatibility gate
#
# Token similarity alone cannot separate "is sauna good for a cold" from
# "is-cold-plunge-good-for-women" (0.498) or "how hot should a sauna be" from
# "hot-tub-cold-plunge-combo" (0.433). Both are phrase-shape collisions across
# different products. The queue is 100% sauna keywords; the corpus is 20%
# cold-plunge. Without this gate the remap quietly points sauna pins at cold
# plunge articles, which is exactly the "plausible but wrong" outcome the
# withhold-beats-guess rule exists to prevent.
# ---------------------------------------------------------------------------

SUBJECTS = {
    "sauna":       r"\bsauna|saunas\b",
    "cold_plunge": r"\bcold[\s-]*plunge|ice[\s-]*bath|cold[\s-]*water[\s-]*immersion|plunge\b",
    "hot_tub":     r"\bhot[\s-]*tub|jacuzzi|swim[\s-]*spa\b",
    "red_light":   r"\bred[\s-]*light\b",
    "massage":     r"\bmassage[\s-]*chair\b",
    "float":       r"\bfloat[\s-]*(?:tank|therapy)|cryotherapy\b",
    "steam_room":  r"\bsteam[\s-]*room\b",
}
_SUBJ = {k: re.compile(v, re.I) for k, v in SUBJECTS.items()}

# Articles with no product subject at all (thermal science, HSPs, recovery)
# are treated as universally compatible -- they genuinely apply to any of them.
GENERIC_OK = True


def subjects(text):
    t = text or ""
    return {name for name, rx in _SUBJ.items() if rx.search(t)}


def article_subjects(article):
    return subjects(f"{article.get('title','')} {article.get('slug','')}")


def subject_compatible(keyword, article):
    """True when the keyword's product subject is actually covered by the article."""
    ks = subjects(keyword)
    if not ks:
        return True                       # keyword names no product -- no constraint
    a = article_subjects(article)
    if not a:
        return GENERIC_OK                 # generic thermal article, applies broadly
    return bool(ks & a)


def match_row(keyword, articles, idf):
    """Full deterministic match: score, then apply the subject gate.

    Returns (score, article, verdict, reason). Never invents a URL.
    """
    ranked = sorted(((score(keyword, a, idf), a) for a in articles),
                    key=lambda t: (-t[0], t[1]["url"]))
    # Walk down until a subject-compatible candidate appears.
    rejected_subject = None
    for s, a in ranked:
        if subject_compatible(keyword, a):
            if s >= STRONG_MATCH:
                return s, a, "strong", None
            if s >= MATCH_THRESHOLD:
                return s, a, "weak", None
            return s, a, "blocked", (
                f"best subject-compatible match scored {s:.3f}, below the "
                f"{MATCH_THRESHOLD} threshold — no article covers this keyword")
        if rejected_subject is None:
            rejected_subject = (s, a)
    if rejected_subject:
        s, a = rejected_subject
        return 0.0, None, "blocked", (
            f"no subject-compatible article exists; best token match "
            f"{a['slug']} ({s:.3f}) is about a different product")
    return 0.0, None, "blocked", "corpus is empty"
