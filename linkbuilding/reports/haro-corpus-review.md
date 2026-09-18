# HARO corpus review — is the claim bank mis-scoped, or is the channel quiet?

Round 9 · generated from `data/links.db` · 112 distinct HARO requests, 2026-09-15 to 2026-09-18 (8 digests, 162 rows)

## What this document is, and is not

It is **evidence for a human decision about scope.** Nothing here changed the filter, the claim bank, the anchor lists, or any threshold. No draft was written and nothing was sent.

The competence classification in the last column is **my reading, not a code gate.** It is published per item precisely so it can be disagreed with line by line, and it feeds nothing.

## The question

162 HARO items produced **0 clinical answerable** and 14 marginal for Dr. Alptunaer. HARO produced **all four** of his proven links. Both cannot be right, and the hypothesis was that `claims.json` is scoped to the *product* — sauna, heat, cold, recovery — rather than to the *expert's competence*.

## The answer, in one table

| Of 112 distinct HARO requests | Count | Share |
|---|---|---|
| **A — within the general competence of a practising physician** | **9** | 8% |
| B — medical, but gated on a specialty the roster does not state | 16 | 14% |
| **C — outside any medical scope at all** | **87** | 78% |

**The hypothesis is half right, and the half it gets wrong matters more.**

The bank *is* narrower than the expert: widening it from the product to general medicine would take HARO from **0 reachable to at most 9** over these four days — about two a day. That is real, and it is the difference between a dead channel and a working one.

But **87 of 112 requests — 78% — are outside medicine entirely.** Holiday gift guides, Route 66 road trips, greasing baking pans, artificial Christmas trees, squirrel-proof bird feeders, cybersecurity for CISOs. HARO is a general-purpose press-query newsletter that happens to carry a health category, not a medical channel. No scoping decision reaches those.

So the answer to "mis-scoped bank or quiet channel?" is **both, in that order**: fix the scope and the channel goes from 0 to roughly 2 a day. It does not go to 20.

### Tier B is the number that cannot be settled here

16 requests are squarely medical but call for a named specialty — dermatology (4), veterinary (4), psychiatry or behavioural neurology (3), reproductive medicine (2), transplant, plastic surgery, dentistry. **`data/experts.json` records Dr. Alptunaer's credential as `MD` and states no specialty.** Whether those 16 are reachable is a fact about him that this project does not hold. If he is a dermatologist, A becomes 13. That is a question for a human, and it is the single cheapest thing that would sharpen every number above.

---

## Two concrete defects the corpus exposed

### 1. The same question, opposite outcomes, decided by one word

Red light therapy for skin arrived on both platforms in the same week.

| | Connectively | HARO |
|---|---|---|
| Wording | "red or **near-infrared** light" | "**light-based** skin treatments" |
| Matched | `infrared` | nothing |
| Bucket | **answerable**, alptunaer | **rejected** |

Same subject, same week, same expert. The gate is keyed to product vocabulary, not to subject matter, and this is what that looks like from the outside.

### 2. `infrared` is in the filter and in NO claim in the bank

The rejection reason the pipeline printed for the match above reads: *"modality ['infrared'] named; the claim bank covers this directly."*

It does not. **Zero of the 30 claims mention infrared, and zero are about skin, dermatology or photobiomodulation.** The bank's topic list is `heat, cold, cardiovascular, sleep, mood, recovery, safety…` — nothing optical.

So the one clinical answerable in the entire corpus is a match on a filter keyword with no claim behind it. Had the bank been approved and a drafter existed, that row would have been pitched under a physician's name with nothing to say. **The filter's vocabulary and the bank's contents have drifted apart, and nothing currently checks that they agree.**

Neither defect was fixed. Both are out of Round 9's scope.

---

## The 14 Alptunaer marginals, quoted in full

These are the closest the clinical filter came. **14 rows, 10 distinct requests** — HARO repeats queries across its three daily editions, so the duplication is visible here too.

### M01 · Bergen Magazine

- **HARO category:** Lifestyle and Entertainment
- **Anchor that matched:** `spa`
- **Why marginal:** wellness-adjacent (['spa']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Do you pamper your pet? Feed him/her special food? Send him/her to doggy daycare or a pet spa?
> Use a mobile groomer? How do you protect your pet from getting lost (GPS tracker, microchip,
> etc.)? Has your pet ever been lost? If you're a pet person LOCATED IN BERGEN COUNTY, NJ, I'd
> love to speak with you. I'd also like to interview high-end providers of pet services IN BERGEN
> COUNTY.

### M02 · Bergen Magazine

- **HARO category:** Lifestyle and Entertainment
- **Anchor that matched:** `spa`
- **Why marginal:** wellness-adjacent (['spa']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Do you pamper your pet? Feed him/her special food? Send him/her to doggy daycare or a pet spa?
> Use a mobile groomer? How do you protect your pet from getting lost (GPS tracker, microchip,
> etc.)? Has your pet ever been lost? If you're a pet person LOCATED IN BERGEN COUNTY, NJ, I'd
> love to speak with you. I'd also like to interview high-end providers of pet services IN BERGEN
> COUNTY.

### M03 · East End Taste

- **HARO category:** Gift Bags
- **Anchor that matched:** `wellness`
- **Why marginal:** wellness-adjacent (['wellness']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> East End Taste is accepting submissions for our 2026 Holiday Gift Guide, featuring elevated,
> thoughtful and distinctive gifts for the holiday season. We are seeking products and giftable
> experiences across the following categories: Food and drink Travel and hospitality Fashion and
> accessories Beauty and wellness Home and entertaining Children and family Luxury gifts Please
> include the product or experience name, a concise description, retail price, purchasing link,
> holiday availability, high-resolution imagery and the specific reason it would appeal to East
> End Taste readers. Complimentary editorial consideration is available but does not guarantee
> inclusion. Products should be available to U.S. consumers for purchase or delivery during the
> holiday season.

### M04 · Famadillo

- **HARO category:** Gift Bags
- **Anchor that matched:** `self-care`
- **Why marginal:** wellness-adjacent (['self-care']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> We’re currently seeking products for hands-on review for an upcoming Gift Guide for the Person
> Who Has Everything. We’re looking for unique, unexpected, clever, useful, and memorable gift
> ideas that stand out from the usual holiday gifts. Products of interest include innovative
> gadgets, food and beverages, home and lifestyle products, beauty and self-care, tech, travel,
> entertaining, hobbies, personalized gifts, experiences, and unusual finds. We are **only seeking
> product samples for hands-on editorial review**. Brands and PR representatives with products
> available to send for review are invited to reach out with product information, MSRP, website
> link, images, and sample details.

### M05 · Famadillo.com

- **HARO category:** Health and Pharma
- **Anchor that matched:** `spa, recovery`
- **Why marginal:** wellness-adjacent (['spa', 'recovery']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> I'm working on an experiential Famadillo story in the same spirit as our Manhattan Laser Spa PRP
> Treatment Review (https://famadillo.com/manhattan-laser-spa-prp-treatment-review/). Famadillo is
> seeking reputable U.S. plastic surgery practices that offer mommy makeover procedures for a
> first-hand, independently reported review. We are looking for practices with a board-certified
> plastic surgeon and an accredited facility that may be willing to host a Famadillo writer for an
> experience from consultation through recovery. Specifically, we need practices willing to
> disclose: - What is being offered (complimentary, discounted, or standard pricing) - Surgeon
> credentials and board certification - Practice location - What procedures are included in the
> mommy makeover package and how they are typically customized - Recovery expectations - Whether
> the practice can accommodate editorial access for a writer to document the full journey Please
> note: Any medical decisions remain between the writer and the qualified clinician. Participation
> or hosting does not guarantee positive coverage. Any complimentary or hosted services will be
> clearly disclosed in the final piece. We do not request medical advice from unqualified sources.
> If your practice is interested and meets these criteria, please respond with details about your
> mommy makeover offering and willingness to host a Famadillo writer for an editorial review.

### M06 · Famadillo.com

- **HARO category:** Health and Pharma
- **Anchor that matched:** `spa, recovery`
- **Why marginal:** wellness-adjacent (['spa', 'recovery']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> I'm working on an experiential Famadillo story in the same spirit as our Manhattan Laser Spa PRP
> Treatment Review (https://famadillo.com/manhattan-laser-spa-prp-treatment-review/). Famadillo is
> seeking reputable U.S. plastic surgery practices that offer mommy makeover procedures for a
> first-hand, independently reported review. We are looking for practices with a board-certified
> plastic surgeon and an accredited facility that may be willing to host a Famadillo writer for an
> experience from consultation through recovery. Specifically, we need practices willing to
> disclose: - What is being offered (complimentary, discounted, or standard pricing) - Surgeon
> credentials and board certification - Practice location - What procedures are included in the
> mommy makeover package and how they are typically customized - Recovery expectations - Whether
> the practice can accommodate editorial access for a writer to document the full journey Please
> note: Any medical decisions remain between the writer and the qualified clinician. Participation
> or hosting does not guarantee positive coverage. Any complimentary or hosted services will be
> clearly disclosed in the final piece. We do not request medical advice from unqualified sources.
> If your practice is interested and meets these criteria, please respond with details about your
> mommy makeover offering and willingness to host a Famadillo writer for an editorial review.

### M07 · Health Insiders

- **HARO category:** Health and Pharma
- **Anchor that matched:** `wellness, hydration`
- **Why marginal:** wellness-adjacent (['wellness', 'hydration']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Hello! I’m a writer working on an article for a health and wellness publication about the best
> collagen creams. I’m seeking expert input from board-certified dermatologists, cosmetic
> dermatologists, or qualified skincare professionals. If interested, please share your
> perspective on: Can topical collagen actually penetrate the skin deeply enough to stimulate or
> rebuild collagen, or does it primarily support surface hydration and temporary plumping? What
> role do ingredients such as hydrolyzed collagen, hyaluronic acid, peptides, and retinol play in
> collagen-focused creams? What should consumers look for when evaluating a collagen cream’s
> ingredient quality, texture, sourcing, and formulation? Are collagen creams appropriate for
> sensitive, dry, oily, or acne-prone skin? What side effects or ingredients—such as fragrance,
> retinoids, or heavier occlusives—should consumers watch for? How long should someone use a
> collagen cream before evaluating whether it is benefiting skin hydration, texture, or the
> appearance of fine lines? Your expertise will help readers understand the realistic benefits of
> topical collagen, choose better-formulated creams, and avoid exaggerated anti-aging claims. Full
> attribution will be provided. Thanks & Regards Rodgers Panato Health & Wellness Writer Bio
> Profile – https://www.healthinsiders.com/profile/rodgers

### M08 · Health Insiders

- **HARO category:** Health and Pharma
- **Anchor that matched:** `wellness`
- **Why marginal:** wellness-adjacent (['wellness']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Hello! I’m a writer working on an article for a health and wellness publication about the best
> dental and oral health supplements. I’m seeking expert input from dentists, dental hygienists,
> registered dietitians, or oral-health specialists. If interested, please share your perspective
> on: What evidence supports ingredients such as xylitol, hydroxyapatite, oral probiotics,
> calcium, vitamin D, and vitamin C for oral wellness? How can these ingredients support enamel,
> gum health, oral bacteria balance, and breath freshness? Are oral probiotics effective, and
> should consumers look for products that identify specific probiotic strains and amounts? What
> should consumers look for regarding ingredient dosage, formula transparency, and third-party
> testing? Can oral health supplements replace brushing, flossing, professional cleanings, or
> dental treatment? Are there safety concerns or special considerations for people with dental
> conditions, medication use, or allergies? Your expertise will help readers understand where oral
> supplements may fit into a daily dental-care routine and make evidence-based choices without
> treating supplements as substitutes for professional oral care. Full attribution will be
> provided. Thanks & Regards Rodgers Panato Health & Wellness Writer Bio Profile –
> https://www.healthinsiders.com/profile/rodgers

### M09 · Health Insiders

- **HARO category:** Health and Pharma
- **Anchor that matched:** `wellness, hydration`
- **Why marginal:** wellness-adjacent (['wellness', 'hydration']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Hello! I’m a writer working on an article for a health and wellness publication about the best
> collagen creams. I’m seeking expert input from board-certified dermatologists, cosmetic
> dermatologists, or qualified skincare professionals. If interested, please share your
> perspective on: Can topical collagen actually penetrate the skin deeply enough to stimulate or
> rebuild collagen, or does it primarily support surface hydration and temporary plumping? What
> role do ingredients such as hydrolyzed collagen, hyaluronic acid, peptides, and retinol play in
> collagen-focused creams? What should consumers look for when evaluating a collagen cream’s
> ingredient quality, texture, sourcing, and formulation? Are collagen creams appropriate for
> sensitive, dry, oily, or acne-prone skin? What side effects or ingredients—such as fragrance,
> retinoids, or heavier occlusives—should consumers watch for? How long should someone use a
> collagen cream before evaluating whether it is benefiting skin hydration, texture, or the
> appearance of fine lines? Your expertise will help readers understand the realistic benefits of
> topical collagen, choose better-formulated creams, and avoid exaggerated anti-aging claims. Full
> attribution will be provided. Thanks & Regards Rodgers Panato Health & Wellness Writer Bio
> Profile – https://www.healthinsiders.com/profile/rodgers

### M10 · Health Insiders

- **HARO category:** Health and Pharma
- **Anchor that matched:** `wellness`
- **Why marginal:** wellness-adjacent (['wellness']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> Hello! I’m a writer working on an article for a health and wellness publication about the best
> dental and oral health supplements. I’m seeking expert input from dentists, dental hygienists,
> registered dietitians, or oral-health specialists. If interested, please share your perspective
> on: What evidence supports ingredients such as xylitol, hydroxyapatite, oral probiotics,
> calcium, vitamin D, and vitamin C for oral wellness? How can these ingredients support enamel,
> gum health, oral bacteria balance, and breath freshness? Are oral probiotics effective, and
> should consumers look for products that identify specific probiotic strains and amounts? What
> should consumers look for regarding ingredient dosage, formula transparency, and third-party
> testing? Can oral health supplements replace brushing, flossing, professional cleanings, or
> dental treatment? Are there safety concerns or special considerations for people with dental
> conditions, medication use, or allergies? Your expertise will help readers understand where oral
> supplements may fit into a daily dental-care routine and make evidence-based choices without
> treating supplements as substitutes for professional oral care. Full attribution will be
> provided. Thanks & Regards Rodgers Panato Health & Wellness Writer Bio Profile –
> https://www.healthinsiders.com/profile/rodgers

### M11 · Medical News Today

- **HARO category:** Health and Pharma
- **Anchor that matched:** `blood pressure`
- **Why marginal:** wellness-adjacent (['blood pressure']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> A new study examines time-restricted eating length and changes in body weight and
> cardiometabolic outcomes. I need someone in the field to review the study and provide answers to
> some of the questions below. Please message me first to make sure I still need comments. Also
> include a link to your work/education (not LinkedIn) for consideration. Press release:
> https://www.news-medical.net/news/20260914/An-8-hour-eating-window-stood-out-for-weight-loss-
> but-the-full-picture-is-more-complicated.aspx Study:
> https://www.nature.com/articles/s41387-026-00467-1%20 Questions: 1. What do you see as the
> study's most important finding, and how much does it add to the existing evidence on time-
> restricted eating? 2. Does the study provide convincing evidence that an 8-hour eating window is
> better for weight loss than a 10- or 12-hour window? Why or why not? 3. What might explain the
> lack of consistent improvements in glucose, cholesterol, triglycerides, and blood pressure? 4.
> What safety considerations or contraindications should people discuss with a healthcare
> professional before trying time-restricted eating? 5. Is there anything else you would like our
> audience to know?

### M12 · Medscape

- **HARO category:** Health and Pharma
- **Anchor that matched:** `metabolic`
- **Why marginal:** wellness-adjacent (['metabolic']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> I am writing an upcoming feature for Medscape exploring the intricate feedback loop between
> mental health and obesity, specifically zooming in on the interoceptive facet in this piece. For
> decades, many individuals struggling with obesity have been conditioned by diet culture, chronic
> stress, or trauma to override their internal biological cues. This feature examines how
> clinicians are utilizing somatic therapy and interoceptive awareness training to help patients
> safely reconnect with their bodies, teaching them how to accurately translate physical
> sensations like hunger, fatigue, and emotional triggers. I am looking to speak with board-
> certified psychiatrists, psychologists, behavioral obesity medicine specialists, and licensed
> somatic therapists who clinicalize these techniques. Questions: Please provide written responses
> (2-4 sentences per question) to the following five questions. Feel free to draw on clinical
> anecdotes (anonymized) or evidence-based practices. If you cite clinical studies in your answer,
> I'd really appreciate an accompanying link. From a clinical perspective, how do chronic stress,
> trauma, and decades of restrictive diet culture structurally alter a patient's ability to
> perceive and trust basic internal biological signals (e.g., true hunger, early satiety, and
> fatigue)? How do you define and introduce interoceptive awareness training to patients who are
> deeply disconnected from or distrustful of their physical sensations? What specific somatic
> therapy techniques or exercises have you found most effective in helping patients differentiate
> between genuine physiological hunger and emotional triggers (such as anxiety, boredom, or
> shame)? What are the biggest clinical hurdles or psychological safety barriers when patients
> begin to re-experience uncomfortable physical sensations, and how do you navigate them? How does
> restoring interoceptive awareness practically interrupt or mitigate the broader feedback loop
> between mental health distress and metabolic/weight challenges in long-term treatment?
> Submission Guidelines Format: Please answer the questions directly in your response or paste a
> secure link. Attachments will not be delivered to me via HARO. Credentials: Include your full
> name, full title as you'd like it published, and a headshot/bio link if available. Please also
> provide a disclosure statement relative to the issues covered.

### M13 · Medscape

- **HARO category:** Health and Pharma
- **Anchor that matched:** `metabolic`
- **Why marginal:** wellness-adjacent (['metabolic']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> I'm exploring the growing body of toxicology and endocrinology research examining how endocrine-
> disrupting chemicals found in everyday plastics, food packaging, and consumer products
> contribute to metabolic dysfunction and weight regulation challenges. I am looking to speak with
> environmental health experts and obesity medicine specialists who study this area of expertise.
> I'd love for you to answer the below questions. Please also be sure to include your full name,
> clinical title, institutional affiliation, and a headshot/bio link if available. Please also
> provide a disclosure statement relative to the issues covered. Questions for Experts: Mechanisms
> of Action: How do endocrine-disrupting chemicals (EDCs) classified as "obesogens" specifically
> interfere with human metabolic pathways, adipogenesis, and long-term weight regulation compared
> to traditional caloric and lifestyle factors? Primary Exposure Routes: What are the most common
> everyday sources of environmental obesogens—such as specific plastics, food packaging materials,
> or household products—that current research identifies as posing the highest risk to metabolic
> health? Critical Windows of Vulnerability: Are there specific life stages (such as prenatal
> development, early childhood, or puberty) where exposure to these chemical toxicants has a more
> permanent or pronounced impact on a person's metabolic programming? Clinical and Public Health
> Implications: How should healthcare providers and public health policies begin addressing or
> incorporating chemical obesogen exposure into standard obesity prevention and treatment
> strategies? Mitigation Strategies: What practical, evidence-based steps can individuals
> realistically take to minimize their daily exposure to these endocrine-disrupting compounds in
> their home and dietary environments?

### M14 · Part B News

- **HARO category:** Health and Pharma
- **Anchor that matched:** `heart, management`
- **Why marginal:** wellness-adjacent (['heart']) but no sauna/cold/heat modality named; answering would stretch a claim past its do_not_say

> CMS' Advancing Chronic Care with Effective, Scalable Solutions (ACCESS) Model, a pay-for
> performance scheme that rewards medical tech innovators for measurable patient care results, is
> off to a fast start. Less than a year after its announcement, the program has 150 care partners
> with more to come in January. This month CMS said ACCESS would pay partners for results in four
> new categories: Heart failure, COPD, substance use disorders, and nicotine dependence. It this a
> sign of success, or just doubling down? What kind of innovators might the new tracks attract,
> and what are their chances of success? Readers of our practice management weekly will be
> interested to hear from practice and policy experts about this. Thanks, Roy Edroso Part B News
> https://pbn.decisionhealth.com/

---

## All 112 distinct requests, grouped by subject area

`Tier` is the competence reading: **A** general physician · **B** medical, other specialty · **C** outside medicine.

### Health and Pharma — 24 requests  (A 9 · B 10 · C 5)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| B | A&E | Hello! I'm looking to speak with medical professionals knowledgeable about living donor kidn… | rejected | transplant medicine |
| C | Bezzy | I am looking for HR professionals to discuss specific tips for people with IBD who are start… | marginal | wellness-shaped but no modality named |
| B | Bezzy | We are looking to do a story on 5 ways to de-stress when you have a condition like RA, diabe… | rejected | mental health professional (stated) |
| B | Blavity | I'm writing a Blavity Health piece on treating head lice in Black hair. A study presented to… | rejected | dermatology |
| B | Blavity | I'm writing a piece on treating hyperpigmentation in Black skin, built on a 2024 systematic … | rejected | dermatology |
| B | Chewy | Hi! I'm looking for commentary from a U.S.-based veterinarian on potential reasons why dogs … | rejected | veterinary |
| B | Famadillo.com | I'm working on an experiential Famadillo story in the same spirit as our Manhattan Laser Spa… | marginal | plastic surgery |
| B | Health Insiders | Hello! I’m a writer working on an article for a health and wellness publication about the be… | marginal | dermatology / skincare |
| B | Health Insiders | Hello! I’m a writer working on an article for a health and wellness publication about the be… | marginal | dentistry / dietetics |
| C | Healthline | I'm looking for firsthand accounts from people who have experienced side effects from weight… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| A | MDLinx | Seeking physicians (ideally oncologists) to comment for articles on supplements, nutrition, … | rejected | Explicitly seeking physicians; supplements, nutrition, fatigue, adherence |
| A | MedCentral | For MedCentral, I'm writing a deep dive on your recently published scientific statement by t… | rejected | Endocrine Society statement on obesity outcomes — metabolic medicine |
| A | Medical News Today | A new study examines time-restricted eating length and changes in body weight and cardiometa… | marginal | Time-restricted eating vs cardiometabolic outcomes — study review |
| B | Medscape | 'm seeking psychiatrists, behavioral neurologists, neuroscientists, and bariatric specialist… | rejected | psychiatry / behavioural neurology |
| A | Medscape | I am writing an upcoming feature for Medscape exploring the intricate feedback loop between … | marginal | Mental-health/obesity feedback loop — metabolic, physician-answerable |
| A | Medscape | I'm exploring the growing body of toxicology and endocrinology research examining how endocr… | marginal | Endocrine-disrupting chemicals and metabolic dysfunction |
| C | NHK | Our production would like to talk with a person who is saving money by using programs TrumpR… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| A | No One Is Coming | I'm looking for an emergency physician or nurse to interview about emergency medical issues.… | rejected | When to go to hospital, bleeding, poisoning — general clinical |
| A | Oprah Daily | Stress and anxiety are common triggers for chronic hives, also called chronic spontaneous ur… | rejected | Stress-reduction technique for a condition trigger — general clinical |
| A | Part B News | CMS' Advancing Chronic Care with Effective, Scalable Solutions (ACCESS) Model, a pay-for per… | marginal | CMS chronic-care model — care delivery, physician perspective |
| C | Part B News | Concerned by private equity firms buying up medical practices, some states have tightened th… | marginal | wellness-shaped but no modality named |
| A | Red Light Therapy Digest | We're looking for dermatologists, cosmetic physicians, skincare researchers, estheticians, a… | rejected | Red/near-infrared light and skin — photobiomodulation |
| B | St. Louis Magazine | I am writing about a local politician who narrowly survived a mass shooting. Since then he’s… | rejected | psychiatry |
| C | The Story Exchange | The Story Exchange, an award-winning nonprofit media platform dedicated to elevating women’s… | marginal | wellness-shaped but no modality named |

### General — 15 requests  (A 0 · B 3 · C 12)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | A&E | I'm looking for sources who are very knowledgeable about the Gotti family and their dealings… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | American Television (ATV) | Hello- am looking for anyone who is able to comment on the flock cameras specifically around… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Bored Panda | I am writing an in-depth article analyzing the recent cultural and sociological fallout surr… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| B | Chewy | Hi! I'm looking for commentary from a U.S.-based veterinarian on potential reasons why dogs … | rejected | veterinary |
| B | Chewy | Hi! I'm looking for commentary from a U.S.-based veterinarian on potential reasons why dogs … | rejected | veterinary |
| C | Classical Singer | Looking to interview opera singers who take GLP-1 meds, or voice teachers with students who … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Eteach | We’re looking for headteachers, trust leaders, CPD leads, education workforce researchers an… | marginal | wellness-shaped but no modality named |
| C | Famadillo | Famadillo is expanding its automotive review coverage and is looking to connect with automak… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MS NOW | Ali Velshi is hosting a live TV show in the 11pm ET hour on October 13. He'll be in the Colu… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | New York Post | I’m working on a New York Post Catholic schools special section in print and am looking to i… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | New York Post | Writing a story on Catholic schools and AP programs for print in the New York Post's upcomin… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | PetHelpful | Hello! We're working on a story educating homeowners on how to keep birds from housing thems… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Rolling Stone | I am looking to speak with Black farmers who are at risk of losing their land due to racism … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | The Guardian | I'm looking to speak to estate planners, lawyers, or grief counselors for a service piece ab… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| B | The Rover Blog | Hello, pet people! I’m writing an article for Rover about puppy development and care from 1 … | rejected | veterinary |

### Business and Finance — 21 requests  (A 0 · B 0 · C 21)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | AIM Group | I'm looking for job board leaders and data experts who can discuss the impact of Chile's Law… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Bankrate | Hello! I am interested in speaking to low- or moderate-income homebuyers who were able to ac… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | CMSWire | I am looking for marketers and tech specialists who have run an A/B test as a geo experience… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Clockify Blog | Please note that AI-generated answers will not be considered for publication. Kindly note th… | marginal | wellness-shaped but no modality named |
| C | College Ave | I'm looking to interview new graduate students who started school this fall without access t… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Deel Works | Reporting a feature for Deel Works, Deel's publication for HR and people leaders, about the … | answerable | **answerable — tripler (provisional)** |
| C | Deel Works | Reporting a feature for Deel Works. Most benefits and eligibility architecture was designed … | marginal | wellness-shaped but no modality named |
| C | Electrical Apparatus | I need to interview experts on the expansion of dedicated charging infrastructure for heavy … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Khaleej Times | I’m a journalist working on a Khaleej Times business story about the growth of women-founded… | answerable | **answerable — tripler (provisional)** |
| C | MarketingSherpa | What did you change? How did you get the idea to change it? What surprised you? Here are pre… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | 1. What kind of RV do you rent, and for how much? 2. How long have you been renting your RV?… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | I’m looking to speak with U.S.-based automotive experts, mechanics, car-buying experts and a… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | I’m looking to speak with U.S.-based financial advisors, CFP professionals and retirement pl… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | I’m looking to speak with U.S.-based financial advisors, CFPs, CPAs and tax professionals ab… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | I’m looking to speak with U.S.-based retirement planners, CFP professionals and financial ad… | marginal | wellness-shaped but no modality named |
| C | NTD | Hola Folks, we're writing a story about the upcoming (estimated) 3.9% COLA Social Security h… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Realtor.com | I am writing a story for Realtor.com titled "Nearly Half of Americans Would Buy a 3D-Printed… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Signaturely | We're creating an article about Freelancer Contract Tools and I'm looking for suitable tools… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | The Ad Firm | I'm writing a piece on the early-stage marketing spend founders only recognize as a mistake … | answerable | **answerable — tripler (provisional)** |
| C | The Cut | Do you live with your parents because they need your financial support (rent money), not bec… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | The Zebra | Hello. I’m a freelance writer with The Zebra (www.thezebra.com/resources). I’m seeking to in… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |

### Gift Bags — 14 requests  (A 0 · B 2 · C 12)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | Budget Savvy Diva | I'm putting together my annual Holiday Gift Guide for BudgetSavvyDiva.com, launching Novembe… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| B | DailyBloid | The Future of Fertility brings together five nationally recognized leaders spanning reproduc… | answerable | **answerable — tripler (provisional)** |
| B | Dailybloid.com | The Future of Fertility brings together five nationally recognized leaders spanning reproduc… | answerable | **answerable — tripler (provisional)** |
| C | East End Taste | East End Taste is accepting submissions for our 2026 Holiday Gift Guide, featuring elevated,… | marginal | wellness-shaped but no modality named |
| C | Emily Reviews | Emily Reviews is putting together our Holiday Gift Guide for 2026, and we're looking for bra… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Famadillo | We’re currently seeking products for hands-on review for an upcoming Gift Guide for the Pers… | marginal | wellness-shaped but no modality named |
| C | Famadillo | We’re currently seeking products for hands-on review for an upcoming Halloween Entertaining … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Life in a Break Down | Hi, It’s that time of year again! I’m starting to put together my 2026 Christmas Gift Guides… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | New Century Festivals | Looking for drink and product contributions to the 11th Annual Moon Festival on Sep 19th-20t… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Posh Lifestyle & Beauty Blog | Posh Lifestyle & Beauty Blog is now curating a Holiday Stocking Stuffers 2026 guide featurin… | answerable | **answerable — tripler (provisional)** |
| C | Right On! Digital | We are looking for gift bag items for a sneaker ball, so think--athletic items and that woul… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | The Business of WE (Women En… | The Business of WE (Women Entrepreneurs) is preparing for its 11th Annual Small Business Sum… | answerable | **answerable — tripler (provisional)** |
| C | The R.E.L.L.E. Legacy Founda… | The R.E.L.L.E. Legacy Foundation is preparing for "The Best of Me: A Day of Empowerment," a … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | The Review Wire | We are seeking products and companies for our 15th Annual Breast Cancer Awareness Guide: Com… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |

### Lifestyle and Entertainment — 18 requests  (A 0 · B 1 · C 17)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | Abstract House | We have a packed exhibition schedule including Affordable Art Fair in Battersea, London and … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | American Trail Running Assoc… | For Trail Runner Magazine, I'm working on a story about leave no trace principles and bathro… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Bergen Magazine | Do you pamper your pet? Feed him/her special food? Send him/her to doggy daycare or a pet sp… | marginal | wellness-shaped but no modality named |
| B | Business Insider | Hello, pet people! I’m writing a piece for Business Insider on heated dog beds and would lik… | rejected | veterinary |
| C | CrunchyTales | We're looking for a professional colour analyst or image consultant to contribute a short ex… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Food Republic | I am working on an expert-driven feature about affordable grocery store wines that taste mor… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Food Republic | This week, I'm writing an editorial feature about mistakes to avoid when curing meat. I'm lo… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Homes & Gardens | I'm working on a feature on small laundry rooms for Homes & Gardens online, and I am looking… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Mic | Hi, I'm an editor with Mic.com and I'm working on a product piece about "interior design mis… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Parade | I'm working on a Parade piece with this angle: "We Asked 3 Stylists Which Fashion 'Rule' The… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | PetHelpful | Hello! I'm working on a piece about how people can (humanely) keep squirrels from raiding th… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Salon | I'm looking for home and backyard furniture and storage for a gift guide in Salon (syndicate… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Salon | I'm writing a gift guide for Salon, with syndication on MSN and Yahoo. I'm looking for home … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Simply Recipes | I'm looking for pro bakers to offer insights and opinions on greasing baking pans with butte… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | WSJ Buy Side | Do you have go-to fall pieces for men and women that you wear or recommend to clients? Sweat… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | WSJ | Buy Side | I tested artificial Christmas trees for a Buy Side guide and am looking to add a bit of expe… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Yahoo | I'm looking for US-based professional/trained chefs to comment on the best ways to cook baco… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Yahoo | I'm working on a story about alternatives to wearing black during the fall/winter months. I'… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |

### Podcasts — 6 requests  (A 0 · B 0 · C 6)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | AM 830 | We are looking for former or current professional athletes to be guests on an ESPN LA-affili… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Basalingo | I am looking for parents of children younger than 18, who knows a second or more languages, … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Humanized Podcast | I'm working on an episode of Humanized, a podcast for founders and revenue leaders, about ho… | answerable | **answerable — tripler (provisional)** |
| C | Lemonada Media | Hi there! I'm producing a video podcast hosted by Reshma Saujani (Moms First) about the figh… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Persuasion by the Pint | In a crowded marketplace, customers rarely remember a company’s full origin story or lengthy… | marginal | wellness-shaped but no modality named |
| C | Thirty Minute Mentors | I am filling the last open slots for the 2026 lineup. Interviews are with America's top lead… | answerable | **answerable — tripler (provisional)** |

### Technology — 7 requests  (A 0 · B 0 · C 7)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | Arran Rice | I'm looking for an aviation, aerospace supply-chain, or China industrial-policy expert for a… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | InformationWeek | 1. How prevalent is AI human bias? 2. What makes it potentially damaging? 3. What's the best… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | InformationWeek | Technology journalist John Edwards (@TechJohnEdwards) is looking for experts who can answer … | marginal | wellness-shaped but no modality named |
| C | Marker | Looking to speak with people who have been directly or indirectly involved in a web accessib… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | MoneyLion | Toyota has said it is working toward commercializing all-solid-state batteries around 2027-2… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Plandek | This article explores the idea that an “AI superteam” can outpace the humans who must decide… | marginal | wellness-shaped but no modality named |
| C | TechTarget Cybersecurity | I'm looking for cybersecurity experts/analysts/practitioners who can offer prevention strate… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |

### Travel — 7 requests  (A 0 · B 0 · C 7)

| Tier | Outlet | Topic | Bucket | Why not answerable |
|---|---|---|---|---|
| C | Arran Rice | I'm looking for a transport, infrastructure, aviation or rail expert for a 30-45 minute reco… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Cruise America | If you've driven part or all of Route 66, what's one stop that genuinely surprised you and o… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Cruise America | If you've taken a fall foliage road trip, how did you decide when to go - and did you hit pe… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Famadillo | Famadillo has a travel writer heading to Raleigh, North Carolina, for a first-hand travel fe… | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Famadillo.com | Famadillo has a writer traveling to Toronto in October 2026 and is seeking opportunities to … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | New York Post | For upcoming special fall family fun section in print in the New York Post. The paper has a … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |
| C | Parade | For a quick turnaround story for Parade magazine, I'm looking to speak with travel advisors … | rejected | no sauna/heat/cold/recovery vocabulary; nothing medical in it |

---

## What this does not tell you

**Four days is four days.** 112 requests over one HARO week is enough to see the shape of the channel and not enough to price it. The 14-day clock started 2026-09-15 and has 10 days to run.

**The four proven links are not in this sample.** They were earned 2026-01-20 to 2026-07-02 through a contractor's own HARO account, and nothing in this corpus is one of them. The Healthline placement is understood to have been about heart-attack risk in younger males — general cardiology, tier A, and exactly the kind of request the current bank cannot match. That is the strongest single piece of support for the mis-scope hypothesis, and it sits outside this dataset rather than in it.

**The competence column is a judgement.** Nine is my count, itemised above so it can be checked. A reviewer who counts differently should say so on the rows, not on the total.
