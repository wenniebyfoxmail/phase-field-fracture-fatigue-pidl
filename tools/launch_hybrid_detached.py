"""Exactly one detached producer supervisor; reserve before spawn, never retry."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import time

from hybrid_inputs import read_manifest,sha256
from hybrid_producer_common import verify_package,write_json
from run_hybrid_producer import validate_card, require_enabled_execution


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--card',type=Path,required=True);p.add_argument('--package',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--review',type=Path,required=True)
    args=p.parse_args()
    if platform.system()!='Linux':raise RuntimeError('launch is Linux producer-only')
    card=read_manifest(args.card);validate_card(card)
    require_enabled_execution(card)
    code=Path(__file__).resolve().parents[1];package=read_manifest(args.package)
    verify_package(code,package)
    review=read_manifest(args.review)
    if (review.get('verdict')!='REVIEW_PASS' or review.get('card_sha256')!=sha256(args.card)
            or review.get('artifact_id')!=package['artifact_id']):raise RuntimeError('exact producer review missing')
    root=Path(card['run_root'])
    if Path(card['archive_root']).exists():raise FileExistsError('archive already exists; inspect, never relaunch')
    command=[sys.executable,'-u',str(code/'tools/run_hybrid_producer.py'),
             '--card',str(args.card.resolve()),'--package',str(args.package.resolve()),
             '--inputs',str(args.inputs.resolve()),'--review',str(args.review.resolve()),'--execute']
    reservation=root/'launch_reservation.json'
    fd=os.open(reservation,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    record=dict(state='reserved',command=command,artifact_id=package['artifact_id'],time=time())
    with os.fdopen(fd,'w') as f:
        json.dump(record,f);f.flush();os.fsync(f.fileno())
    env=os.environ.copy()
    for d in ['tmp','cache','jitcache']:(root/d).mkdir(exist_ok=True)
    env.update(PYTHONPATH=f'{root}/deps:{code}/source:{code}/tools',TMPDIR=str(root/'tmp'),
               XDG_CACHE_HOME=str(root/'cache'),TORCH_EXTENSIONS_DIR=str(root/'jitcache'),
               OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='16',MKL_NUM_THREADS='16',
               CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg',MPLCONFIGDIR=str(root/'cache/matplotlib'))
    with (root/'supervisor.log').open('x') as log:
        proc=subprocess.Popen(command,cwd=code,env=env,stdin=subprocess.DEVNULL,
                              stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record.update(state='spawned',pid=proc.pid)
    print(json.dumps(record),flush=True)
    write_json(reservation,record)
    # A disconnect or a following write error leaves reservation intact. Inspect
    # pid/cwd/cmdline and receipts; this tool refuses every second invocation.


if __name__=='__main__':main()
