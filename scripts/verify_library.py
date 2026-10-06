"""Audit catalogue consistency and PDF integrity without any network requests.

Default checks public files plus the recorded acquisition snapshot. --local
requires every successfully acquired PDF to exist and match its recorded hash.
The distinction is included in the report; public CI cannot verify absent copies.
"""
import argparse
import collections
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def audit(local=False, min_works=100):
    sources = json.loads((ROOT/'bibliography/sources.json').read_text())
    downloads = json.loads((ROOT/'bibliography/downloads.json').read_text())
    notes = json.loads((ROOT/'bibliography/reading-notes.json').read_text())
    errors = []
    for name, items in [('sources',sources),('downloads',downloads),('notes',notes)]:
        ids = [x['id'] for x in items]
        if len(ids)!=len(set(ids)):
            errors.append(f'duplicate IDs in {name}')
    by = {x['id']:x for x in sources}
    dn = {x['id']:x for x in downloads}
    if set(by)!=set(dn) or set(by)!={x['id'] for x in notes}:
        errors.append('sources, download attempts and notes must cover the same IDs')
    for s in sources:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',s['id']):
            errors.append(f'unsafe ID: {s["id"]}')
        for field in ['title','authors','year','url','pdf_url','areas','kind','license']:
            if not s.get(field): errors.append(f'{s["id"]}: missing {field}')
        if s.get('redistribute') and not s.get('rights_basis'):
            errors.append(f'{s["id"]}: no redistribution basis')
        if s.get('included_in') and s['included_in'] not in by:
            errors.append(f'{s["id"]}: unknown containing work')
        if not isinstance(s.get('qualifies_for_download_floor'),bool):
            errors.append(f'{s["id"]}: missing count decision')
    verified = []
    downloaded = [d for d in downloads if d['status']=='downloaded']
    for d in downloaded:
        s=by.get(d['id'],{})
        expected_folder='library/open' if s.get('redistribute') else 'library/downloads'
        if d['path']!=f'{expected_folder}/{d["id"]}.pdf':
            errors.append(f'{d["id"]}: unexpected PDF path'); continue
        if not re.fullmatch('[0-9a-f]{64}',d['sha256']):
            errors.append(f'{d["id"]}: invalid SHA-256')
        if d['pages']<2 or d['bytes']<1000:
            errors.append(f'{d["id"]}: implausible complete-work metadata')
        p=ROOT/d['path']
        required=local or s.get('redistribute',False)
        if not p.exists():
            if required: errors.append(f'{d["id"]}: required file missing')
            continue
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=d['sha256'] or len(data)!=d['bytes']:
            errors.append(f'{d["id"]}: file hash/size mismatch'); continue
        try:
            if len(PdfReader(p).pages)!=d['pages']:
                errors.append(f'{d["id"]}: page-count mismatch'); continue
        except Exception as e:
            errors.append(f'{d["id"]}: invalid PDF: {e}'); continue
        verified.append(d['id'])
    public_expected={d['path'] for d in downloaded if by[d['id']].get('redistribute')}
    public_actual={str(p.relative_to(ROOT)) for p in (ROOT/'library/open').glob('*.pdf')}
    if public_expected!=public_actual:
        errors.append('public PDF directory differs from approved manifest')
    qualifying=[d for d in downloaded if by[d['id']].get('qualifies_for_download_floor')]
    hashes={d['sha256'] for d in qualifying}
    if len(hashes)<min_works:
        errors.append(f'only {len(hashes)} qualifying distinct hashes; need {min_works}')
    if len(qualifying)!=len(hashes):
        errors.append('qualifying works contain identical PDFs')
    for n in notes:
        for field in ['reading_level','finding','formalization_use','caution']:
            if not n.get(field): errors.append(f'{n["id"]}: missing note {field}')
        pages=dn.get(n['id'],{}).get('pages',0)
        if any(not isinstance(p,int) or p<1 or p>pages for p in n['pdf_pages_examined']):
            errors.append(f'{n["id"]}: invalid examined PDF page')
    terminology=json.loads((ROOT/'bibliography/terminology-readings.json').read_text())['readings']
    if len({r['source_id'] for r in terminology}) != len(terminology):
        errors.append('duplicate source in terminology readings')
    for r in terminology:
        d=dn.get(r['source_id'],{})
        if r['path'] != d.get('path') or r['sha256'] != d.get('sha256'):
            errors.append(f'{r["source_id"]}: terminology reading differs from acquisition record')
        if any(not isinstance(p,int) or not 1 <= p <= d.get('pages',0) for p in r['pdf_pages_read']):
            errors.append(f'{r["source_id"]}: invalid terminology reading page')
        if not set(r['pdf_pages_visually_checked']) <= set(r['pdf_pages_read']):
            errors.append(f'{r["source_id"]}: visual reading outside recorded pages')
    coverage=collections.Counter()
    for d in qualifying: coverage.update(by[d['id']]['areas'])
    return {
        'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'mode':'full-local' if local else 'public-and-manifest',
        'catalogue_entries':len(sources), 'downloaded_pdfs_recorded':len(downloaded),
        'qualifying_distinct_works_recorded':len(hashes),
        'qualifying_works_verified_on_disk':sum(d['id'] in verified for d in qualifying),
        'all_pdfs_verified_on_disk':len(verified), 'public_pdfs':len(public_expected),
        'retained_bytes_recorded':sum(d['bytes'] for d in downloaded),
        'retained_pages_recorded':sum(d['pages'] for d in downloaded),
        'coverage_overlapping':dict(sorted(coverage.items())),
        'reading_levels':dict(collections.Counter(n['reading_level'] for n in notes)),
        'count_exclusions':[{ 'id':d['id'],'reason':by[d['id']]['count_exclusion']} for d in downloaded if not by[d['id']]['qualifies_for_download_floor']],
        'failed_acquisitions':[d['id'] for d in downloads if d['status']!='downloaded'],
        'errors':errors, 'passed':not errors,
        'limitations':['PDF validity, page counts and hashes do not prove bibliographic completeness or that every page has been read.',
                      'Reading notes record selected excerpts. Scanned and font-encoded PDFs may have incomplete extracted text.',
                      'A public checkout can verify only files actually present; the full-local audit is separate.']
    }


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--local',action='store_true')
    p.add_argument('--min-works',type=int,default=100)
    p.add_argument('--output',type=Path)
    a=p.parse_args();report=audit(a.local,a.min_works)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
