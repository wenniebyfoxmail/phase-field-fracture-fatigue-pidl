#!/usr/bin/env python3
"""Prepared R002 bounded read-only status/retrieval, not execution authority."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

CTL = Path(__file__).resolve().parent
LOCAL = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/recovery_20261020_R002')
ROOT = '/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002'
OUTPUT = ROOT + '/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002'
SSH_OPTIONS = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ConnectionAttempts=1',
               '-o', 'ControlMaster=no', '-o', 'ControlPath=none', '-o', 'ServerAliveInterval=10',
               '-o', 'ServerAliveCountMax=2']
RSYNC_SSH = shlex.join(['ssh'] + SSH_OPTIONS)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()

def command(dest, name, seconds, args):
    """Exclusive logs, one child group per call; no retry or remote termination."""
    with (dest/(name+'.stdout')).open('xb') as out, (dest/(name+'.stderr')).open('xb') as err:
        child = subprocess.Popen(args, stdout=out, stderr=err, start_new_session=True)
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait()
            raise RuntimeError(name+': timeout, remote state unknown; stop without retry')
        if code:
            raise RuntimeError(name+': exit '+str(code)+'; stop without retry')
    return (dest/(name+'.stdout')).read_bytes()

def remote(dest, name, seconds, source):
    # All remote snippets are stdlib-only read/hash operations in the exact R002 root.
    return command(dest, name, seconds,
                   ['ssh']+SSH_OPTIONS+['gpu-taobo', '/usr/bin/python3 -B -c '+shlex.quote(source)])

def main():
    template = json.loads((CTL/'decision_template.json').read_text())
    decision = json.loads((LOCAL/'approved_decision.json').read_text())
    assert set(decision) == set(template)
    assert all(decision[k] == v for k, v in template.items() if k != 'approval_source')
    assert isinstance(decision['approval_source'], str) and decision['approval_source'].strip()
    assert 'dispatch_pid=' in (LOCAL/'attempt/verify_extract_dispatch.stdout').read_text()
    dest = LOCAL/'collection'
    dest.mkdir(exist_ok=False)  # never overwrite or resume a previous collection
    status_source = """
import json,pathlib
root=pathlib.Path(ROOT)
output=pathlib.Path(OUTPUT)
value={'receipt':None,'start':None,'worker':None,'driver_pid':None,'driver_tail':None}
for key,rel in [('receipt','receipt.json'),('start','start_receipt.json'),('worker','worker_identity.json')]:
    p=output/rel
    if p.exists():
        assert p.is_file() and not p.is_symlink() and p.stat().st_size<=65536
        value[key]=json.loads(p.read_text())
p=root/'launch.claim/driver.pid'
if p.exists():
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<=128
    value['driver_pid']=p.read_text()
p=root/'logs/driver.log'
if p.exists():
    assert p.is_file() and not p.is_symlink()
    with p.open('rb') as f:
        f.seek(max(0,p.stat().st_size-4096))
        value['driver_tail']=f.read(4096).decode(errors='replace')
print(json.dumps(value))
""".replace('pathlib.Path(ROOT)', 'pathlib.Path('+repr(ROOT)+')').replace('pathlib.Path(OUTPUT)', 'pathlib.Path('+repr(OUTPUT)+')')
    deadline = time.monotonic()+900
    terminal = None
    for index in range(30):
        if index:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(30, remaining))
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            break
        status = json.loads(remote(dest, 'status_'+str(index), min(60,remaining), status_source))
        if status['receipt'] is not None:
            terminal = status['receipt']
            assert terminal['contract_sha256'] == template['contract_sha256']
            assert terminal['host'] == template['host']
            assert terminal['execution'] in ('succeeded', 'stopped_no_retry')
            break
        # A driver already reported failure before science: stop, do not keep polling.
        if status['driver_tail'] and ('Traceback (most recent call last)' in status['driver_tail']):
            raise RuntimeError('Driver admission failed; preserve logs, no retry')
    if terminal is None:
        raise RuntimeError('No terminal receipt within status allowance; unknown, never relaunch')
    # A failed scientific terminal receipt permits evidence retrieval only, not another run.
    manifest_source = """
import hashlib,json,pathlib,stat
root=pathlib.Path(OUTPUT)
assert root.is_dir() and not root.is_symlink()
items={}
total=0
for p in sorted(root.rglob('*')):
    s=p.lstat()
    assert not p.is_symlink()
    if stat.S_ISDIR(s.st_mode): continue
    assert stat.S_ISREG(s.st_mode) and len(items)<256
    total+=s.st_size
    assert total<=134217728
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''): h.update(chunk)
    after=p.stat()
    assert (s.st_size,s.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    items[str(p.relative_to(root))]={'bytes':s.st_size,'sha256':h.hexdigest()}
print(json.dumps(items,indent=2))
""".replace('pathlib.Path(OUTPUT)', 'pathlib.Path('+repr(OUTPUT)+')')
    manifest = json.loads(remote(dest,'artifact_manifest',60,manifest_source))
    (dest/'result').mkdir()
    (dest/'logs').mkdir()
    common = ['/usr/bin/rsync','-a','--partial','--timeout=120','--stats','-e',RSYNC_SSH]
    command(dest,'result_transfer',300,common+['gpu-taobo:'+OUTPUT+'/',str(dest/'result')+'/'])
    command(dest,'log_transfer',120,common+['gpu-taobo:'+ROOT+'/logs/',str(dest/'logs')+'/'])
    actual={str(p.relative_to(dest/'result')) for p in (dest/'result').rglob('*') if p.is_file()}
    assert actual==set(manifest), 'Missing/unexpected local output files; retain partial, no retry'
    for name, row in manifest.items():
        p=dest/'result'/name
        assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    receipt={'run_id':decision['run_id'],'execution':terminal['execution'],
             'retrieval':'verified','files_verified':len(manifest),
             'scientific_verdict':'pending_visual_interpretation' if terminal['execution']=='succeeded' else 'uninterpreted_partial',
             'retry':False,'old_scores_replaced':False}
    with (dest/'retrieval_receipt.json').open('x') as f:
        json.dump(receipt,f,indent=2)
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
