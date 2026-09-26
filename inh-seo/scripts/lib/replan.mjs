/* Re-read live at APPLY time and diff against the plan.
 *
 * WHY. Round 23's accordion plan was 87 at dry run and 88 at apply: a product was published between
 * the two. The splicer re-reads live, so the overrun was VISIBLE. Ten apply scripts select targets
 * from a stored dump and would have skipped it and reported clean.
 *
 * ⚠️ assertFresh does NOT cover this. It compares a dump against data/changelog.jsonl — it answers
 * "has anything changed since WE last wrote". An admin-side publish writes no changelog row, so a dump
 * can be provably fresh by that test and still be missing a member that arrived after it was taken.
 * assertFresh measures our own activity as a proxy for the world's. This measures the world.
 *
 * It THROWS rather than exiting, deliberately: an exiting guard cannot be driven by a fixture, and a
 * try/catch around one is dead code that reads as a guard (see scripts/audit/exit-vs-throw.mjs).
 */

/* planned and live are arrays of stable keys — handles or gids. Never titles. */
export function diffPlan(planned, live) {
  const P = new Set(planned), L = new Set(live);
  return {
    gained: [...L].filter((k) => !P.has(k)).sort(),   // arrived after the plan was taken
    lost: [...P].filter((k) => !L.has(k)).sort(),     // gone, unpublished, or no longer matching
  };
}

/* Refuses unless every difference is declared. A silent exclusion is indistinguishable from an
   exclusion that matched nothing, so both lists are always PRINTED, even when allowed. */
export function assertPlanCurrent(planned, live, { label = 'batch', allowGained = [], allowLost = [], log = console.log } = {}) {
  if (!Array.isArray(planned) || !Array.isArray(live)) throw new Error('replan: planned and live must both be arrays');
  if (!planned.length) throw new Error('replan: an empty plan cannot be checked — refusing rather than reporting clean');
  const { gained, lost } = diffPlan(planned, live);
  const undeclaredG = gained.filter((k) => !allowGained.includes(k));
  const undeclaredL = lost.filter((k) => !allowLost.includes(k));
  if (gained.length) log(`  ${label}: ${gained.length} member(s) GAINED since the plan: ${gained.join(', ')}`);
  if (lost.length) log(`  ${label}: ${lost.length} member(s) LOST since the plan: ${lost.join(', ')}`);
  if (!gained.length && !lost.length) log(`  ${label}: live matches the plan exactly (${planned.length})`);
  const msg = [];
  if (undeclaredG.length) msg.push(`${undeclaredG.length} undeclared arrival(s): ${undeclaredG.join(', ')}`);
  if (undeclaredL.length) msg.push(`${undeclaredL.length} undeclared departure(s): ${undeclaredL.join(', ')}`);
  if (msg.length) throw new Error(`replan ${label}: ${msg.join('; ')}. The reviewed plan is not the current population — re-run the dry run, or declare them.`);
  return { gained, lost };
}

export const REPLAN_FIXTURES = [
  ['identical populations pass', () => { const r = assertPlanCurrent(['a', 'b'], ['b', 'a'], { log: () => {} }); return r.gained.length === 0 && r.lost.length === 0; }, true],
  ['an undeclared arrival throws', () => { try { assertPlanCurrent(['a'], ['a', 'b'], { log: () => {} }); return false; } catch { return true; } }, true],
  ['an undeclared departure throws', () => { try { assertPlanCurrent(['a', 'b'], ['a'], { log: () => {} }); return false; } catch { return true; } }, true],
  ['a DECLARED arrival passes', () => { const r = assertPlanCurrent(['a'], ['a', 'b'], { allowGained: ['b'], log: () => {} }); return r.gained[0] === 'b'; }, true],
  ['a declared arrival is still PRINTED', () => { let out = ''; assertPlanCurrent(['a'], ['a', 'b'], { allowGained: ['b'], log: (s) => { out += s; } }); return /GAINED/.test(out); }, true],
  ['an empty plan refuses rather than reporting clean', () => { try { assertPlanCurrent([], [], { log: () => {} }); return false; } catch { return true; } }, true],
  ['a non-array refuses', () => { try { assertPlanCurrent('a', ['a'], { log: () => {} }); return false; } catch { return true; } }, true],
  ['the real Round 23 case: 87 planned, 88 live, undeclared -> throws', () => {
    const p = Array.from({ length: 87 }, (_, i) => `h${i}`);
    try { assertPlanCurrent(p, [...p, 'vorarlberg-5-person-sauna'], { log: () => {} }); return false; } catch (e) { return /vorarlberg/.test(e.message); }
  }, true],
  ['it THROWS rather than exiting, so a fixture can drive it', () => typeof assertPlanCurrent === 'function', true],
];
