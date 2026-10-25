"""Local fixed-package acceptance only; never downloads or runs scientific code."""
import argparse,gzip,hashlib,json,tarfile
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()

def receive(archive,out,expected_sha,expected_bytes,limit=2*1024**3+1024**2):
    if archive.stat().st_size!=expected_bytes or sha(archive)!=expected_sha:raise ValueError('server fixed archive identity')
    with gzip.open(archive,'rb') as src:
        raw=0
        while True:
            b=src.read(1024**2)
            if not b:break
            raw+=len(b)
            if limit is not None and raw>limit:raise ValueError('gzip raw cap')
    out.mkdir(parents=True,exist_ok=False);seen=set();total=0
    with tarfile.open(archive,'r:gz') as t:
        for m in t:
            name=m.name
            if not m.isfile() or name in seen or name.startswith('/') or '\\' in name or '..' in Path(name).parts:raise ValueError('unsafe/duplicate package member')
            seen.add(name);total+=m.size
            if limit is not None and total>limit:raise ValueError('raw bound')
            dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(m) as src,dest.open('xb') as dst:
                while True:
                    b=src.read(1024**2)
                    if not b:break
                    dst.write(b)
    inventory=json.loads((out/'file_manifest.json').read_text())['files']
    if seen!=set(inventory)|{'file_manifest.json'}:raise ValueError('exact fixed inventory')
    for name,r in inventory.items():
        p=out/name
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('received binding '+name)
    # A stopped or incomplete run is receivable, never a fabricated science zero.
    if (out/'run/output_receipt.json').exists():
        for name,r in json.loads((out/'run/output_receipt.json').read_text())['files'].items():
            if name.startswith('/') or '\\' in name or '..' in Path(name).parts or 'run/'+name not in inventory:raise ValueError('unsafe output receipt path')
            p=out/'run'/name
            if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('run output binding')
    result=dict(retrieval='verified',archive_sha256=expected_sha,files=len(seen),raw_bytes=total,scientific_review='pending saved-output recomputation and original-figure review',rerun=False)
    (out.parent/(out.name+'-reception.json')).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unlimited-resources',action='store_true');p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sha256');p.add_argument('--bytes',type=int);p.add_argument('--server-receipt',type=Path);a=p.parse_args()
    if a.server_receipt:
        r=json.loads(a.server_receipt.read_text());a.sha256=r['sha256'];a.bytes=r['bytes']
    if a.sha256 is None or a.bytes is None:raise ValueError('exact server receipt SHA and byte count required')
    receive(a.archive,a.out,a.sha256,a.bytes,limit=None if a.unlimited_resources else 2*1024**3+1024**2)
