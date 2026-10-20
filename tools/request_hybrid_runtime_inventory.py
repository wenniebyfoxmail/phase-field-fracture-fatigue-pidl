"""Show by default; one explicitly approved metadata-only SSH attempt.

No source file is installed on the producer: exact reviewed Python is passed
through stdin to an isolated interpreter under GNU timeout. No retry/fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from time import perf_counter


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def request_for(payload, dependency_root):
    remote = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=3s', '20s',
              '/usr/bin/env', 'CUDA_VISIBLE_DEVICES=', 'PYTHONDONTWRITEBYTECODE=1',
              'OMP_NUM_THREADS=1', 'OPENBLAS_NUM_THREADS=1', 'MKL_NUM_THREADS=1',
              '/usr/bin/python3', '-I', '-B', '-', '--dependency-root', dependency_root]
    return dict(schema='hybrid-runtime-inventory-request-v1',
                payload_file='tools/hybrid_runtime_inventory.py', payload_sha256=sha(payload),
                ssh_argv=['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes',
                          '-o', 'ConnectTimeout=10', '-o', 'ConnectionAttempts=1',
                          'drtao@172.16.100.2', shlex.join(remote)],
                expected_hostname='GPUServer8', expected_account='drtao',
                expected_python='3.10.12', dependency_root=dependency_root,
                local_timeout_seconds=45, remote_timeout_seconds=20,
                remote_kill_after_seconds=3, max_cpu_seconds=10,
                max_address_space_bytes=256*2**20, gpu_seconds=0,
                permission='PENDING_HUMAN_APPROVAL_FOR_THIS_SINGLE_READ_ONLY_ACTION',
                scientific_execution_authorized=False, retries=0)


def execute(request, code_root, output):
    payload = Path(code_root)/request['payload_file']
    if sha(payload) != request['payload_sha256']:
        raise RuntimeError('reviewed inventory payload differs')
    expected = request_for(payload, request['dependency_root'])
    if request != expected:
        raise RuntimeError('inventory destination, command or limits differ')
    output = Path(output)
    # Reserve before contacting host. Unknown outcome cannot silently relaunch.
    with output.open('x') as handle:
        handle.write(json.dumps(dict(status='reserved', request=request))+'\n')
    started = perf_counter()
    receipt = dict(status='failed', request=request, scientific_execution_authorized=False)
    try:
        proc = subprocess.run(request['ssh_argv'], input=payload.read_bytes(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=request['local_timeout_seconds'], check=False,
                              start_new_session=True)
        if len(proc.stdout)>1024*1024 or len(proc.stderr)>1024*1024:
            raise RuntimeError('unexpectedly large inventory response')
        receipt.update(returncode=proc.returncode,
                       stderr=proc.stderr.decode('utf-8',errors='replace'))
        if proc.returncode != 0 or proc.stderr:
            raise RuntimeError('single inventory SSH attempt failed; no retry')
        observed = json.loads(proc.stdout)
        receipt['observed'] = observed
        if (observed['hostname']!=request['expected_hostname'] or
                observed['account']!=request['expected_account'] or
                observed['python']!=request['expected_python'] or
                observed['scientific_imports'] or observed['scientific_states_opened'] or
                observed['metadata_errors']):
            raise RuntimeError('runtime inventory identity or metadata incomplete')
        receipt['status']='observed_metadata_only_not_runtime_admission'
    except Exception as exc:
        receipt['error']=f'{type(exc).__name__}: {exc}'
    finally:
        receipt['local_wall_seconds']=perf_counter()-started
        receipt['gpu_seconds']=0.
        receipt['numerical_seconds']=0.
        output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',required=True,type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    request=json.loads(args.request.read_text())
    if not args.execute:
        print(json.dumps(request,indent=2));return
    if args.output is None:raise ValueError('single-attempt receipt path required')
    code=Path(__file__).resolve().parents[1]
    result=execute(request,code,args.output)
    print(json.dumps(result,indent=2))
    if result['status']=='failed':raise SystemExit(1)


if __name__=='__main__':main()
