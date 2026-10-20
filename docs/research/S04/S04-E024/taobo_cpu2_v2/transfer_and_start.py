#!/usr/bin/env python3
"""One-shot approved D013 v2 transport and conditional producer dispatch.
Default/false authority performs no SSH/SCP and never imports real Torch.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import shlex
import select

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('d013_remote',HERE/'remote_entry.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
ACCOUNT='drtao@172.16.100.2'
SSH=['ssh','-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=15',ACCOUNT]
SCP=['scp','-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=15']
HISTORICAL_COST=71.93754945798841


def validate_local_auth(a,m,digest):
    r.validate_auth(a)
    if a['action_manifest_sha256']!=digest:raise r.PackageError('wrong action manifest')
    for key in ('package_id','payload_sha256','payload_manifest_sha256','remote_entry_sha256','remote_root','fixed_local_archive_bytes','base_nontraining_charge_seconds'):
        if a.get(key)!=m.get(key):raise r.PackageError('authorization/manifest mismatch '+key)
    if m['account']!=ACCOUNT or m['science_commit']!=r.SCIENCE or m['science_tree_sha256']!=r.TREE:
        raise r.PackageError('account/science manifest mismatch')
    if m['base_nontraining_charge_seconds']<HISTORICAL_COST:raise r.PackageError('historical budget reset')


def invoke(command,stdin,timeout,log):
    """Bound only this owned SSH/SCP client. Unknown remote outcome never retries."""
    start=time.monotonic()
    result=subprocess.run(command,input=stdin,text=True,capture_output=True,timeout=timeout)
    r.write(log,dict(command=command,wall_seconds=time.monotonic()-start,returncode=result.returncode,
        stdout=result.stdout,stderr=result.stderr))
    if result.returncode:raise r.PackageError('transport/bootstrap failed; no retry')
    return result


def upload_capacity(fixed_local_bytes,payload_bytes,peak_remote_bytes):
    if any(type(x) is not int or x<0 for x in (fixed_local_bytes,payload_bytes,peak_remote_bytes)):
        raise r.PackageError('invalid combined archive accounting')
    if fixed_local_bytes+payload_bytes>1024**3 or fixed_local_bytes+peak_remote_bytes>1024**3:
        raise r.PackageError('pre-upload combined1GiB peak admission')


def anchor_authority(auth,answer,elapsed):
    if answer.get('status')!='ANCHOR_ONLY_NO_METADATA' or answer.get('root')!=str(r.ROOT) or answer.get('action_manifest_sha256')!=auth['action_manifest_sha256']:
        raise r.PackageError('unclear create/anchor result')
    stamp=r.finite_number(answer.get('anchor_monotonic_seconds'),'producer ACK anchor')
    r.finite_number(elapsed,'client ACK elapsed')
    identity=dict(anchor_monotonic_seconds=stamp,authority=auth['action_manifest_sha256'])
    result=dict(auth,producer_anchor_monotonic_seconds=stamp,anchor_ack_client_elapsed_seconds=elapsed)
    r.anchored_deadlines(result,identity)
    return result


def invoke_create(command,auth,start,remaining,log):
    """One SSH, two stdin messages. No metadata/root claim before deadline ACK."""
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    first=json.dumps(auth).encode()+b'\n';received=b'';begin=time.monotonic()
    try:
        child.stdin.write(first);child.stdin.flush()
        while b'\n' not in received:
            ready,_,_=select.select([child.stdout],[],[],remaining())
            if not ready:raise r.PackageError('anchor ACK timeout; no retry')
            data=os.read(child.stdout.fileno(),4096)
            if not data:raise r.PackageError('SSH closed before anchor ACK')
            received+=data
            if len(received)>200000:raise r.PackageError('oversized anchor ACK')
        line,tail=received.split(b'\n',1)
        anchored=anchor_authority(auth,r.read_json_text(line.decode()),time.monotonic()-start)
        rest,err=child.communicate(input=json.dumps(anchored).encode()+b'\n',timeout=remaining())
        output=(tail+rest).decode()
        r.write(log,dict(command=command,wall_seconds=time.monotonic()-begin,returncode=child.returncode,
            anchor_ACK=line.decode(),stdout=output,stderr=err.decode()))
        if child.returncode:raise r.PackageError('metadata admission failed; no retry')
        result=r.read_json_text(output)
        if result.get('status')!='FRESH_ROOT_CLAIMED_NOT_SCIENCE' or result.get('anchor_monotonic_seconds')!=anchored['producer_anchor_monotonic_seconds']:
            raise r.PackageError('unclear metadata/root-claim result')
        return anchored
    except BaseException:
        # Local SSH only. This is NOT a remote cancellation or stopped receipt.
        if child.poll() is None:child.kill()
        child.communicate(timeout=2)
        raise


def main():
    start=time.monotonic();p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authorization',type=Path)
    a=p.parse_args()
    if a.authorization is None:p.error('closed authority: final approved v2 action required')
    auth=r.read(a.authorization)
    if auth.get('user_approved_final_execution') is not True:raise r.PackageError('explicit v2 approval required')
    m=r.read(HERE/'action_manifest.json');digest=r.sha(HERE/'action_manifest.json')
    validate_local_auth(auth,m,digest)
    if HERE!=Path(m['control_bundle_dir']):raise r.PackageError('approved local control directory changed')
    used=m['base_nontraining_charge_seconds'];deadline=start+300-used
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise r.PackageError('transport/preflight300s budget exhausted')
        return value
    def check():remaining()
    if sum(r.files_under(Path(q)) for q in m['local_archive_roots'])>m['fixed_local_archive_bytes']:
        raise r.PackageError('local prepared archive exceeds frozen charge')
    for name,identity in m['control_files'].items():
        q=HERE/name
        if q.is_symlink() or q.stat().st_size!=identity['bytes'] or r.sha(q,check)!=identity['sha256']:
            raise r.PackageError('control payload changed: '+name)
    upload_capacity(m['fixed_local_archive_bytes'],m['payload_bytes'],m['predicted_remote_peak_bytes'])
    wire=Path(m['payload_path'])
    if wire.is_symlink() or wire.stat().st_size!=m['payload_bytes'] or r.sha(wire,check)!=m['payload_sha256']:
        raise r.PackageError('wire payload changed')
    # Claim on Mac only AFTER exact human approval; survives every failure.
    claim=HERE.parent/'ACTION_ONCE'
    claim.mkdir()
    r.write(claim/'authorization_snapshot.json',auth)
    program=(HERE/'remote_entry.py').read_text();phase='bootstrap_create'
    def ssh_command(mode):
        return SSH+[PYTHON_REMOTE+' -c '+shlex.quote(program)+' '+mode]
    try:
        first=dict(auth,transport_charge_seconds=time.monotonic()-start)
        anchored=invoke_create(ssh_command('--bootstrap-create'),first,start,remaining,claim/'01_create.json')
        phase='upload'
        invoke(SCP+[str(wire),ACCOUNT+':'+str(r.ROOT/'payload.tar')],None,remaining(),claim/'02_scp.json')
        phase='conditional_dispatch'
        # SAME producer monotonic deadline from the first ACK; no restarted
        # remote5s timer and no claim that an SSH timeout cancels remote work.
        final=dict(anchored,transport_charge_seconds=time.monotonic()-start)
        dispatched=invoke(ssh_command('--bootstrap-start'),json.dumps(final),remaining(),claim/'03_dispatch.json')
        answer=r.read_json_text(dispatched.stdout)
        if answer['status']!='DISPATCHED_NOT_COMPLETED':raise r.PackageError('ambiguous dispatch; inspect, never resend')
        r.write(claim/'dispatched.json',dict(**answer,phase=phase,action_manifest_sha256=digest,
            transport_actual_wall_seconds=time.monotonic()-start,no_retry=True))
        print(json.dumps(answer))
    except BaseException as e:
        r.write(claim/'failure.json',dict(phase=phase,error=type(e).__name__+': '+str(e),
            elapsed_seconds=time.monotonic()-start,remote_state='UNKNOWN_OR_PARTIAL; read receipts before action',no_retry=True))
        raise

PYTHON_REMOTE='/usr/bin/python3'
if __name__=='__main__':main()
