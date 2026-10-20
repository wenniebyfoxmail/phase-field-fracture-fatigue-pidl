"""Single bounded stdin bundle verification/extraction and reviewed dispatch.

Use external timeout20s plus kill3s, local45s. No retry or broad cleanup.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import time

ROOT = Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3')
ARCHIVE = Path('/mnt/data2/drtao/pidl_archives/pf_hybrid_solver_v6_20261020_r3')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    started = time.perf_counter()
    if socket.gethostname() != 'GPUServer8' or not ROOT.is_dir():
        raise RuntimeError('wrong producer/staging root')
    if any(p.is_symlink() for p in [ROOT,*ROOT.parents]):
        raise RuntimeError('symlink in run root')
    if ARCHIVE.exists() or (ROOT/'code').exists() or (ROOT/'launch_reservation.json').exists():
        raise RuntimeError('fresh dispatch required; never retry')
    with (ROOT/'dispatch_reservation.json').open('x') as f:
        json.dump(dict(state='reserved',epoch=time.time(),bundle_sha256=sys.argv[1]),f)
    payload = sys.stdin.buffer.read(2*2**20+1)
    if len(payload)>2*2**20 or sha(payload)!=sys.argv[1]:
        raise RuntimeError('bundle exceeds cap or differs')
    files={}
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tar:
        members=tar.getmembers()
        if len(members)>256 or sum(m.size for m in members)>4*2**20:
            raise RuntimeError('expanded bundle cap')
        for m in members:
            p=Path(m.name)
            if not m.isfile() or p.is_absolute() or '..' in p.parts or m.name in files:
                raise RuntimeError('nonlocal/duplicate/nonregular member')
            files[m.name]=tar.extractfile(m).read()
    package=json.loads(files['source_manifest.json'])
    expected=sha(json.dumps(package['files'],sort_keys=True,allow_nan=False).encode())
    if expected!=package['artifact_id']:
        raise RuntimeError('artifact differs')
    names={'source_manifest.json','execution_card.json','execution_review.json'}|{'code/'+p for p in package['files']}
    if set(files)!=names:
        raise RuntimeError('bundle file closure differs')
    for rel,want in package['files'].items():
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or sha(files['code/'+rel])!=want:
            raise RuntimeError('reviewed source differs')
    review=json.loads(files['execution_review.json'])
    card=json.loads(files['execution_card.json'])
    if (review['verdict']!='REVIEW_PASS' or review['artifact_id']!=expected or
            review['card_sha256']!=sha(files['execution_card.json']) or
            card['run_root']!=str(ROOT) or card['archive_root']!=str(ARCHIVE) or
            card['execution_enabled'] is not True or
            card['dispatch_accounting']!=dict(dispatch_reserve_seconds=45,cleanup_reserve_seconds=45,kill_after_seconds=20)):
        raise RuntimeError('exact executable review/card differs')
    staged=json.loads((ROOT/'stage_receipt.json').read_text())
    if staged.get('passed') is not True:
        raise RuntimeError('no staged input receipt')
    for item in staged['inventory']:
        p=ROOT/item['target']
        if p.is_symlink() or sha(p.read_bytes())!=item['sha256']:
            raise RuntimeError('staged input/dependency changed')
    for name,data in files.items():
        dest=ROOT/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:
            f.write(data)
    if time.perf_counter()-started>15:
        raise RuntimeError('dispatch preparation cap; no spawn')
    env=os.environ.copy()
    env.update(PYTHONPATH=f'{ROOT}/deps:{ROOT}/code/source:{ROOT}/code/tools',
               PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',
               OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='16',MKL_NUM_THREADS='16')
    cmd=['/usr/bin/python3','-B',str(ROOT/'code/tools/launch_hybrid_budgeted.py'),
         '--card',str(ROOT/'execution_card.json'),'--package',str(ROOT/'source_manifest.json'),
         '--inputs',str(ROOT/'inputs'),'--review',str(ROOT/'execution_review.json')]
    result=subprocess.check_output(cmd,env=env,cwd=ROOT/'code',timeout=10,text=True)
    record=dict(state='dispatched',launch=json.loads(result),wall_seconds=time.perf_counter()-started,
                bundle_sha256=sys.argv[1],artifact_id=expected,card_sha256=review['card_sha256'],
                dispatch_reserve_seconds=45,retries=0)
    (ROOT/'dispatch_receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)


if __name__=='__main__':
    main()
