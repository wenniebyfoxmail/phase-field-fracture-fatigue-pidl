"""Build a local, disabled comparison packet from reviewed existing files.

No arrays are loaded, no scientific solver/model imported, no SSH/install/fit.
Distribution metadata inventory remains a separate action needing approval.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from request_hybrid_runtime_inventory import request_for

OWNER = 'docs/research/S04/hybrid_constrained_design_20261019'
DOCS = OWNER+'/comparison_preparation_20261020'
RUN_ID = 'pf_hybrid_complete_20261020_r2'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def build(code,inputs,out):
    code,inputs,out=Path(code).resolve(),Path(inputs).resolve(),Path(out).resolve()
    prior=json.loads((code/OWNER/'coupled_repair_source_manifest_v4.json').read_text())
    for rel,expected in prior['files'].items():
        if digest(code/rel)!=expected:raise RuntimeError('reused file changed: '+rel)
    base=json.loads((code/OWNER/'coupled_repair_card_v4.json').read_text())
    manifest=json.loads((inputs/'inputs.json').read_text())
    if digest(inputs/'inputs.json')!=base['execution_template']['inputs_sha256']:
        raise RuntimeError('retained input manifest differs')
    inventory=[]
    for rel,expected in manifest['assets'].items():
        path=Path(rel)
        if path.is_absolute() or '..' in path.parts:raise ValueError('nonlocal input asset')
        source=inputs/path
        if digest(source)!=expected:raise RuntimeError('retained input asset differs: '+rel)
        inventory.append(dict(path=rel,sha256=expected,bytes=source.stat().st_size))
    new_files=['tools/hybrid_runtime_inventory.py','tools/request_hybrid_runtime_inventory.py',
               'tools/prepare_hybrid_comparison.py','tests/test_hybrid_comparison_preparation.py',
               DOCS+'/README.md',DOCS+'/loading_property_extension.md']
    files=sorted(set(prior['files'])|set(new_files))
    # The manifest needs its own tracked identity so retained prior hashes remain
    # traceable; it is not the new packet's self-referential source manifest.
    files.append(OWNER+'/coupled_repair_source_manifest_v4.json')
    subprocess.run(['git','-C',str(code),'diff','--quiet','HEAD','--',*files],check=True)
    head=subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip()
    out.mkdir(parents=True,exist_ok=False)
    stage=out/'code';stage.mkdir()
    for rel in files:
        target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(code/rel,target)
    packet=dict(source_commit=head,base_owner_commit='829508617534c6c5febc813899498a31053684df',
                files={rel:digest(stage/rel) for rel in sorted(files)})
    packet['artifact_id']=object_digest(packet['files'])
    dump(out/'source_manifest.json',packet)
    card=copy.deepcopy(base['execution_template'])
    card.update(run_id=RUN_ID,run_root='/mnt/data2/drtao/wennie/'+RUN_ID,
                archive_root='/mnt/data2/drtao/pidl_archives/'+RUN_ID,
                execution_enabled=False,
                preparation_status='BLOCKED_ONLY_FOR_RUNTIME_INVENTORY_PIN_EXACT_REVIEW_AND_HUMAN_EXECUTION_APPROVAL')
    assert card['runtime_expected']['matplotlib'] is None
    assert card['solver']==base['execution_template']['solver']
    assert card['phases']==base['execution_template']['phases']
    dump(out/'complete_comparison_pending_runtime.json',card)
    req=request_for(stage/'tools/hybrid_runtime_inventory.py',
                    '/mnt/data2/drtao/wennie/pf_hybrid_full_20261019_r1/deps')
    dump(out/'runtime_inventory_request.json',req)
    dump(out/'inputs_inventory.json',dict(source=str(inputs),
         inputs_sha256=digest(inputs/'inputs.json'), assets=inventory,
         scientific_arrays_loaded=False, total_asset_bytes=sum(r['bytes'] for r in inventory),
         state0_id=manifest['state0_id'],physics_id=manifest['physics_id'],mesh_id=manifest['mesh_id']))
    with tarfile.open(out/'reviewed_code.tar.gz','w:gz') as tar:
        for rel in sorted(files):tar.add(stage/rel,arcname='code/'+rel,recursive=False)
        tar.add(out/'source_manifest.json',arcname='source_manifest.json')
        tar.add(out/'complete_comparison_pending_runtime.json',arcname='complete_comparison_pending_runtime.json')
        tar.add(out/'runtime_inventory_request.json',arcname='runtime_inventory_request.json')
    dump(out/'build_receipt.json',dict(source_commit=head,artifact_id=packet['artifact_id'],
         source_file_count=len(files),source_bytes=sum((stage/p).stat().st_size for p in files),
         code_tar_bytes=(out/'reviewed_code.tar.gz').stat().st_size,
         code_tar_sha256=digest(out/'reviewed_code.tar.gz'),
         card_sha256=digest(out/'complete_comparison_pending_runtime.json'),
         inventory_request_sha256=digest(out/'runtime_inventory_request.json'),
         production_execution_enabled=False,runtime_inventory_executed=False,
         new_fem_solves=0,training_updates=0,ssh_calls=0,
         inputs_reused_without_array_load=True,
         remaining_host_hours_before_inventory=base['execution_template']['budget']['remaining_host_hours_after_all_known_prior_runs']))
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    out=build(Path(__file__).resolve().parents[1],args.inputs_root,args.out)
    print((out/'build_receipt.json').read_text())


if __name__=='__main__':main()
