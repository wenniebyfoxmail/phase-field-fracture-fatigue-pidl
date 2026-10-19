"""Future single-attempt launcher; no resource/model/producer calls by default.

Run only on the approved producer after a separate final execution approval.
GNU timeout covers worker imports, CUDA admission, both arms and final export.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def launch(grant_path):
    grant = json.loads(grant_path.read_text())
    if platform.system() == 'Darwin' or grant.get('execution_authorized') is not True:
        raise PermissionError('separate final producer execution approval required')
    if not all(grant.get(k) for k in ('approved_commit', 'human_approval_reference', 'review_reference')):
        raise PermissionError('exact source, human approval and review required')
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() != grant['approved_commit']:
        raise PermissionError('exact approved source required')
    if grant.get('protocol') != 'S04-E034/v1-finite-raw-reaction-F8-F802-20261019' or grant.get('hostname') != platform.node():
        raise PermissionError('exact protocol/host required')
    runroot = Path(grant['run_root'])
    if runroot.parent != Path('/mnt/data2/drtao/wennie') or grant.get('output') != str(runroot/'output'):
        raise PermissionError('fresh canonical run root required')
    # O_EXCL root: a stopped attempt cannot be relaunched by this entrypoint.
    runroot.mkdir(exist_ok=False)
    for name in ('tmp', '.cache', '.jitcache'): (runroot/name).mkdir()
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='5', TMPDIR=str(runroot/'tmp'),
               XDG_CACHE_HOME=str(runroot/'.cache'), TORCH_EXTENSIONS_DIR=str(runroot/'.jitcache'))
    copied = runroot/'grant.json'; copied.write_text(json.dumps(grant, indent=2)+'\n')
    command = ['timeout', '--signal=TERM', '--kill-after=5s', '1790s', sys.executable,
               str(root/'SENS_tensile/run_s04_e034.py'), '--execute', '--grant', str(copied), '--out', str(runroot/'output')]
    started = time.time()
    with (runroot/'worker.log').open('xb') as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        (runroot/'launch_once.json').write_text(json.dumps(dict(pid=process.pid, command=command, cwd=str(root), commit=grant['approved_commit'], start_unix=started, retry=False), indent=2)+'\n')
        returncode = process.wait()
    ended = time.time()
    (runroot/'outer_receipt.json').write_text(json.dumps(dict(start_unix=started, end_unix=ended, elapsed_seconds=ended-started,
        conservative_GPU_hours=(ended-started)/3600, cumulative_GPU_hours_upper=1.108339654581623+(ended-started)/3600,
        returncode=returncode, retry=False, status='exited_pending_HQ' if returncode == 0 else 'stopped_no_retry'), indent=2)+'\n')
    return returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--execute', action='store_true'); parser.add_argument('--grant', type=Path)
    args = parser.parse_args()
    if not args.execute: print('Preparation only; no resource preflight or launch.')
    elif not args.grant: parser.error('exact approved grant required')
    else: sys.exit(launch(args.grant))
