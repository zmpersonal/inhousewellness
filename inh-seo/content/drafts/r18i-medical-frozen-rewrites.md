---
status: APPROVED 2026-09-18 (recommended version of each; #5 repoint to Finnmark). Built as scripts/apply/r18i-frozen-edit.mjs; NOT YET APPLIED — Admin token refused.
correction: in #4 the two 'spaces' around the empty anchor are U+00A0, not U+0020. This draft's FROM was typed from a display and matched 0x; the script's spec uses code-point escapes.
round: 18i
product: medical-frozen-plunge-1-cold-therapy (DRAFT, discontinued on quality grounds)
source-of-strings: live article bodies read 2026-09-18 ~14:08Z. Every FROM below is copied from the data, never retyped.
enumeration: 7 hrefs in 5 articles. Visible "Frozen" appears only inside the 4 recommending sentences (checked per
  article). There are no bare mentions or title attributes elsewhere, so nothing else needs to change.
---

# Medical Frozen Plunge 1: four recommending sentences, one repoint

**The problem.** Four sentences recommend the Plunge 1, and three of them do it for safety or reliability.
`/blogs/cold-plunge/cold-plunge-brand-we-dont-recommend` says *"We carry Frozen cold plunges and we do not
recommend them first."* The site contradicts itself, and the recommended product 404s.

**The rule for these drafts:** remove the recommendation and invent nothing in its place. Three of the four
are **deletions**. The sentence before each one already makes the paragraph's point without a product. The fourth
is a **heading change**: the recommendation there is a linked product name standing as a section heading.

---

## 1. `/blogs/wellness/heat-cold-pain-modulation-not-elimination`

This sits in the section *"Who Should Not Use Heat/Cold Without Medical Guidance"*. It attaches a risk claim
("to minimize risk") to a product, in the medical-caution section. 2 hrefs (one wraps a single space).

**FROM**
```html
<p>For at-home protocols, consider controlled equipment like the<a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy"> </a><a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy">Medical Frozen Plunge for controlled cold exposure</a> to minimize risk while maximizing consistency.</p>
```
**TO (recommended): delete the paragraph.** The "Evidence strength" line that follows still closes the section.

*Alternative, if the section should keep an at-home line.* It names what to control and makes no claim for any
equipment:
```html
<p>For at-home protocols, the two things to control are water temperature and time in the water; set both before you start, and agree them with your clinician if any of the conditions in this section apply to you.</p>
```

## 2. `/blogs/wellness/thermal-modalities-interfere-training-adaptation`

The product name, linked, **is** the section heading. That is a recommendation by placement. 1 href.

**FROM**
```html
<h3 id="h.s2sfup1fmnra"><a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy">Medical Frozen Plunge cold therapy tub</a></h3>
```
**TO** (the heading id is kept, so no jump link breaks):
```html
<h3 id="h.s2sfup1fmnra">Equipment for cold-water immersion</h3>
```
The paragraph under it is unchanged. It names no product. **For your read:** its second sentence, *"Clinic-grade
cold plunge tubs support standardized application aligned with evidence-based protocols"*, is generic
marketing register. It is left alone because it recommends nothing, but it could go.

## 3. `/blogs/wellness/heat-cold-inflammatory-timeline-musculoskeletal-injuries`

*"with reliable equipment"* is the property the product was withdrawn over. 1 href.

**FROM** (the last sentence of the paragraph)
```html
 For readers exploring structured cold exposure with reliable equipment, the <a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy">Medical Frozen Plunge for Cold Therapy</a> offers controlled temperature management.</p>
```
**TO: delete the sentence.** The paragraph then ends on its existing price-band sentence:
```html
</p>
```
Resulting paragraph end: *"…to premium systems ($10,000+) designed for consistent temperature control and durability."*

## 4. `/blogs/cold-plunge/cold-plunge-buying-mistakes`

This closes the section *"When a Purpose-Built Plunge Is Smarter"* and names the unit as the example for
*"performance and safety"*. 2 hrefs (one wraps a single space).

**FROM**
```html
<p>The<a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy"> </a><a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy">Medical Frozen Plunge 1 cold therapy tub</a> is one example of a purpose-built option for buyers prioritizing performance and safety over building their own.</p>
```
**TO (recommended): delete the paragraph.** The sentence before it already makes the section's case, *"…who wants
predictable performance, integrated filtration, and a real warranty"*.

*Alternative, if the section should end on something to do.* It gives buying guidance, not a product:
```html
<p>Purpose-built units differ most in the lowest temperature they will hold, the chiller's capacity, and how the tub is insulated. Compare those three before you compare prices.</p>
```

**Found in passing, not in scope:** a few lines below, this article shows the literal text
`<a id="mistake-7"></a>` to readers. That is an escaped anchor rendered as visible copy, the
`markdown-anchor-literal` shape `scan-broken-copy` screens for. Reported, not changed.

---

## 5. The fifth link: a repoint, not a rewrite

`/blogs/wellness/beyond-sauna-heat-cold-exposures-hsp-map`, section *"Summary Verdicts by Goal"*:
```html
<p>If you want controlled cold at home, <a href="https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy">consider options designed for consistency and safety</a>.</p>
```
The sentence does not name the product, so only the href changes and the anchor text stays as it is.

**Proposed target: Finnmark SoulCold, `/products/finnmark-soulcold-plunge`, $9,320.** Re-read on the public
storefront today: available. It is ACTIVE with sell-when-out-of-stock off (DENY), per the Admin read earlier
this session.

- **It is the closest match in form.** It is a freestanding reclined one-person tub, like the Plunge 1 (FR-1-CP,
  70" × 33" × 36", $9,649). Its exterior is 75" × 35" × 30", and it holds 34–108°F, so it also heats. It is $329
  cheaper.
- **The Icetubs IceBarrel ($9,800) is a different form factor.** It is an upright barrel: you sit rather than
  recline. Its 92.5 gallons is closer to the Plunge 1's 97, but the way you use it is different. It is not
  proposed.

**One thing to decide.** The anchor text says *"options"*, plural, and a repoint to one product narrows it to
one. If that reads wrong, the alternative is `/collections/cold-plunge`, which keeps the plural true and routes
to the category.

---

**Totals if approved as recommended:** 6 hrefs removed (3 deletions and 1 heading), 1 href repointed. No
sentence names Frozen afterwards. The only change to visible text in the heading edit is the heading itself.
These go through the article proof runner (`scripts/apply/r18i-article-proof.sh`):
- injection tests must land and be refused;
- restore, then the no-op check;
- the tamper premise, then the refusal with live unchanged;
- the link multiset and masked visible text must match the declared changes exactly.
