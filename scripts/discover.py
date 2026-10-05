"""Cache primary-source metadata for manual literature selection (not a paper count)."""
import concurrent.futures as cf
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'library' / 'metadata'
CACHE.mkdir(parents=True, exist_ok=True)
HEADERS = {'User-Agent': 'comparative-method-literature-study/1.0 (academic bibliography)'}

def get(url, name):
    path = CACHE / name
    if not path.exists():
        r = requests.get(url, timeout=60, headers=HEADERS)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path.read_text()

def acl():
    tree = json.loads(get('https://api.github.com/repos/acl-org/acl-anthology/git/trees/master?recursive=1', 'acl-tree.json'))
    paths = [x['path'] for x in tree['tree'] if x['path'].startswith('data/xml/') and x['path'].endswith('.xml')]
    chosen = [p for p in paths if re.search(r'/(20(?:1[89]|2[0-6])\.(?:acl|emnlp|naacl|eacl|coling|lrec|sigtyp|sigmorphon|computel|lt4hala|scil|iwslt|conll|ranlp|jcl|cl|change)[^.]*|[JDPENW](?:0[5-9]|1[0-9]))\.xml$', p)]
    def fetch(p):
        try:
            root = ET.fromstring(get('https://raw.githubusercontent.com/acl-org/acl-anthology/master/' + p, 'acl-' + p.split('/')[-1]))
            found = []
            for volume in root.findall('volume'):
                for paper in volume.findall('paper'):
                    title = ''.join(paper.find('title').itertext()) if paper.find('title') is not None else ''
                    if not re.search(r'cognat|proto.?language|proto.?form|reconstruct.*(?:language|phonolog|word|ancest)|sound (?:change|correspond)|diachronic phon|historical linguist|etymolog|phonological recon|finite.state.*(?:phon|morph)|(?:phon|morph).*finite.state|two.level morphology', title, re.I):
                        continue
                    cid, vid, n = root.get('id'), volume.get('id'), paper.get('id')
                    if '.' in cid:
                        pid = f'{cid}-{vid}.{n}'
                    elif cid.startswith('W'):
                        pid = f'{cid}-{int(vid):02d}{int(n):02d}'
                    else:
                        pid = f'{cid}-{vid}{int(n):03d}'
                    authors = [' '.join([a.findtext('first',''),a.findtext('last','')]).strip() for a in paper.findall('author')]
                    abstract = ''.join(paper.find('abstract').itertext()) if paper.find('abstract') is not None else ''
                    found.append({'id':pid,'title':title,'authors':authors,'year':volume.findtext('meta/year'),'abstract':abstract,'area':'computational','doi':paper.findtext('doi'),'venue':volume.findtext('meta/booktitle'),'url':'https://aclanthology.org/'+pid+'/','pdf_url':'https://aclanthology.org/'+pid+'.pdf'})
            return found
        except Exception as e:
            print('ERROR', p, str(e), flush=True)
            return []
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        results = [item for batch in pool.map(fetch,chosen) for item in batch]
    (CACHE/'acl-candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print('ACL candidates',len(results),'collections',len(chosen))
    for r in results:
        print(r['id'],r['title'])

if __name__ == '__main__':
    acl()
