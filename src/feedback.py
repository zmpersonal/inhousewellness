"""Self-improvement loop: collect -> score -> adjust.

Built before autonomy, not bolted on after. The collect and score halves are
complete. The adjust half is wired but runs dry_run=True: it logs what it WOULD
change and changes nothing.

The loop proposes; it does not widen its own permissions. Everything outside
ALLOWED_KNOBS is a REVIEW for the human, and the allow-list itself is not a knob.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
from collections import defaultdict

# ---------------------------------------------------------------- permissions
# The loop may tune these.
ALLOWED_KNOBS = frozenset({
    "archetype_mix",
    "keyword_priority",
    "board_assignment",
    "posting_time",
    "satellite_rotation_order",
})

# The loop may NEVER touch these. Listed explicitly so a proposal naming one is
# rejected by identity, not by omission.
FORBIDDEN_KNOBS = frozenset({
    "validator", "gates", "health_claim_rules", "inh_floor",
    "brand_palette", "typography", "card_layouts", "cadence_ceiling",
    "allowed_knobs", "forbidden_knobs", "guardrails",
})

# ---------------------------------------------------------------- guardrails
MIN_SEGMENT_POSTS = 30        # never act on noise
REVERT_AFTER_DAYS = 14        # a change that does not move its metric reverts
PRIMARY_METRIC = "reach"
INH_DOMAIN = "inhousewellness.com"
SECONDARY_METRIC = "saves"


class LoopHalted(Exception):
    pass


# ---------------------------------------------------------------- collect
def collect(buffer_metrics, blotato_top_posts, published_log):
    """Join platform analytics back to our own published rows.

    buffer_metrics:      {channel_id: {metric: value}} -- Pinterest (the only source)
    blotato_top_posts:   [ {id, platform, content, latestMetrics{...}}, ... ]
    published_log:       [ {post_id, platform, item_id, archetype, board,
                            link_domain, published_at, external_id}, ... ]

    Rows we cannot join are reported, never guessed at.
    """
    by_external = {str(r.get("external_id")): r for r in published_log if r.get("external_id")}
    joined, unmatched_platform, unmatched_ours = [], [], []

    for post in blotato_top_posts or []:
        rec = by_external.get(str(post.get("id")))
        if not rec:
            unmatched_platform.append(post.get("id"))
            continue
        m = (post.get("latestMetrics") or {}).get("metrics", {}) or {}
        joined.append({**rec,
                       "reach": _num(m.get("reach_count") or m.get("viewsCount")),
                       "saves": _num(m.get("saves") or m.get("savesCount")),
                       "source": "blotato"})

    # Pinterest: Buffer reports aggregates only, never per-post. Attribute at the
    # channel level and say so -- do not fabricate per-pin numbers.
    pin_rows = [r for r in published_log if r.get("platform") == "pinterest"]
    pinterest_aggregate = None
    if buffer_metrics and pin_rows:
        agg = {m["type"]: m["value"] for m in buffer_metrics.get("metrics", [])}
        pinterest_aggregate = {
            "posts": agg.get("postCount"),
            "reach": agg.get("impressions"),
            "saves": agg.get("saves"),
            "engagement_rate": agg.get("engagementRate"),
            "granularity": "channel-aggregate",
            "note": ("Buffer's free plan exposes aggregates only, over a rolling "
                     "31-day window. Per-pin reach is NOT available, so Pinterest "
                     "segments cannot be scored per-post."),
        }

    for r in published_log:
        if r.get("platform") != "pinterest" and not any(
                j["post_id"] == r["post_id"] for j in joined):
            unmatched_ours.append(r["post_id"])

    return {
        "joined": joined,
        "pinterest_aggregate": pinterest_aggregate,
        "unmatched_platform_posts": unmatched_platform,
        "unmatched_our_posts": unmatched_ours,
        "collected_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------- score
SEGMENTS = ("archetype", "platform", "link_domain", "board")


def score(collected, segments=SEGMENTS):
    """Rolling win-rate per segment. Primary reach, secondary saves.

    A segment below MIN_SEGMENT_POSTS is reported with enough_data=False and is
    not eligible to drive any adjustment.
    """
    rows = collected["joined"]
    overall = _mean([r["reach"] for r in rows]) if rows else 0.0

    out = {}
    for seg in segments:
        buckets = defaultdict(list)
        for r in rows:
            key = r.get(seg)
            if key is not None:
                buckets[key].append(r)
        out[seg] = {}
        for key, rs in sorted(buckets.items()):
            reach = [r["reach"] for r in rs]
            saves = [r["saves"] for r in rs]
            n = len(rs)
            out[seg][key] = {
                "n": n,
                "mean_reach": round(_mean(reach), 1),
                "median_reach": _median(reach),
                "mean_saves": round(_mean(saves), 2),
                # win-rate = share of posts beating the overall mean
                "win_rate": round(sum(1 for x in reach if x > overall) / n, 3) if n else 0.0,
                "enough_data": n >= MIN_SEGMENT_POSTS,
            }
    return {"overall_mean_reach": round(overall, 1),
            "n_posts": len(rows), "segments": out,
            "pinterest_aggregate": collected.get("pinterest_aggregate")}


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs):
    if not xs:
        return 0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


# ---------------------------------------------------------------- adjust
class Proposal:
    def __init__(self, knob, change, evidence, expected_metric):
        self.knob = knob
        self.change = change
        self.evidence = evidence
        self.expected_metric = expected_metric
        self.created = dt.date.today().isoformat()

    @property
    def allowed(self):
        return self.knob in ALLOWED_KNOBS and self.knob not in FORBIDDEN_KNOBS

    def learnings_entry(self):
        status = "applied" if self.allowed else "REVIEW — outside the allow-list"
        return (
            f"\n### {self.created} — loop: {self.knob}\n"
            f"**Status:** {status} · **Metric:** {self.expected_metric} · "
            f"**Revert if unmoved by:** "
            f"{(dt.date.today() + dt.timedelta(days=REVERT_AFTER_DAYS)).isoformat()}\n\n"
            f"**Change:** {self.change}\n\n"
            f"**Evidence:** {self.evidence}\n")

    def __repr__(self):
        return f"<Proposal {self.knob} allowed={self.allowed}>"


def propose(scored, broken_post_rate=0.0, *, dry_run=True):
    """Derive bounded proposals. Halts outright if any post broke.

    Returns (proposals, applied, notes). With dry_run=True nothing is applied,
    ever -- `applied` comes back empty and the proposals are logged only.
    """
    notes = []
    if broken_post_rate > 0:
        raise LoopHalted(
            f"broken-post rate is {broken_post_rate:.1%}, not zero — the loop halts "
            f"regardless of reach. Fix the breakage before tuning anything.")

    proposals = []
    seg = scored["segments"]

    arche = {k: v for k, v in seg.get("archetype", {}).items() if v["enough_data"]}
    if len(arche) >= 2:
        best = max(arche, key=lambda k: arche[k]["mean_reach"])
        worst = min(arche, key=lambda k: arche[k]["mean_reach"])
        if arche[best]["mean_reach"] > arche[worst]["mean_reach"] * 1.3:
            proposals.append(Proposal(
                "archetype_mix",
                f"shift 5 points of weight from {worst!r} to {best!r}",
                f"{best} mean reach {arche[best]['mean_reach']} over n={arche[best]['n']}; "
                f"{worst} mean reach {arche[worst]['mean_reach']} over n={arche[worst]['n']}",
                "monthly impressions"))
    else:
        notes.append(
            f"archetype: no segment has reached the {MIN_SEGMENT_POSTS}-post minimum "
            f"({ {k: v['n'] for k, v in seg.get('archetype', {}).items()} }) — no proposal")

    # Satellite rotation order is a knob over SATELLITES only. INH is not in the
    # rotation -- its share is fixed by the 70% floor, which the loop cannot touch.
    dom = {k: v for k, v in seg.get("link_domain", {}).items()
           if v["enough_data"] and k != INH_DOMAIN}
    if len(dom) >= 2:
        best = max(dom, key=lambda k: dom[k]["mean_reach"])
        proposals.append(Proposal(
            "satellite_rotation_order",
            f"move {best!r} earlier in the rotation",
            f"{best} mean reach {dom[best]['mean_reach']} over n={dom[best]['n']}",
            "monthly impressions"))

    applied = []
    if not dry_run:
        applied = [p for p in proposals if p.allowed]      # not reachable in Round 2
    else:
        notes.append(f"dry_run=True — {len(proposals)} proposal(s) logged, none applied")

    for p in proposals:
        if not p.allowed:
            notes.append(f"REVIEW: {p.knob!r} is outside the allow-list; "
                         f"the loop proposes, it does not apply")
    return proposals, applied, notes


def append_learnings(proposals, path="LEARNINGS.md"):
    """Every adjustment writes a dated, evidenced entry."""
    if not proposals:
        return 0
    p = pathlib.Path(path)
    with p.open("a") as fh:
        for pr in proposals:
            fh.write(pr.learnings_entry())
    return len(proposals)
