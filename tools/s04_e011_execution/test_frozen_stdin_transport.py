"""One offline transport fixture: real metadata only, no SSH/model/arrays."""
from pathlib import Path
import ast,hashlib,json,shlex,subprocess,sys,time

def main():
    began=time.monotonic();root=Path(__file__).resolve().parents[2]
    owner=root/'docs/research/S04/S04-E011/frozen_completion_stdin_r2_20261021'
    card=json.loads((owner/'execution_card.json').read_text());old=json.loads((owner.parent/'frozen_completion_20261021/execution_card.json').read_text())
    assert card['input_bindings']==old['input_bindings'] and card['reuse_bindings']==old['reuse_bindings'] and len(card['reuse_bindings'])==371
    assert card['science']==old['science'] and card['work_caps']==old['work_caps'] and card['resource_limits_bytes']==old['resource_limits_bytes']
    raw=json.dumps(card).encode();code='import json,sys; raw=sys.stdin.buffer.read(); json.loads(raw); sys.stdout.buffer.write(raw)'
    p=subprocess.run([sys.executable,'-B','-c',code],input=raw,capture_output=True,timeout=5,check=True)
    assert p.stdout==raw and json.loads(p.stdout)==card
    tree=ast.parse((root/'tools/s04_e011_execution/frozen_completion_client.py').read_text());strings={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['probe','stage']:strings[n.targets[0].id]=ast.literal_eval(n.value)
    assert set(strings)=={'probe','stage'} and 'json.load(sys.stdin)' in strings['probe']
    vals=dict(ROOT=repr(card['run_root']),ARCHIVE=repr(card['archive_root']),MECHSTART='999999.012345678',DEADLINE=repr(card['envelope_deadline_epoch']),BLOBLEN='1048576',BLOBSHA=repr('a'*64),PKGSHA=repr('b'*64),AUTHSHA=repr('c'*64))
    for k,v in vals.items():strings['stage']=strings['stage'].replace(k,v)
    rows=[]
    for name,script in strings.items():
        ast.parse(script);argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','-o','ControlMaster=no','-o','ControlPath=none','gpu-taobo','/usr/bin/python3 -B -c '+shlex.quote(script)]
        sizes=[len(v.encode())+1 for v in argv];assert max(sizes)<=16384 and sum(sizes)<=65536
        rows.append(dict(command=name,single_max_bytes=max(sizes),total_argv_bytes=sum(sizes)))
    result=dict(status='PASS_one_stdin_roundtrip_fixture',stdin_bytes=len(raw),stdin_sha256=hashlib.sha256(raw).hexdigest(),all_fields_equal=True,reuse_identity_items=371,original_science_unchanged=True,commands=rows,wall_seconds=time.monotonic()-began,new_SSH=0,new_model_array_calls=0)
    (owner/'stdin_fixture.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
