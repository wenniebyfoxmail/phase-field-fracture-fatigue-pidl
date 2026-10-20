"""Single detached producer with external deadline for dispatch accounting.

Original solver/supervisor unchanged. Dispatch45s and cleanup45s are unspent
reserves, not fabricated actual prior costs. GNU timeout exit124/137 is failure.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import time, perf_counter

from hybrid_inputs import read_manifest,sha256
from hybrid_producer_common import verify_package,write_json
from run_hybrid_producer import validate_card, initial_totals, require_enabled_execution


def dispatch_timeout_seconds(card, prior_wall, overhead):
    import math
    if not all(math.isfinite(v) and v >= 0 for v in (prior_wall, overhead)):
        raise ValueError('invalid actual cost/launch overhead')
    if card['dispatch_accounting'] != dict(dispatch_reserve_seconds=45, cleanup_reserve_seconds=45, kill_after_seconds=20):
        raise ValueError('reviewed outer deadline changed')
    reserve=card.get('historical_control_reserve_seconds',0.)
    if isinstance(reserve,bool) or not isinstance(reserve,(int,float)) or not math.isfinite(reserve) or reserve<0:
        raise ValueError('invalid unmeasured historical control reserve')
    # A reserve reduces usable wall time; it is never recorded as actual work.
    seconds = card['budget']['cpu_wall_hours']*3600 - prior_wall - 45 - 45 - overhead - reserve
    if seconds <= 0:
        raise RuntimeError('study allowance exhausted before dispatch')
    return seconds


def main():
    launch_started = perf_counter()
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
    supervisor_command=[sys.executable,'-u',str(code/'tools/run_hybrid_producer.py'),
             '--card',str(args.card.resolve()),'--package',str(args.package.resolve()),
             '--inputs',str(args.inputs.resolve()),'--review',str(args.review.resolve()),'--execute']
    prior = initial_totals(card, launch_started, code)
    seconds = dispatch_timeout_seconds(card, prior['wall_seconds'], perf_counter()-launch_started)
    command=['/usr/bin/timeout','--signal=TERM','--kill-after=20s',f'{seconds:.6f}s',*supervisor_command]
    reservation=root/'launch_reservation.json'
    fd=os.open(reservation,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    record=dict(state='reserved',command=command,artifact_id=package['artifact_id'],time=time(), actual_prior_wall_seconds=prior['wall_seconds'], outer_timeout_seconds=seconds,
                dispatch_reserve_seconds=45, cleanup_reserve_seconds=45,
                timeout_exit124_or137_is_failure=True)
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
