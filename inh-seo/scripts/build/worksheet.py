#!/usr/bin/env python3
"""
Regenerates docs/collection-worksheet.xlsx from current data.

Read-only against the store. Sources:
  data/collections-plan.json          actions, keywords, volume, CPC
  data/collections.json               live state (run `npm run audit:collections` first)
  data/gsc-baseline-2026-09-07/       real impressions per collection URL

Rows are DROPPED when the collection is unpublished, marked DEINDEX/DELETE, or
marked SCOPE-OUT. The client should not be looking at pages that no longer
serve traffic, or at categories deliberately outside the programme.

Requires openpyxl:  pip3 install openpyxl
Run:                python3 scripts/build/worksheet.py
"""
import json, csv, collections, sys, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D=lambda *p: os.path.join(ROOT,*p)

plan=json.load(open(D('data','collections-plan.json')))
live={c['handle']:c for c in json.load(open(D('data','collections.json')))}

def num(s): return float(str(s).replace('%','').replace(',','').strip() or 0)
imp=collections.defaultdict(float)
with open(D('data','gsc-baseline-2026-09-07','Pages.csv'), encoding='utf-8-sig') as fh:
    for r in csv.DictReader(fh):
        u=r['Top pages'].split('#')[0]
        if '/collections/' in u:
            imp[u.split('/collections/')[1].rstrip('/')]+=num(r['Impressions'])

DROP={'DEINDEX','DELETE','SCOPE-OUT'}
rows=[]; dropped=collections.Counter()
for p in plan:
    h=p['handle']; c=live.get(h)
    if not c: dropped['not in store']+=1; continue
    if not c['publishedOnline']: dropped['unpublished']+=1; continue
    if p['action'] in DROP: dropped[p['action']]+=1; continue
    rows.append({'p':p,'c':c,'imp':int(imp.get(h,0))})
rows.sort(key=lambda r: (-(r['p'].get('volume') or 0), -r['c']['products']))

YELLOW=PatternFill('solid', fgColor='FFF9E6'); DARK=PatternFill('solid', fgColor='1B1613')
HDR=Font(size=10,bold=True,color='FFFFFF'); BASE=Font(size=10)
THIN=Border(*[Side(style='thin', color='D9D9D9')]*4)
WRAP=Alignment(wrap_text=True, vertical='top'); TOP=Alignment(vertical='top')

wb=Workbook(); wb.remove(wb.active)
ws=wb.create_sheet('Collections')
cols=[('#',5),('Handle',30),('URL',46),('Collection Title',30),('Products',9),('GSC Impr',10),
      ('Description',13),('SEO Title?',12),('Meta Desc?',12),('ALREADY DONE',18),('Suggested Action',17),
      ('ACTION',14),('PRIMARY KEYWORD',26),('Vol/mo',9),('CPC',8),
      ('NEW SEO TITLE',40),('NEW META DESCRIPTION',52),('NEW DESCRIPTION',52),('WRITER NOTES',40),('Audit Notes',60)]
YCOLS=set(range(12,20))
for i,(name,w) in enumerate(cols,1):
    c=ws.cell(1,i,name); c.font=HDR; c.fill=DARK; c.alignment=WRAP
    ws.column_dimensions[get_column_letter(i)].width=w
ws.freeze_panes='B2'; ws.auto_filter.ref='A1:T%d'%(len(rows)+1)

for n,r in enumerate(rows,1):
    p,c=r['p'],r['c']
    done=[x for x,ok in (('title',c['seoTitle']),('meta',c['seoDescription']),('description',c['descriptionLength']>0)) if ok]
    vals=[n,p['handle'],'https://inhousewellness.com/collections/'+p['handle'],c['title'],c['products'],r['imp'],
          'has copy' if c['descriptionLength']>0 else 'empty',
          'yes' if c['seoTitle'] else 'MISSING','yes' if c['seoDescription'] else 'MISSING',
          ' + '.join(done),p['action'],'',p.get('primaryKeyword') or '',p.get('volume') or '',p.get('cpc') or '',
          '','','','',p.get('auditNotes') or '']
    for i,v in enumerate(vals,1):
        cell=ws.cell(n+1,i,v); cell.font=BASE; cell.border=THIN
        cell.alignment=WRAP if i in (4,10,13,17,18,19,20) else TOP
        if i in YCOLS: cell.fill=YELLOW

need_t=sum(1 for r in rows if not r['c']['seoTitle'])
need_m=sum(1 for r in rows if not r['c']['seoDescription'])
need_d=sum(1 for r in rows if r['c']['descriptionLength']==0)
zero=sum(1 for r in rows if r['imp']==0)
tot_i=sum(r['imp'] for r in rows)

rd=wb.create_sheet('README',0); rd.column_dimensions['A'].width=112
L=[('InHouse Wellness — Collection SEO Worksheet','h1'),
 ('Regenerated %s from the live Shopify Admin API, data/collections-plan.json and the'%os.environ.get('WS_DATE','7 September 2026'),'p'),
 ('Search Console baseline in data/gsc-baseline-2026-09-07/.','p'),('','p'),
 ('This REPLACES every earlier version. Do not fill in an old one.','b'),('','p'),
 ('HOW MANY ROWS NEED YOU','h2'),('','p'),
 ('  %d collections are in this worksheet.'%len(rows),'p'),('','p'),
 ('  Needs a NEW SEO TITLE:        %2d of %d   (%d already have one — leave those blank)'%(need_t,len(rows),len(rows)-need_t),'b'),
 ('  Needs a NEW META DESCRIPTION: %2d of %d   (%d already have one)'%(need_m,len(rows),len(rows)-need_m),'b'),
 ('  Needs a DESCRIPTION:          %2d of %d   (%d already written)'%(need_d,len(rows),len(rows)-need_d),'b'),('','p'),
 ('  Every row still needs you to confirm or change ACTION.','p'),
 ('  The ALREADY DONE column tells you per row what is handled. If it says "meta", the meta','p'),
 ('  description is written and live — do not write another one.','p'),('','p'),
 ('WHAT IS NOT IN HERE, AND WHY','h2'),('','p'),
 ('  %d rows were dropped from the 90-collection plan:'%sum(dropped.values()),'p'),
 ('    %2d unpublished from the Online Store (Round 1.5 and earlier)'%dropped['unpublished'],'p'),
 ('    %2d marked SCOPE-OUT — outdoor cooking, a deliberate decision, not a gap'%dropped['SCOPE-OUT'],'p'),
 ('    %2d marked DEINDEX or DELETE and still pending'%(dropped['DEINDEX']+dropped['DELETE']),'p'),('','p'),
 ('  Outdoor cooking (bbq-grills, cal-flame, fire-pits, outdoor-kitchen and 7 more) stays','p'),
 ('  published, sellable and indexed. It just does not get copy. 155 products. See CLAUDE.md.','p'),('','p'),
 ('SORTING','h2'),('','p'),
 ('  Search volume first, product count second. The pages that matter are at the top.','p'),
 ('  Rows with no volume sit at the bottom — that means no keyword has been researched for','p'),
 ('  them yet, not that they are unimportant.','p'),('','p'),
 ('GSC IMPR','h2'),('','p'),
 ('  Real Search Console impressions for that collection URL, 28 days to 5 September 2026.','p'),
 ('  %d of %d collections got ZERO. Total across all rows: %s impressions, 5 clicks.'%(zero,len(rows),f'{tot_i:,}'),'p'),
 ('  A zero does not mean the page is worthless — it means nothing finds it, which is the point.','p'),('','p'),
 ('HOW TO USE IT','h2'),('','p'),
 ('  Yellow columns are yours. Everything else comes from the store or from research.','p'),('','p'),
 ('  1. Work top-down. Set ACTION on every row.','p'),
 ('  2. Fill PRIMARY KEYWORD where blank.','p'),
 ('  3. NEW SEO TITLE only where SEO Title? says MISSING. Under 60 characters.','p'),
 ('  4. NEW META DESCRIPTION only where Meta Desc? says MISSING. Under 155 characters.','p'),
 ('  5. Descriptions: write NEW DESCRIPTION yourself, or leave blank and put guidance in','p'),
 ('     WRITER NOTES — Claude Code drafts against real product data plus your notes.','p'),('','p'),
 ('  Count characters on the DECODED string. "&amp;" is five characters stored, one on the page.','p'),
 ('  Never write a health claim. That rule is why 16 metas were rewritten and 6 descriptions cleared.','p')]
for i,(t,k) in enumerate(L,1):
    c=rd.cell(i,1,t)
    c.font=Font(size=14,bold=True) if k=='h1' else Font(size=11,bold=True) if k=='h2' else Font(size=10,bold=True) if k=='b' else Font(size=10)

mf=wb.create_sheet('Mechanical Fixes')
for i,(n,w) in enumerate(zip(['Priority','Issue','Where','Status','Detail'],[9,32,34,14,70]),1):
    c=mf.cell(1,i,n); c.font=HDR; c.fill=DARK; c.alignment=WRAP
    mf.column_dimensions[get_column_letter(i)].width=w
for n,row in enumerate(json.load(open(D('data','mechanical-fixes.json'))),2):
    for i,v in enumerate([row['priority'],row['issue'],row['where'],row['status'],row['detail']],1):
        c=mf.cell(n,i,v); c.font=BASE; c.border=THIN; c.alignment=WRAP
        if i==4 and row['status'].startswith('YOU'):
            c.fill=YELLOW; c.font=Font(size=10,bold=True)
mf.freeze_panes='A2'

wb.save(D('docs','collection-worksheet.xlsx'))
print("docs/collection-worksheet.xlsx — %d rows" % len(rows))
print("  dropped: %s" % dict(dropped))
print("  needs title %d | needs meta %d | needs description %d" % (need_t,need_m,need_d))
