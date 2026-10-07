#!/usr/bin/env python3
"""Electrical tool R1 Part A: scan every cached Verified source (out/verified/cache) for breaker,
AWG/wire-size and GFCI statements. Read-only, offline. Usage: electrical_source_scan.py OUT.json
Evidence only: nothing found here is a database value until a Verified round extracts it."""
import json,re,sys,os
from pathlib import Path
root=Path(__file__).resolve().parent.parent
m=json.load(open(root/'data/verified/cache-manifest.json'))['entries']
RX=re.compile(r'(?i)(\b\d{1,2}\s*(?:awg|ga\b|gauge)|wire\s*(?:size|gauge)|\bbreaker\b|\bGFCI\b|\bGFI\b|double[- ]pole|\d{2}\s*a(?:mp)?\s*(?:double|2)[- ]pole)')
out=[]
import pypdf,io
for key,e in m.items():
    f=root/'out/verified/cache'/(e.get('cache_file') or 'NONE')
    if not f.exists(): continue
    b=f.read_bytes()
    if b[:4]==b'%PDF':
        try:
            rd=pypdf.PdfReader(io.BytesIO(b))
            for i,p in enumerate(rd.pages):
                t=p.extract_text() or ''
                for mm in RX.finditer(t):
                    out.append(dict(key=key,page=i+1,kind='pdf',span=t[max(0,mm.start()-160):mm.end()+160].replace('\n',' ')))
        except Exception as ex:
            out.append(dict(key=key,kind='pdf-error',span=str(ex)[:100]))
    else:
        t=b.decode('utf-8','ignore')
        t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
        t=re.sub(r'<[^>]+>',' ',t)
        for mm in RX.finditer(t):
            out.append(dict(key=key,kind='html',span=re.sub(r'\s+',' ',t[max(0,mm.start()-160):mm.end()+160])))
json.dump(out,open(sys.argv[1],'w'),indent=1)
print(len(out))
