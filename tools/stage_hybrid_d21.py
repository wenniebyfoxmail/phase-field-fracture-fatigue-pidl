"""Small hash-closed code receiver and once-only original detached launcher.

Run on the authorized producer with the compressed bundle on stdin. Private
inputs and the previously verified OSQP runtime remain on the same server.
Unknown dispatch outcomes must be inspected, never submitted a second time.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys
import tarfile
from time import perf_counter


def main():
    started = perf_counter()
    raw = sys.stdin.buffer.read(4*2**20+1)
    digest = lambda b: hashlib.sha256(b).hexdigest()
    if len(raw) > 4*2**20 or digest(raw) != sys.argv[1]:
        raise RuntimeError('bundle size or digest differs')
    if socket.gethostname() != 'GPUServer8' or pwd.getpwuid(os.geteuid()).pw_name != 'drtao':
        raise RuntimeError('wrong producer/account')
    if not os.path.ismount('/mnt/data2'):
        raise RuntimeError('canonical storage mount unavailable')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        if len(members) > 160 or sum(m.size for m in members) > 8*2**20:
            raise RuntimeError('expanded code cap')
        for m in members:
            path = Path(m.name)
            if not m.isfile() or path.is_absolute() or '..' in path.parts or m.name in files:
                raise RuntimeError('unsafe bundle member')
            files[m.name] = tar.extractfile(m).read()
    card = json.loads(files['execution_card.json'])
    package = json.loads(files['source_manifest.json'])
    if digest(json.dumps(package['files'],sort_keys=True,allow_nan=False).encode()) != package['artifact_id']:
        raise RuntimeError('source artifact mismatch')
    if set(files) != {'execution_card.json','source_manifest.json','benchmark_admission.json'} | {'code/'+p for p in package['files']}:
        raise RuntimeError('bundle is not closed')
    for rel, want in package['files'].items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or digest(files['code/'+rel]) != want:
            raise RuntimeError('source hash mismatch')
        if rel.endswith('.py'): compile(files['code/'+rel],rel,'exec')
    run = card['run_id']
    if not run.startswith('pf_hybrid_d21_complete_') or '/' in run or '..' in run:
        raise RuntimeError('invalid run identity')
    root = Path('/mnt/data2/drtao/wennie')/run
    archive = Path('/mnt/data2/drtao/pidl_archives')/run
    if card['run_root'] != str(root) or card['archive_root'] != str(archive):
        raise RuntimeError('attribution differs')
    for p in (root,archive):
        if p.exists() or any(x.is_symlink() for x in [p,*p.parents]):
            raise RuntimeError('nonfresh/unsafe destination; inspect existing task')
    root.mkdir()
    for name, data in files.items():
        target=root/name; target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f: f.write(data)
    deps = json.loads(files['code/docs/research/S04/hybrid_constrained_design_20261019/solver_repair_v12/retained_deps_manifest.json'])
    old = Path('/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3/deps')
    copied = 0
    for name,want in deps['files'].items():
        rel=Path(name); source=old/rel
        if rel.is_absolute() or '..' in rel.parts or any(x.is_symlink() for x in [source,*source.parents]):
            raise RuntimeError('unsafe retained dependency')
        data=source.read_bytes(); copied+=len(data)
        if copied > 2**20 or digest(data) != want: raise RuntimeError('retained OSQP differs')
        target=root/'deps'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
    env=dict(os.environ,PYTHONPATH=f'{root}/deps:{root}/code/source:{root}/code/tools',
             CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
    if len(sys.argv)>2 and sys.argv[2]=='stage-only':
        receipt=dict(state='staged_not_launched',bundle_sha256=sys.argv[1],artifact_id=package['artifact_id'],
                     same_host_dependency_bytes=copied,wall_seconds=perf_counter()-started)
        (root/'stage_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt),flush=True)
        return
    command=['/usr/bin/python3','-B',str(root/'code/tools/launch_hybrid_detached.py'),
             '--card',str(root/'execution_card.json'),'--package',str(root/'source_manifest.json'),
             '--review',str(root/'benchmark_admission.json'),
             '--inputs','/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3/inputs']
    result=subprocess.check_output(command,cwd=root/'code',env=env,text=True,timeout=30)
    receipt=dict(state='dispatched',launch=json.loads(result),bundle_sha256=sys.argv[1],
                 artifact_id=package['artifact_id'],same_host_dependency_bytes=copied,
                 code_only_no_private_data=True,wall_seconds=perf_counter()-started)
    (root/'dispatch_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)


if __name__ == '__main__':main()
