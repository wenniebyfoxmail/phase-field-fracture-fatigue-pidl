"""One control benchmark on tiny child processes; zero scientific state solves."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def test_fixed_pipeline_control_success_then_first_deadline_stop(tmp_path):
    import hybrid_incremental,hybrid_inputs,hybrid_transaction,hybrid_work_trace
    script=Path(__file__).resolve().parents[1]/'tools/run_q4_inverse_validation.py'
    spec=importlib.util.spec_from_file_location('q4_validation_control',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    card=json.loads((script.parents[1]/'docs/research/inverse_fem_A/execution_20261026.json').read_text())
    phases=module.phase_specs(card)
    assert sum(p['kind']=='forward' for p in phases)==25
    assert sum(p['kind']=='direction' for p in phases)==8
    assert sum(p['hours'] for p in phases)+card['budget']['supervision_cleanup_hours']==536
    primary=tmp_path/'primary';archive=tmp_path/'archive';primary.mkdir();archive.mkdir()
    env=dict(os.environ)
    args=dict(cwd=tmp_path,env=env,wall_seconds=4.,step_seconds=.2,rss_bytes=512*1024**2,
              primary=primary,archive=archive,primary_cap=10**7,archive_cap=10**7)
    success=module.supervise([sys.executable,'-c','print("synthetic metadata-only success")'],
        output=primary/'success.log',active=primary/'inactive.json',**args)
    assert success['exit_code']==0 and success['stop_reason'] is None
    active=primary/'active.json'
    module.write_json(active,{'computing':True,'start_monotonic':time.monotonic()-1,'step':1})
    failure=module.supervise([sys.executable,'-c','import time; time.sleep(20)'],
        output=primary/'timeout.log',active=active,**args)
    assert failure['exit_code']!=0 and failure['stop_reason']=='physical/directional substep deadline'
    assert failure['wall_seconds']<4
    # A caller may advance only after success; timeout is not turned into a
    # new Run or skipped phase. No scientific state was generated in this test.
    assert not (primary/'next_phase_started').exists()
