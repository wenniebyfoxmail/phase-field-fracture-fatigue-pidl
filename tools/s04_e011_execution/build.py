"""Create one CLOSED local package from a clean committed source tree.

Copies source/compact old evidence only; no arrays/models, SSH or host probe.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
from control import FAMILY,PHASES,SECONDS,digest,verify_package,write_json

SCIENCE='docs/research/S04/S04-E011/pidl_profiled_hidden_adapter_card_20261020.json'
EXEC='docs/research/S04/S04-E011/profiled_hidden_execution_20261020/execution_card.json'
COMPACT='docs/research/S04/S04-E011/runs/pidl_tight_coupling_result_20261019/'


def build(repo,out,execution_card=None):
    repo=Path(repo);out=Path(out)
    if out.exists():raise FileExistsError('fresh local package only; never overwrite')
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('exact clean committed tree required')
    requested=Path(execution_card or EXEC)
    if requested.is_absolute() or '..' in requested.parts:raise RuntimeError('execution card must be tracked repository-relative source')
    git('ls-files','--error-unmatch',str(requested))
    commit=git('rev-parse','HEAD');files=git('ls-tree','-r','--name-only',commit,'source','SENS_tensile','tools').splitlines()
    files=[f for f in files if f.endswith('.py')]
    files +=[SCIENCE,COMPACT+'result.json',COMPACT+'metrics.csv',
        'docs/research/S04/S04-E011/runs/pidl_hidden_direction_result_20261020/directions.csv']
    out.mkdir();code=out/'code';code.mkdir()
    for name in files:
        p=repo/name
        if p.is_symlink():raise RuntimeError('source symlink not allowed')
        target=code/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
    (out/'execution_card.json').write_bytes((repo/requested).read_bytes())
    entries=[]
    for p in sorted(out.rglob('*')):
        if p.is_file():entries.append(dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=digest(p)))
    manifest=dict(family=FAMILY,source_commit=commit,source_branch=git('branch','--show-current'),source_dirty=False,
        files=entries,science_source_base='ae01bfed',execution_enabled=False,scientific_run_performed=False)
    write_json(out/'package_manifest.json',manifest);verify_package(out,manifest)
    card=json.loads((out/'execution_card.json').read_text())
    closed=dict(approved_by=None,activate_closed_package=False,approval_ref=None,family=FAMILY,run_id=card['run_id'],
        package_sha256=digest(out/'package_manifest.json'),scope=None)
    if card.get('admission_revision'):closed.update(amends_first_stop_package_sha256=None,amends_first_stop_receipt_sha256=None)
    write_json(out/'authority.closed.json',closed)
    write_json(out/'build_receipt.json',dict(package_sha256=digest(out/'package_manifest.json'),authority_closed_sha256=digest(out/'authority.closed.json'),
        source_commit=commit,files=len(entries),bytes=sum(r['bytes'] for r in entries),execution_enabled=False))
    return json.loads((out/'build_receipt.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--execution-card',type=Path)
    a=p.parse_args();print(json.dumps(build(a.repo,a.out,a.execution_card),indent=2))
