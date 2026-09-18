/**
 * assertReach proved against ALL THREE known-broken cases, not one.
 *
 * A guard that has never failed has not been tested, and a guard proved against
 * a single case is proved against a single case. These reproduce the actual
 * regressions of 9 September 2026 from their recorded before/after values.
 *
 * SYNTHETIC. Repairing the estate cannot break them.
 *   node scripts/audit/reach-selftest.mjs
 */
import { captureReach, classifyReach, assertReach } from '../lib/reach.mjs';

const cap = async (rows) => captureReach(async () => rows);
let failures = 0;
const check = (name, cond, detail = '') => {
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!cond) failures += 1;
};

/* ── CASE 1 — INSTANCE 56 ────────────────────────────────────────────────────
   Writing a meta description nulled the SEO title, because Shopify treats `seo`
   as a whole object. The script declared it was changing seo.description. */
console.log('\nCASE 1 — instance 56: a partial `seo` object nulls the title');
{
  const before = await cap([{ handle: 'sauna-heaters', title: 'Sauna Heaters',
    seo: { title: 'Sauna Heaters | 95 Electric & Wood, 4kW to 40kW', description: null } }]);
  const after = await cap([{ handle: 'sauna-heaters', title: 'Sauna Heaters',
    seo: { title: null, description: 'At all three brands we checked, the heating element…' } }]);
  const r = classifyReach(before, after, { handles: ['sauna-heaters'], fields: ['seo.description'] });
  check('the intended description change is DECLARED', r.declared.some((d) => d.field === 'seo.description'));
  check('the nulled title is COLLATERAL', r.collateral.some((c) => c.field === 'seo.title' && c.after === null),
    r.collateral.map((c) => c.field).join(', ') || 'none');
  let threw = false;
  try { assertReach(before, after, { handles: ['sauna-heaters'], fields: ['seo.description'] }); } catch { threw = true; }
  check('assertReach THROWS', threw);
}

/* ── CASE 2 — INSTANCE 55 ────────────────────────────────────────────────────
   A dry run reviewed --only cold-plunge; the apply ran unscoped over 56
   collections and reverted cluster links on two of them. 53 were no-ops, which
   is what made it invisible. */
console.log('\nCASE 2 — instance 55: an unscoped apply reverts undeclared handles');
{
  const noop = (h, n) => ({ handle: h, descriptionHtml: `<p>unchanged copy for ${h}</p>`, seo: { title: `T${n}`, description: `D${n}` } });
  const beforeRows = [
    { handle: 'cold-plunge', descriptionHtml: '<p>Eighteen cold plunge tubs…</p>', seo: { title: 'CP', description: null } },
    { handle: 'full-spectrum', descriptionHtml: '<p>…see our reviews of <a href="/blogs/saunas/sun-home-saunas-review">Sun Home</a> and <a href="/blogs/saunas/clearlight-saunas-review">Clearlight</a>.</p>', seo: { title: 'FS', description: null } },
    { handle: 'low-emf', descriptionHtml: '<p>…<a href="/blogs/saunas/clearlight-saunas-review">not one puts the figure on the product page</a>.</p>', seo: { title: 'LE', description: null } },
    ...Array.from({ length: 53 }, (_, i) => noop(`other-${i}`, i)),
  ];
  const afterRows = [
    { handle: 'cold-plunge', descriptionHtml: '<p>Nineteen cold plunge tubs…</p>', seo: { title: 'CP', description: null } },
    { handle: 'full-spectrum', descriptionHtml: '<p>…judgement we are not going to make for you.</p>', seo: { title: 'FS', description: null } },
    { handle: 'low-emf', descriptionHtml: '<p>…Ask for the number and the distance together.</p>', seo: { title: 'LE', description: null } },
    ...Array.from({ length: 53 }, (_, i) => noop(`other-${i}`, i)),
  ];
  const before = await cap(beforeRows), after = await cap(afterRows);
  const r = classifyReach(before, after, { handles: ['cold-plunge'], fields: ['descriptionHtml'] });
  check('the intended cold-plunge change is DECLARED', r.declared.length === 1 && r.declared[0].handle === 'cold-plunge');
  check('BOTH reverted collections are COLLATERAL', r.collateral.length === 2
    && r.collateral.some((c) => c.handle === 'full-spectrum') && r.collateral.some((c) => c.handle === 'low-emf'),
    r.collateral.map((c) => c.handle).join(', ') || 'none');
  check('the 53 no-ops are silent, not noise', r.collateral.every((c) => !c.handle.startsWith('other-')));
  let threw = false;
  try { assertReach(before, after, { handles: ['cold-plunge'], fields: ['descriptionHtml'] }); } catch { threw = true; }
  check('assertReach THROWS', threw);
}

/* ── CASE 3 — THE DRIFT CASCADE ──────────────────────────────────────────────
   THE WEAKER CLAIM, PROVED AS STATED. assertReach does NOT catch this at the
   write: archiving a product is a legitimate declared change, and the damage is
   to figures on OTHER pages. What is proved here is only what was claimed — the
   same capture makes it catchable, because a derived count taken alongside the
   record moves visibly at the moment of the archive. */
console.log('\nCASE 3 — the drift cascade: NOT caught at the write; catchable from the same capture');
{
  const beforeRows = [
    { handle: 'catalonia-8p-infrared-sauna', status: 'ACTIVE', derived_far_infrared_count: 71, derived_far_infrared_price_max: 14999 },
  ];
  const afterRows = [
    { handle: 'catalonia-8p-infrared-sauna', status: 'ARCHIVED', derived_far_infrared_count: 70, derived_far_infrared_price_max: 9999 },
  ];
  const before = await cap(beforeRows), after = await cap(afterRows);

  /* Declaring only the archive — which is what the operator intended */
  const bare = classifyReach(before, after, { handles: ['catalonia-8p-infrared-sauna'], fields: ['status'] });
  check('the archive itself is DECLARED', bare.declared.some((d) => d.field === 'status'));
  check('WITHOUT derived fields in the capture, nothing else would surface',
    bare.collateral.every((c) => c.field.startsWith('derived_')),
    'the only collateral comes from the derived fields we deliberately captured');
  check('WITH derived fields captured, the cascade IS visible at the moment of the archive',
    bare.collateral.length === 2
    && bare.collateral.some((c) => c.field === 'derived_far_infrared_count' && c.before === 71 && c.after === 70)
    && bare.collateral.some((c) => c.field === 'derived_far_infrared_price_max'),
    bare.collateral.map((c) => `${c.field} ${c.before}->${c.after}`).join('; '));
  console.log('        (claim proved is the WEAK one: the capture makes it catchable, not that assertReach catches it)');
}

/* ── CASE 4 — the guard must not fire on a correct write ─────────────────── */
console.log('\nCASE 4 — negative control: a correct, fully-declared write passes silently');
{
  const before = await cap([{ handle: 'hybrid', descriptionHtml: '<p>old</p>', seo: { title: 'H', description: 'D' } }]);
  const after = await cap([{ handle: 'hybrid', descriptionHtml: '<p>new</p>', seo: { title: 'H', description: 'D' } }]);
  let threw = false;
  try { assertReach(before, after, { handles: ['hybrid'], fields: ['descriptionHtml'] }); } catch { threw = true; }
  check('assertReach does NOT throw', !threw);
}

/* ── CASE 5 — --reach-ok must work, or the guard gets commented out ──────── */
console.log('\nCASE 5 — an explicitly allowed collateral field does not block');
{
  const before = await cap([{ handle: 'x', seo: { title: 'T', description: null } }]);
  const after = await cap([{ handle: 'x', seo: { title: null, description: 'D' } }]);
  let threw = false;
  try { assertReach(before, after, { handles: ['x'], fields: ['seo.description'] }, { allow: ['seo.title'] }); } catch { threw = true; }
  check('allowed collateral passes', !threw);
  let threw2 = false;
  try { assertReach(before, after, { handles: ['x'], fields: ['seo.description'] }, { allow: ['seo.somethingElse'] }); } catch { threw2 = true; }
  check('an unrelated allowance does NOT excuse it', threw2);
}

/* ── CASE 6 — a record that disappears must block (18i: proves VANISHED) ── */
console.log('\nCASE 6 — a row present before and absent after is VANISHED and blocks');
{
  const before = await cap([{ handle: 'kept', title: 'K' }, { handle: 'gone', title: 'G' }]);
  const after = await cap([{ handle: 'kept', title: 'K' }]);
  const r = classifyReach(before, after, { handles: ['kept'], fields: ['title'] });
  check('the missing row is classified VANISHED', r.vanished.length === 1 && r.vanished[0].handle === 'gone');
  let threw = false;
  try { assertReach(before, after, { handles: ['kept'], fields: ['title'] }); } catch { threw = true; }
  check('assertReach THROWS on a vanished row', threw);
}

/* ── CASE 7 — null and '' are different values (18i: proves the comparison is not String(x ?? '')) ── */
console.log("\nCASE 7 — a meta nulled from '' (and '' from null) is a change, not a no-op");
{
  const before = await cap([{ handle: 'n', seo: { title: 'T', description: '' } }, { handle: 'm', seo: { title: null } }]);
  const after = await cap([{ handle: 'n', seo: { title: 'T', description: null } }, { handle: 'm', seo: { title: '' } }]);
  const r = classifyReach(before, after, { handles: ['x'], fields: ['descriptionHtml'] });
  check("'' -> null is COLLATERAL", r.collateral.some((c) => c.handle === 'n' && c.field === 'seo.description'));
  check("null -> '' is COLLATERAL", r.collateral.some((c) => c.handle === 'm' && c.field === 'seo.title'));
  const same = classifyReach(await cap([{ handle: 'q', price: 10 }]), await cap([{ handle: 'q', price: '10' }]), { handles: [], fields: [] });
  check('a number and its string form stay equal (control)', same.collateral.length === 0);
}

console.log(failures ? `\n${failures} check(s) FAILED — do not trust assertReach.` : '\nAll checks pass across all three known-broken cases, the vanished and null/empty cases, and two controls.');
process.exit(failures ? 1 : 0);
