"""Download selected openly accessible works; validate PDFs and retain page-indexed text.

No login, paywall bypass, or content-search snippets are used. Public redistribution
is a separate, explicit decision in the source catalogue. Run from any directory.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
logging.getLogger('pypdf').setLevel(logging.ERROR)

def fetch(source, expected=None):
    sid = source['id']
    folder = 'library/open' if source.get('redistribute') else 'library/downloads'
    path = ROOT / folder / (sid + '.pdf')
    path.parent.mkdir(parents=True, exist_ok=True)
    text_path = ROOT / 'library/text' / (sid + '.json')
    text_path.parent.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / 'library/downloads' / (sid + '.pdf')
    try:
        resolved = source['pdf_url']
        if not path.exists():
            if source.get('redistribute') and old_path.exists():
                path.write_bytes(old_path.read_bytes())
            else:
                errors = []
                for url in [source['pdf_url']] + source.get('fallback_pdf_urls', []):
                    try:
                        r = requests.get(url, timeout=(15,90), headers={'User-Agent':'HistoricalLinguisticsResearch/1.0 (public academic source download)'})
                        r.raise_for_status()
                        if not r.content.lstrip().startswith(b'%PDF-'):
                            raise ValueError('response is not a PDF')
                        if expected and hashlib.sha256(r.content).hexdigest() != expected:
                            raise ValueError('source bytes changed: SHA-256 differs from acquisition snapshot; inspect a new version separately')
                        tmp = path.with_suffix('.tmp')
                        tmp.write_bytes(r.content)
                        check = PdfReader(tmp)
                        if len(check.pages) < 2:
                            raise ValueError('less than two pages; inspect manually')
                        tmp.replace(path)
                        resolved = r.url
                        break
                    except Exception as e:
                        errors.append(f'{url}: {e}')
                else:
                    raise ValueError('; '.join(errors))
        data = path.read_bytes()
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('local PDF differs from acquisition snapshot')
        reader = PdfReader(path)
        if not text_path.exists():
            pages = []
            for i,page in enumerate(reader.pages):
                try:
                    pages.append({'pdf_page':i+1,'text':page.extract_text() or ''})
                except Exception as e:
                    pages.append({'pdf_page':i+1,'text':'','extraction_error':str(e)})
            text_path.write_text(json.dumps(pages,ensure_ascii=False,indent=2))
        else:
            pages = json.loads(text_path.read_text())
        result = {'id':sid,'status':'downloaded','path':str(path.relative_to(ROOT)),
                  'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                  'pages':len(reader.pages),'text_characters':sum(len(p['text']) for p in pages),
                  'resolved_url':resolved,'checked_at':datetime.now(timezone.utc).isoformat()}
        print(f'OK {sid}: {result["pages"]} pages, {result["bytes"]} bytes',flush=True)
        return result
    except Exception as e:
        print(f'FAILED {sid}: {e}',flush=True)
        return {'id':sid,'status':'failed','error':str(e),'checked_at':datetime.now(timezone.utc).isoformat()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids',nargs='+')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--available',action='store_true',help='Only fetch works successfully acquired in the committed snapshot')
    parser.add_argument('--record',action='store_true',help='Explicitly update the committed acquisition ledger; default writes an ignored local report')
    args = parser.parse_args()
    sources = json.loads((ROOT/'bibliography/sources.json').read_text())
    ledger = ROOT/'bibliography/downloads.json'
    previous = {r['id']:r for r in json.loads(ledger.read_text())} if ledger.exists() else {}
    if args.workers < 1:
        parser.error('--workers must be positive')
    known = {s['id'] for s in sources}
    if args.ids and set(args.ids) - known:
        parser.error('unknown source IDs: '+', '.join(sorted(set(args.ids)-known)))
    selected = [s for s in sources if s.get('pdf_url') and (not args.ids or s['id'] in args.ids)
                and (not args.available or previous.get(s['id'],{}).get('status')=='downloaded')]
    results = {}
    def job(source):
        return fetch(source,previous.get(source['id'],{}).get('sha256'))
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(job,selected):
            results[result['id']] = result
    if args.record:
        # A transient failure must not erase evidence of a previous acquisition.
        for sid,result in results.items():
            if result['status']=='downloaded' or sid not in previous or previous[sid]['status']!='downloaded':
                previous[sid]=result
        ledger.write_text(json.dumps(sorted(previous.values(),key=lambda r:r['id']),ensure_ascii=False,indent=2)+'\n')
    report = ROOT/'library/metadata/fetch-report.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(list(results.values()),ensure_ascii=False,indent=2)+'\n')
    successful = [r for r in results.values() if r['status']=='downloaded']
    failures = len(results)-len(successful)
    print(f'{len(successful)} verified PDFs in this run; {failures} failed; {len({r["sha256"] for r in successful})} unique hashes')
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
