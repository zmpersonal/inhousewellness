# Backlink baseline — 2026-09-14

Live pull, Ubersuggest MCP, account `julian@zaragozamarketing.com` (tier1).
Supersedes the September 2026 table in `CLAUDE.md`, which is retained there
for the trend line.

## Profile totals

| Metric | Sept 2026 | 2026-09-14 | Δ |
|---|---|---|---|
| Domain Authority | 16 | **18** | +2 |
| Total backlinks | 198 | **196** | −2 |
| Referring domains (reported) | 68 | **66** | −2 |
| Referring domains (earned) | ~20 est. | **17 confirmed, 23 ceiling** | — |
| Top-3 organic positions | 0 | not re-measured | — |

`backlinks(one_per_domain=true, limit=70)` returned 66 rows against 66 reported
referring domains — complete coverage, no truncation at tier1, `done: true` on
first attempt.

**The reported figure is 66. It is never the number this project reports.**
The earned figure is 17.

## Classification — all 66 referring domains

| Class | Count | Share |
|---|---|---|
| **Earned** | **17** | 25.8% |
| Owned | 8 | 12.1% |
| Controlled profiles | 2 | 3.0% |
| Affiliate | 6 | 9.1% |
| Syndication (scraper copies) | 9 | 13.6% |
| Spam / auto-generated | 14 | 21.2% |
| Scraped local aggregators | 4 | 6.1% |
| Unresolved | 6 | 9.1% |
| **Total** | **66** | 100% |

### Earned (17)

| Domain | DR | Target | Anchor | rel |
|---|---|---|---|---|
| healthline.com | 91 | `/` | inhouse wellness | follow |
| eatthis.com | 83 | `/` | in house wellness | follow |
| womansworld.com | 66 | `/pages/featured-experts-consultants` | timur alptunaer md | follow |
| singlecare.com | 63 | `/pages/featured-experts-consultants` | inhouse wellness | follow |
| contra.com | 46 | `/` | — (bare) | follow |
| o2resortvalledeguadalupe.com | 41 | fire-pits post | fire pits | follow |
| terristeffes.com | 36 | golden-designs review | this golden designs sauna guide | follow |
| amritayogawellness.com | 34 | infrared-safety post | safety considerations for infrared heat yoga | follow |
| cedar-sense.com | 20 | arcadia-barrel guide | setup and performance guide | nofollow |
| sarawest.ca | 14 | fire-pits post | inhouse wellness ran an article | follow |
| davonex.com | 9 | low-EMF guide | low emf vs near zero emf saunas buyer's decision guide 2025 | nofollow |
| ruckusreviews.com | 7 | cold-plunge-under-2000 | mid range inflatable kits | follow |
| inlandsauna.com | 5 | sauna-wood-species | naked URL | follow |
| plungentubs.com | 5 | cold-plunge-maintenance | proper insulation also affects long term maintenance | nofollow |
| purerecoverylab.com | 4 | heavenly-heat review | inhousewellness.com review | nofollow |
| fitoverflab.com | 4 | `/collections/saunas` | inhouse wellness | follow |
| spalens.com | 3 | sensory-deprivation post | inhouse wellness 2024 | follow |

Thirteen of seventeen point at blog content, which is the shape Hard Rule 6
wants. `fitoverflab.com` is the one earned link landing on a collection page.

The four that matter are intact and all four are **follow** — confirming
Hard Rule 8. Had the audit trusted `backlinks_overview`, it would have
recorded every one of them as nofollow.

Weakest three by provenance, not by DR: `contra.com` (a contractor's
portfolio page listing the store as client work), `davonex.com` (an SEO
agency blog), `spalens.com` (spam score 12). All three are genuine
third-party pages and none matches an exclusion list, so they count — but
they are incidental mentions, not placements, and should not be read as
evidence any tactic is working.

### Owned (8 of 10) — excluded

besthomeinfraredsauna.com, infinitesauna.com, saunaimport.com,
tubsandsaunas.com, saunasfactorydirect.com, homenhealthy.com,
healthresearchdatabase.com, outdoorsteamsauna.com

`arcticsoak.com` and `commercialinfraredsauna.com` remain absent and
quarantined. Matches `owned.json` exactly — eight linking, two not.

### Controlled profiles (2) — excluded

pinterest.com/inhousewellness, inhousewellness.myshopify.com

### Affiliate (6) — excluded

eliterecoverywellness.com, zenergyrecovery.com, yardsanctuary.com,
smartlifehub.com, primehomegear.com, hottubsofstlouis.com

All six present, all six matching `affiliates.json`. Every one still uses an
exact-match commercial or malformed anchor product-page to product-page.

### Syndication (9)

Nine scraper copies of two stories — the Healthline heart-attack piece and
the Woman's World GLP-1 piece:

newsbreak.com, bnlistt.com, chairr.top, healthradar.net, vedanutrics.cfd,
trustedoptima.website, trustedoptima.site, myistyclan.com, hacka.click

These are not independent endorsements. They are the same two placements
counted nine more times, and they are the single largest reason the reported
figure overstates the profile.

### Spam / auto-generated (14) — disavow candidates

| Domain | Spam score | Shape |
|---|---|---|
| vickys.design | 80 | domain-list scraper |
| zhanhao.online | 61 | domain-list scraper |
| newsblogsports.site | 52 | unrelated Pinterest-tool spam |
| wants.cfd | 47 | "seo domain research" |
| knows.sbs | 47 | domain-list scraper |
| backlinkup.co | 19 | link-selling directory |
| research.mental-momentum.ai | 17 | auto-generated research aggregator |
| flrig.beesbuzz.biz | 16 | auto-generated Flickr tag page |
| westernrollercanaryassociation.org | 12 | off-topic injection into a canary-fanciers site |
| dondo.com | 7 | auto-generated AI "brand voice" page |
| openarticle.in | 4 | domain-list scraper |
| gridinsoft.ua | 2 | virus-scanner URL report |
| xploredomains.com | 2 | domain-list scraper |
| tunca.org | 5 | hash-URL page |

Recommend all fourteen to the disavow file. None was solicited; none can be
removed by asking.

### Scraped local aggregators (4)

blushlocal.net, ratelivo.com, poicircle.com, redsavia.com

`blushlocal.net` lists the business as "Austin, TX". Relevant to the
`data/identity.json` open item — a canonical NAP is needed before any
citation work, and before deciding whether Austin is even correct.

### Unresolved (6) — blocking the earned count

Five carry the paid-insertion anchor pattern already flagged in `CLAUDE.md`:

| Domain | Target | Anchor |
|---|---|---|
| momdaughts.com | red-light-therapy post | clinical research on red light therapy for skin |
| journalismband.com | cold-plunge-athletes post | at least 48 hours post workout |
| morpheus8london.com | red-light-therapy post | naked URL |
| lumiluxlimited.com | red-light-therapy post | photobiomodulation and collagen support |
| functionalacademy.org | functional-health-coaching post | modifiable lifestyle factors |

Three of five point at the same red-light-therapy article with mid-sentence
phrase anchors. That is the signature of a bought placement round, not
independent citation. **Provenance must be confirmed by a human who knows
whether these were paid for.** They are held out of the earned count until
then — if all five are legitimate, earned rises to 22.

Sixth: `xwifkv-j0.myshopify.com`, anchor `inhouse wellness+1medicalsaunas.com`
— an unconfigured Shopify store with a leaked template variable, same family
as the `homenhealthy.com` anchor. Still unclassified per `owned.json`.

## Open questions

1. **The two dropped domains cannot be identified.** No September referring-
   domain list exists anywhere in the repo — `linkbuilding/` has two commits,
   both dated today, and no file in the tree carries per-link data. Whether
   the loss was earned or junk is unrecoverable. Going forward this report is
   the snapshot; the next pull diffs against it. Time-boxed as instructed.
2. **Provenance of the five paid-pattern links** (above). Blocks a final
   earned figure.
3. **`xwifkv-j0.myshopify.com`** — owned, affiliate, or unrelated.
4. **Canonical NAP** (`data/identity.json`) — unresolved, and the local
   aggregators are already asserting an Austin, TX address.
5. **Top-3 organic positions not re-measured.** Carried at 0 from September;
   not verified in this pull.

## Reproduced by pipeline

**2026-09-14 — `pipelines/00_audit.py` reproduces this classification exactly
from live data: 17 earned / 10 owned / 6 affiliate / 9 syndication / 14 spam /
4 local aggregator / 6 unresolved, delta +0 in every class, and the earned set
matches this report domain for domain, not merely in count.** The analysis
above stands as written and is not restated here. From this run on, every pull
is archived to `data/snapshots/YYYY-MM-DD.json` and diffed against the previous
one, so open question 1 — two domains lost with no record of what they were —
cannot recur.

## Method note

Rel attributes in this report are taken from the per-link `nofollow` field.
`backlinks_overview` reported `follow: 0, noFollow: 66`, which is false —
see Hard Rule 8.
