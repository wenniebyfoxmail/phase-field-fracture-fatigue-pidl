"""Continue only approved R024 -> qualified R028 -> saved-field comparison.

Finite task orchestration, not a recurring monitor. Never retries a producer.
No PDE assembly or training is entered on this Mac.
"""
from pathlib import Path
import contextlib
import datetime
import importlib.util
import io
import json
import os
import subprocess
import time
import traceback

WORK=Path(__file__).resolve().parents[2]
CASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035')
FLOW=CASE/'pidl_cuda_identity_20261023'
PYTHON='/Users/wenxiaofang/miniconda3/bin/python3'


def record(stage, **extra):
    state=dict(stage=stage,pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**extra)
    (FLOW/'pipeline_state.tmp').write_text(json.dumps(state,indent=2))
    (FLOW/'pipeline_state.tmp').replace(FLOW/'pipeline_state.json')
    print(json.dumps(state),flush=True)


def controller(kind):
    suffix='after_fem' if kind=='pidl' else 'progress'
    path=WORK/'scripts/shear'/f'execute_manav_static_{kind}_{suffix}.py'
    spec=importlib.util.spec_from_file_location(kind+'_controller',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def await_terminal(module,kind):
    # Existing launch must be attributed by status; no launch retry here.
    while True:
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):module.status()
        text=buf.getvalue();print(text,flush=True)
        snapshot=json.loads(text.splitlines()[0])
        if snapshot.get('supervisor_exception.json'):
            raise RuntimeError(kind+' supervisor exception: '+json.dumps(snapshot['supervisor_exception.json']))
        if snapshot.get('exit.json'):
            record(kind+'_terminal',terminal=snapshot['exit.json'],states=snapshot.get('states'))
            return snapshot['exit.json']
        record(kind+'_running',states=snapshot.get('states'),tail=snapshot.get('stdout_tail'))
        time.sleep(45)


def analyze(label, arguments):
    command=['python3',str(FLOW/'analysis_guard.py'),label,PYTHON,*map(str,arguments)]
    p=subprocess.run(command,cwd=WORK,capture_output=True,text=True)
    print(p.stdout,p.stderr,flush=True)
    if p.returncode:raise RuntimeError('Saved-data analysis failed: '+label)


def main():
    with (FLOW/'pipeline_claim.json').open('x') as f:
        json.dump(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='R024 -> verified24 -> R028 -> paired saved-field analysis',unlimited_compute=True),f)
    fem=controller('fem');nn=controller('pidl')
    # Reuse already passed R024 retrieval/reference checks, no repeat solve/validator.
    reference_path=fem.RUN/'analysis/reference_verification.json'
    reference=json.loads(reference_path.read_text())
    retrieval=json.loads((fem.RUN/'retrieval_verification.json').read_text())
    assert reference['complete_valid_reference'] and reference['accepted_prefix']==24
    assert reference['exit']['exit_code']==0 and retrieval['all_remote_hashes_matched']
    record('fem_qualified_reference_reused',reference=reference,source=str(reference_path))
    record('pidl_admission')
    nn.launch()
    terminal=await_terminal(nn,'pidl')
    nn.retrieve()
    record('pidl_retrieved',terminal=terminal)
    out=CASE/'paired_R024_R028'
    analyze('R024_R028_comparison',[WORK/'scripts/shear/analyze_manav_static_pair_converged.py','--fem',fem.RUN/'retrieved/fem','--pidl',nn.RUN/'retrieved/pidl','--out',out])
    figures=out/'figures'
    if figures.is_dir():analyze('R024_R028_figure_sidecars',[WORK/'source/validate_figure_sidecars.py',figures])
    record('paired_analysis_finished',output=str(out),PIDL_terminal=terminal,visual_inspection_pending=True,scientific_verdict='See analyzer saved-state validity and equilibrium metrics; execution completion alone is not physical validation')


if __name__=='__main__':
    try:main()
    except BaseException as e:
        record('control_or_numerical_failure',error=repr(e),traceback=traceback.format_exc(),automatic_retry=False)
        raise
