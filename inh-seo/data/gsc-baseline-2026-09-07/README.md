# Search Console baseline — 28 days to 5 September 2026

Taken immediately before the Round 2 theme publish (7 September 2026). This is the **before**
for that change, and the canonical source for position and traffic on this site.

---

# ⚠️ READ THIS BEFORE COMPARING ANYTHING TO THIS BASELINE

## You must exclude anchor rows, or you will report a phantom 31% CTR improvement

`Pages.csv` contains **77 anchor-variant rows** — URLs ending `#aufguss`, `#specs`, `#price`
and so on. Google generates them from jump-to-section links. They are **the same SERP
appearance counted again under a fragment URL**.

They carry **25,856 impressions and 2 clicks**.

| | Impressions | Clicks | CTR |
|---|---|---|---|
| As GSC reports it | 108,117 | 548 | **0.51%** |
| Anchor rows | 25,856 | 2 | 0.01% |
| **Excluding anchors** | **82,261** | **546** | **0.66%** |

**Excluding anchor rows raises measured CTR from 0.51% to 0.66% — a 31% relative
difference, from filtering alone, with nothing about the site having changed.**

If a later comparison drops anchor rows (because the pages stopped earning jump-links, or
because someone filtered them out) while this baseline keeps them, the delta will look like a
31% CTR win that never happened.

**Rule: filter `#` out of `Top pages` on BOTH sides of any comparison.**

```python
rows = [r for r in rows if '#' not in r['Top pages']]
```

It is worst on the highest-traffic pages, which is where a comparison will focus:

| Page | Base row | Anchor rows | Anchors as % of impressions |
|---|---|---|---|
| `/blogs/saunas/arcadia-barrel-sauna-guide` | 5,103 impr | 9,223 impr / 2 clicks | **64%** |
| `/blogs/saunas/dynamic-saunas-review` | 2,237 | 1,886 / 0 | **46%** |
| `/blogs/saunas/what-is-a-german-sauna` | 23,587 | 11,727 / 0 | **33%** |

`Queries.csv` is **not** affected — it aggregates by query, not URL. Query-level figures are
safe to compare as-is.

## Second caveat: `Queries.csv` is capped at 1,000 rows

The export holds exactly 1,000 query rows totalling **38,244 impressions**, against 108,117
in `Pages.csv`. **About 65% of impressions sit in a long tail this file does not contain.**

The cap is applied **by impressions**, so what is missing is the tail, not a random sample.
Any extrapolation from this file describes the head of the distribution only — and since the
long tail skews more specific and more commercial, query-level CTR read from this file is
**conservative**, not optimistic.

---

## The numbers

| | Clicks | Impressions | CTR |
|---|---|---|---|
| **Site total** | **548** | **108,117** | 0.51% (0.66% ex-anchors) |
| Blog · 165 URLs | 487 (88.9%) | 93,201 | 0.52% |
| Product · 434 URLs | 44 (8.0%) | 10,513 | 0.42% |
| Home/other | 11 (2.0%) | 792 | 1.39% |
| **Collection · 86 URLs** | **5 (0.9%)** | **3,168** | **0.16%** |

Five clicks across 86 collection URLs in 28 days. Top ten collections by impressions: zero
clicks each, positions 23–58.

Organic sessions ≈ **590/month**. The strategy document's claim of ~1,900 was **3× too high**;
any target built on it needs restating.

## Position: this file supersedes the third-party trackers

For the `german sauna` cluster: Semrush said **#2**. Ubersuggest said **zero top-3
positions**. Search Console says **3.8–5.9**. Neither tracker was right, in either direction.
**Use Search Console.**

## Provenance

Filters: Search type Web, Last 28 days. Exported 7 September 2026.

Two zip files were supplied. Their contents are **byte-identical** — `Pages.csv` and
`Queries.csv` diff clean; the `(1)` file differed only in zip metadata and was removed.

Full analysis, including the intent breakdown that reframes what these numbers mean:
`reports/gsc-baseline-investigation.md`.
