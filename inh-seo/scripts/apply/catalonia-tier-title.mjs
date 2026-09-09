import { gql } from '../lib/shopify.js';
import { backup, logChange, parseArgs, banner } from '../lib/util.js';
const flags = parseArgs();
banner('catalonia-tier-title', flags);
const ID = 'gid://shopify/Product/7591178895427';
const FROM = 'Golden Designs GDI-6880-02 Elite Catalonia 8 Person Ultra Low EMF Far Infrared Sauna';
const TO   = 'Golden Designs GDI-6880-02 Elite Catalonia 8 Person Near Zero EMF Far Infrared Sauna';
const r = await gql(`query($id:ID!){ product(id:$id){ id handle title } }`, { id: ID });
const p = r.product;
if (p.title !== FROM) { console.error(`REFUSING — live title is not the expected one.\n  live: ${p.title}\n  spec: ${FROM}`); process.exit(1); }
console.log(`  − ${FROM}`);
console.log(`  + ${TO}`);
console.log('  reason: the manufacturer publishes "EMF Under 2MG when sitting 2 to 3 inches from the heating');
console.log('          panels" and labels it Near Zero EMF. Our tiers: near-zero 2-3 mG, ultra-low 3-5 mG.');
console.log('          Under 2 mG is not ultra-low on any reading. The title contradicted its own collection.');
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
backup('catalonia-title-before', [{ id: p.id, handle: p.handle, title: p.title }]);
const m = await gql(`mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id title } userErrors{ field message } } }`, { input: { id: ID, title: TO } });
if (m.productUpdate.userErrors.length) { console.error(m.productUpdate.userErrors); process.exit(1); }
logChange({ script: 'catalonia-tier-title', kind: 'product', id: ID, handle: p.handle, field: 'title', before: FROM, after: TO,
  reason: 'Title said Ultra Low EMF while the product sits in near-zero-emf. Manufacturer spec settles it at under 2MG. Same class as the wood errors: a title contradicting the verified attribute.' });
console.log('\n  updated. ' + m.productUpdate.product.title);
