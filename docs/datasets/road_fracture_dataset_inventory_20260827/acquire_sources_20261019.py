"""Bounded public metadata acquisition; no authentication, forms or model execution."""
import concurrent.futures
import datetime
import json
import html
import re
import sys
from pathlib import Path
import urllib.request

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/dataset_completion_20261019')
SOURCES = {
    'ltpp_local_six': 'https://infopave.fhwa.dot.gov/Data/StandardDataRelease/',
    'pavetrack_pd': 'https://www.nature.com/articles/s41597-025-05748-5',
    'mnroad': 'https://www.dot.state.mn.us/mnroad/data/index.html',
    'westrack': 'https://infopave.fhwa.dot.gov/Westrack/Overview',
    'camhighways': 'https://drf.eng.cam.ac.uk/research/camhighways-dataset',
    'rdd2022': 'https://api.figshare.com/v2/articles/21431547',
    'rmdcrack': 'https://doi.org/10.57760/sciencedb.32469',
    'three_d_crack': 'https://doi.org/10.21227/2etq-xh36',
    'contract_watchlist': 'https://ieeexplore.ieee.org/document/9899382/',
    'zenodo_11945905': 'https://zenodo.org/api/records/11945905',
    'crackmnist': 'https://zenodo.org/api/records/18454958',
    'mendeley_dic_fatigue': 'https://data.mendeley.com/datasets/dywwnjv22h/1',
    'multitemporal_concrete': 'https://zenodo.org/api/records/15187675',
    'nccd_pf': 'https://zenodo.org/api/records/8215100',
    'idics_sample1': 'https://idics.org/challenge/',
    'ncat_test_track': 'https://eng.auburn.edu/research/centers/ncat/testtrack/index.html',
    'virginia_smart_road': 'https://www.vtti.vt.edu/facilities/highway-section.html',
    'prospective_cambridge_pilot': 'https://drf.eng.cam.ac.uk/research/camhighways-dataset',
}

def get(url, limit=4_000_000):
    req = urllib.request.Request(url, headers={'User-Agent': 'Wennie-research-data-audit/1.0'})
    with urllib.request.urlopen(req, timeout=35) as res:
        data = res.read(limit + 1)
        if len(data) > limit:
            raise ValueError('bounded retrieval exceeded limit')
        return data, res.status, res.url, dict(res.headers)

def fetch(item):
    key, url = item
    out = ROOT / key
    out.mkdir(parents=True, exist_ok=True)
    receipt = {'dataset_id': key, 'official_url': url, 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'attempts': []}
    # The official API gives exact file inventories. Text reader is only fallback.
    api = '/api/records/' in url or 'api.figshare.com' in url
    urls = [url, 'https://r.jina.ai/' + url.replace('/api/records/', '/records/')] if api else ['https://r.jina.ai/' + url, url]
    for target in urls:
        try:
            data, status, final, headers = get(target)
            suffix = '.json' if api and target == url else '.txt'
            dest = out / ('official_metadata' + suffix)
            dest.write_bytes(data)
            receipt['attempts'].append({'url':target, 'status':status, 'final_url':final, 'bytes':len(data), 'file':str(dest)})
            if suffix == '.json':
                obj=json.loads(data)
                receipt['title']=obj.get('metadata', {}).get('title', obj.get('title'))
                receipt['files']=[{'name':f.get('key',f.get('name')), 'bytes':f.get('size'), 'url':f.get('links',{}).get('self',f.get('download_url'))} for f in obj.get('files',[])]
                receipt['license']=obj.get('metadata',{}).get('license',obj.get('license'))
            receipt['retrieval']='retrieved; source content requires inspection'
            break
        except Exception as exc:
            receipt['attempts'].append({'url':target, 'error':str(exc)})
    else:
        receipt['retrieval']='blocked'
    return receipt

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        receipts=list(pool.map(fetch,SOURCES.items()))
    (ROOT/'source_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2))
    for r in receipts:
        print(json.dumps({k:r.get(k) for k in ['dataset_id','retrieval','title','license','files']},ensure_ascii=False),flush=True)

def supplements():
    receipts=json.loads((ROOT/'source_receipts.json').read_text())
    for r in receipts:
        p=ROOT/r['dataset_id']/'official_metadata.txt'
        if p.exists():
            text=p.read_text()
            objects=[]
            for raw in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',text,re.S):
                try: objects.append(json.loads(raw))
                except ValueError: pass
            if objects:
                (p.parent/'structured_metadata.json').write_text(json.dumps(objects,ensure_ascii=False,indent=2))
            if '<html' in text[:500] or '<!doctype' in text[:500].lower():
                text=re.sub(r'<(script|style|nav|header|footer)\b[^>]*>.*?</\1>','',text,flags=re.S|re.I)
                text=html.unescape(re.sub('<[^>]+>',' ',text))
                text=re.sub(r'\s+',' ',text)
            (p.parent/'readable_source.txt').write_text(text)
    jobs=[]
    for r in receipts:
        for f in r.get('files',[]):
            if f.get('bytes') is not None and f['bytes']<4_000_000 and f.get('url'):
                jobs.append((r['dataset_id'], f['name'], f['url']))
    jobs.extend([
        ('mendeley_dic_fatigue','file_listing_api.json','https://data.mendeley.com/public-api/datasets/dywwnjv22h/files?folder_id=root&version=1'),
        ('multitemporal_concrete','github_tree.json','https://api.github.com/repos/saidharb/Multi-Temporal-Crack-Segmentation-Dataset/git/trees/main?recursive=1'),
        ('ncat_test_track','collection_protocol.txt','https://r.jina.ai/https://www.eng.auburn.edu/research/centers/ncat/files/technical-reports/rep04-03.pdf'),
        ('rdd2022','author_repository.json','https://api.github.com/repos/sekilab/RoadDamageDetector/contents/RDD2022'),
    ])
    def task(job):
        key,name,url=job; rec={'dataset_id':key,'name':name,'url':url}
        try:
            data,status,final,headers=get(url)
            dest=ROOT/key/name
            dest.write_bytes(data)
            rec.update(status=status,bytes=len(data),file=str(dest),final_url=final)
        except Exception as e: rec['error']=str(e)
        return rec
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(task,jobs))
    (ROOT/'supplement_receipts.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    for rec in results: print(json.dumps(rec,ensure_ascii=False),flush=True)

if __name__=='__main__':
    supplements() if '--supplements' in sys.argv else main()
