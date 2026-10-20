#!/usr/bin/env python3
"""Local metadata/syntax checks only. Does not execute any deployment entrypoint."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
ARCHIVE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020')
OLD = ARCHIVE/'deployment_20261020'
ROOT = '/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''): h.update(chunk)
    return h.hexdigest()

def main():
    old=json.loads((OLD/'remote_contract.json').read_text())
    raw=(HERE/'remote_contract.json').read_bytes()
    new=json.loads(raw)
    assert [k for k in old if old[k]!=new[k]]==['archive']
    assert set(old)==set(new) and new['archive']==ROOT+'/inputs'
    assert raw==json.dumps(new,indent=2,allow_nan=False).encode()
    assert sha(HERE/'remote_contract.json')=='f737cfd0673861b6ddf815e43be0cdcea1498bb0f767106006ff7c1d7548f057'
    decision=json.loads((HERE/'decision_template.json').read_text())
    assert decision['approval_source'] is None
    assert decision['contract_sha256']==sha(HERE/'remote_contract.json')
    assert decision['output']==ROOT+'/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002'
    assert decision['run_id']==Path(ROOT).name and decision['wall_seconds']==600
    assert not (ARCHIVE/'recovery_20261020_R002/approved_decision.json').exists()
    assert not (ARCHIVE/'recovery_20261020_R002/attempt').exists()
    assert not (ARCHIVE/'recovery_20261020_R002/collection').exists()
    science={
        REPO/'scripts/md03_controlled_opening.py':new['code_sha256'],
        REPO/'docs/research/S03/S03-E049-MD03/controlled_opening_protocol.md':new['protocol_sha256'],
        REPO/'tests/test_md03_controlled_opening.py':'4f1599473329d278a058dfdd888d30c079e8629245bb744c0edfba50c5d64059',
        OLD/'input_assets.tar.gz':'6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240',
        OLD/'code_snapshot.tar.gz':'f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3',
    }
    for path,digest in science.items():
        assert sha(path)==digest, path
    current=(HERE/'run_cpu.sh').read_text()
    restored=current.replace('MD03-D3-OPENING-20261020-R002','MD03-D3-OPENING-20261020-R001').replace(decision['contract_sha256'],'c11719e0301e13675caaeea8d03a80ff77351a73b43c3083d0998433f9eb2173')
    assert restored==(HERE.parent/'deployment/run_cpu.sh').read_text()
    for name in ('first_admission.sh','run_cpu.sh','stage_and_launch.sh','execute_once.sh'):
        text=(HERE/name).read_text()
        subprocess.run(['bash','-n',str(HERE/name)],check=True)
        for embedded in re.findall(r"<<'PY'\n(.*?)\nPY",text,re.S):
            compile(embedded,name+':inline','exec')
    execute=(HERE/'execute_once.sh').read_text()
    embedded=re.search(r"<<'PY'\n(.*?)\nPY",execute,re.S).group(1)
    tree=ast.parse(embedded)
    expected=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets))
    for name,digest in expected.items():
        assert sha(HERE/name)==digest, name
    assert 'step admission 60' in execute
    assert execute.count('step input_transfer 900')==1
    assert execute.count('step verify_extract_dispatch 180')==1
    assert '--partial --timeout=120' in execute
    assert 'mkdir "$MD03_PAYLOAD/attempt"' in execute
    assert 'ControlMaster=no' in execute and 'ConnectionAttempts=1' in execute
    assert 'cp --no-clobber' in execute
    assert 'pkill ' not in execute and 'rm ' not in execute
    bounded=re.search(r'"[$]MD03_PY" -c \x27\n(.*?)\n\x27 "[$]@"',execute,re.S).group(1)
    compile(bounded,'execute_once:bounded','exec')
    compile((HERE/'collect_once.py').read_text(),'collect_once.py','exec')
    collect_tree=ast.parse((HERE/'collect_once.py').read_text())
    collect_main=next(n for n in collect_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    for n in collect_main.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('status_source','manifest_source') for t in n.targets):
            value=n.value
            while isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute):
                value=value.func.value
            compile(ast.literal_eval(value),'collect_once:remote_inline','exec')
    card=(HERE.parent/'recovery_approval_card.md').read_text()
    for block in re.findall(r'~~~bash\n(.*?)\n~~~',card,re.S):
        subprocess.run(['bash','-n'],input=block,text=True,check=True)
    bound_files=[p for p in HERE.iterdir() if p.name not in ('validate_preparation.py',) and p.is_file()]
    for path in bound_files:
        assert sha(path) in card, 'Card SHA missing/outdated: '+path.name
    for link in re.findall(r'\]\((recovery_20261020/[^)]+)\)',card):
        assert (HERE.parent/link).is_file()
    status=json.loads((ARCHIVE/'readonly_inventory_after_vpn_20261020/inventory_receipt.json').read_text())
    assert status['original_run_state']=='STOPPED_NO_RETRY'
    print(json.dumps(dict(
        preparation_only=True,network_calls=0,real_image_decodes=0,scientific_executions=0,
        metadata_checks=[
            'Only archive root changed; Python-canonical JSON byte identity',
            'R002 decision/path/caps/null authority; no approved file/attempt/collection',
            'Original code/protocol/tests/input/code-archive hashes unchanged',
            'run_cpu launcher differs only in R002 path and contract SHA',
            'Four Bash scripts and all embedded Python compile without execution',
            'All orchestrator control hashes and card file links match',
            'Single transfer/dispatch, no-clobber code copy, partial/timeout/no-retry guards',
        ],
        scientific_tests='25 artificial tests inherited, not repeated',
        independent_review=False,remote_state='not refreshed; no SSH',
        deployment_sha256={p.name:sha(p) for p in bound_files}
    ),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
