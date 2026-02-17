# Domain Naming Guide for LLMs

A concise, execution-ready framework for selecting a domain name that improves brand recall, positioning, and marketing performance.

> Scope: Branding and marketing only. This guide intentionally excludes legal, TLD selection, and technical operations.

---

## 1) Start with strategy, not wordplay

Before generating names, define these four inputs:

- Audience: Who you want to attract first.
- Category cue: The market/problem space you want the brand associated with.
- Positioning: Why you are different.
- Brand personality: For example, premium, playful, bold, trustworthy, or technical.

If these inputs are unclear, name evaluation becomes subjective and inconsistent.

---

## 2) Choose one naming direction

Use one direction per naming cycle so candidates are judged consistently:

- Descriptive: Immediate category clarity (high comprehension, lower distinctiveness).
- Suggestive: Signals benefit/outcome (strong balance for many startups).
- Invented/abstract: Highly distinctive and ownable (requires stronger brand-building).
- Founder/personal: Useful for personality-led brands.

Practical rule: With limited budget, prioritize names that are understood quickly.

---

## 3) Generate candidates using strict filters

Keep only names that pass all criteria:

- Easy to pronounce.
- Easy to spell.
- Easy to remember after one exposure.
- Clear when spoken once (radio test).
- No awkward meaning in priority languages/markets.
- Clean visual form (avoid messy letter patterns and ambiguous chunks).
- Works in lowercase and in a logo lockup.

Target profile: Short, clear, and unmistakable.

---

## 4) Optimize for recall over cleverness

Strong domain names win on memory and repeatability.

Prefer:

- Strong rhythm and mouthfeel.
- Distinct visual/phonetic shape.
- Simple syllable structure.
- Easy alignment with a one-sentence brand story.

Avoid:

- Forced misspellings.
- Puns that require explanation.
- Names that are easy to hear but hard to type (or the reverse).

---

## 5) Run cross-channel consistency simulation

The LLM should simulate the marketing ecosystem for each candidate and score how consistently the core brand string survives across channels.

Simulate these touchpoints:

- Social handles
- Product/app naming
- Email sender/display name
- Campaign naming
- Homepage headline usage

### Internal self-check protocol

For each candidate:

1. Generate five realistic examples per touchpoint.
2. Check whether the core brand string remains stable or drifts.
3. Flag collisions, awkward truncation, and readability issues.
4. Assign a Channel Consistency Score (1-5) with one-line rationale.

Rule: A single stable brand string across channels outperforms fragmented naming.

---

## 6) Run simulated evaluation tests (no live interviews)

For LLM workflows, use structured simulation instead of human interviews.

For each candidate, run:

1. Simulated 5-second recall test
Create 10 representative personas, expose the name once, then estimate recall likelihood.

2. Simulated phone/radio test
Generate likely heard spellings from pronunciation and estimate typo risk.

3. Simulated cold comprehension test
Generate first-impression guesses of what the brand does; score clarity.

4. Simulated preference test (A/B/C)
Compare shortlist options across persona segments and output ranked preference.

5. Simulated ad-response proxy
Generate likely hooks and estimate relative CTR potential plus direct-search-intent lift.

### Required output per candidate

- Recall score (1-5)
- Typo risk (1-5, lower is better)
- Comprehension score (1-5)
- Preference rank
- Ad-response proxy score (1-5)
- Confidence note (2-3 lines)

Use one consistent rubric across all candidates to preserve comparability.

---

## 7) Reinforce the name on the homepage

A name performs better when messaging resolves ambiguity immediately:

- Headline states value in one line.
- Subheadline anchors category/problem.
- Visual direction matches brand personality.
- Proof (logos, testimonials, metrics) reduces uncertainty.

If the name is abstract, headline/subheadline clarity is mandatory.

---

## 8) Use a weighted brand scorecard

Score each candidate from 1 to 5 on:

- Memorability (likely to be recalled)
- Clarity (likely to be understood)
- Pronounceability (easy to say confidently)
- Distinctiveness (stands out in category)
- Brand fit (matches intended tone/positioning)
- Channel consistency (stable across touchpoints)

### Suggested weights

- Memorability: 25%
- Clarity: 20%
- Distinctiveness: 20%
- Brand fit: 20%
- Pronounceability: 10%
- Channel consistency: 5%

Select the top-scoring option, then run one final simulation pass on the top three.

---

## Common mistakes to avoid

- Selecting names that sound clever internally but confuse the market.
- Overweighting uniqueness while underweighting clarity.
- Allowing brand string drift across channels.
- Using inconsistent or non-comparable scoring logic.
- Assuming the name alone communicates positioning.

---

## Default 80/20 recommendation

1. Choose a suggestive, easy-to-pronounce name.
2. Prioritize names people can remember and type after one exposure.
3. Validate with structured simulations (recall, comprehension, preference).
4. Keep one stable brand string across domain, social, product, and email.
5. Use homepage messaging to make brand meaning instantly clear.
