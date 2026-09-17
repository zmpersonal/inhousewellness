/* assertSplitPoint — refuse a count derived from a string split without confirming what it
 * split on.
 *
 * WHY THIS EXISTS. On 16 September 2026 I measured "which citations are bibliography-only"
 * by splitting an article on the string "Sources". The article's TABLE OF CONTENTS contains
 * an entry called "Sources", 40,000 characters before the section of the same name, so the
 * split landed on the contents list. Everything after it was treated as the bibliography,
 * everything before it as the body, and the body was therefore "empty" of citations. I
 * reported that nothing cited those sources inline. Four inline citations rested on them.
 *
 * That was the fourth instance in one session of the same failure: reading my own output once.
 * The rule against it is in CLAUDE.md, it is the rule most often quoted there, and it was
 * broken four times that day by the person quoting it. Same reasoning as assertFresh and
 * assertReach: the discipline does not survive a long session, so it becomes a guard.
 *
 *   const i = assertSplitPoint(body, 'Sources', { context: '<h2', pick: 'last' });
 *   const [head, tail] = splitAtAssert(body, 'Sources', { context: '<h2', pick: 'last' });
 */

const show = (text, i, pad = 80) =>
  JSON.stringify(text.slice(Math.max(0, i - pad), i + pad)).slice(0, 2 * pad + 40);

/**
 * Return the index of the ONE split point the caller means, or throw.
 *
 * @param {string} text        the document
 * @param {string} needle      the delimiter being split on
 * @param {object} [opts]
 * @param {string} [opts.context]  a string that must appear within `window` chars BEFORE the
 *                                 match — e.g. '<h2' to insist the heading, not the contents entry
 * @param {number} [opts.window=120]
 * @param {'only'|'first'|'last'} [opts.pick='only']  'only' throws when candidates > 1
 * @param {string} [opts.label='split']
 */
export function assertSplitPoint(text, needle, opts = {}) {
  const { context = null, window = 120, pick = 'only', label = 'split' } = opts;
  if (typeof text !== 'string' || !text.length) throw new Error(`${label}: no text to split`);
  if (!needle) throw new Error(`${label}: no delimiter given`);

  const all = [];
  for (let i = text.indexOf(needle); i !== -1; i = text.indexOf(needle, i + 1)) all.push(i);
  if (!all.length) throw new Error(`${label}: delimiter ${JSON.stringify(needle)} does not occur`);

  const matching = context
    ? all.filter((i) => text.slice(Math.max(0, i - window), i).includes(context))
    : all;

  if (!matching.length) {
    throw new Error(
      `${label}: ${all.length} occurrence(s) of ${JSON.stringify(needle)}, none within ${window} chars after ${JSON.stringify(context)}.\n` +
      all.slice(0, 3).map((i) => `  at ${i}: ${show(text, i, 60)}`).join('\n'));
  }

  if (matching.length > 1 && pick === 'only') {
    throw new Error(
      `${label}: ${matching.length} candidate split points for ${JSON.stringify(needle)}${context ? ` in context ${JSON.stringify(context)}` : ''}. ` +
      `Say which with pick:'first'|'last', or narrow the context.\n` +
      matching.slice(0, 4).map((i) => `  at ${i}: ${show(text, i, 60)}`).join('\n'));
  }

  const idx = pick === 'last' ? matching[matching.length - 1] : matching[0];
  console.log(`  ${label}: split at ${idx} of ${text.length} (${all.length} occurrence(s), ${matching.length} in context) — ${show(text, idx, 45)}`);
  return idx;
}

/** Split once, at an asserted point. Returns [before, after]. */
export function splitAtAssert(text, needle, opts = {}) {
  const i = assertSplitPoint(text, needle, opts);
  return [text.slice(0, i), text.slice(i)];
}
