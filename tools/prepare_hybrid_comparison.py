"""Build a local, disabled comparison packet from reviewed existing files.

No arrays are loaded, no scientific solver/model imported, no SSH/install/fit.
The consumed R2 packet/cards remain immutable historical records. A new
packet has null run identity and does not restore a fit, budget or attempt.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

OWNER = 'docs/research/S04/hybrid_constrained_design_20261019'


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
    prior=json.loads((code/OWNER/'accepted_state_source_manifest_v5.json').read_text())
    for rel,expected in prior['files'].items():
        if digest(code/rel)!=expected:raise RuntimeError('reused file changed: '+rel)
    base=json.loads((code/OWNER/'accepted_state_preparation_card_v5.json').read_text())
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
    files=sorted(prior['files'])
    # The manifest needs its own tracked identity so retained prior hashes remain
    # traceable; it is not the new packet's self-referential source manifest.
    files.append(OWNER+'/accepted_state_source_manifest_v5.json')
    subprocess.run(['git','-C',str(code),'diff','--quiet','HEAD','--',*files],check=True)
    head=subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip()
    out.mkdir(parents=True,exist_ok=False)
    stage=out/'code';stage.mkdir()
    for rel in files:
        target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(code/rel,target)
    packet=dict(source_commit=head,base_owner_commit=base['owner_base_commit'],
                files={rel:digest(stage/rel) for rel in sorted(files)})
    packet['artifact_id']=object_digest(packet['files'])
    dump(out/'source_manifest.json',packet)
    card=copy.deepcopy(base['execution_template'])
    card.update(run_id=None,run_root=None,archive_root=None,
                execution_enabled=False,
                preparation_status='DISABLED_R2_COST_AND_TERMINAL_RECONCILIATION_AND_FUTURE_AUTHORITY_REQUIRED')
    assert card['solver']==base['execution_template']['solver']
    assert card['phases']==base['execution_template']['phases']
    dump(out/'complete_comparison_disabled.json',card)
    dump(out/'inputs_inventory.json',dict(source=str(inputs),
         inputs_sha256=digest(inputs/'inputs.json'), assets=inventory,
         scientific_arrays_loaded=False, total_asset_bytes=sum(r['bytes'] for r in inventory),
         state0_id=manifest['state0_id'],physics_id=manifest['physics_id'],mesh_id=manifest['mesh_id']))
    with tarfile.open(out/'reviewed_code.tar.gz','w:gz') as tar:
        for rel in sorted(files):tar.add(stage/rel,arcname='code/'+rel,recursive=False)
        tar.add(out/'source_manifest.json',arcname='source_manifest.json')
        tar.add(out/'complete_comparison_disabled.json',arcname='complete_comparison_disabled.json')
    dump(out/'build_receipt.json',dict(source_commit=head,artifact_id=packet['artifact_id'],
         source_file_count=len(files),source_bytes=sum((stage/p).stat().st_size for p in files),
         code_tar_bytes=(out/'reviewed_code.tar.gz').stat().st_size,
         code_tar_sha256=digest(out/'reviewed_code.tar.gz'),
         card_sha256=digest(out/'complete_comparison_disabled.json'),
         production_execution_enabled=False,runtime_inventory_executed=False,
         new_fem_solves=0,training_updates=0,ssh_calls=0,
         inputs_reused_without_array_load=True,
         remaining_host_hours_now=None,
         reason='Consumed R2 total costs/fit/step use not reconciled; never reset original study budget'))
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    out=build(Path(__file__).resolve().parents[1],args.inputs_root,args.out)
    print((out/'build_receipt.json').read_text())


if __name__=='__main__':main()
