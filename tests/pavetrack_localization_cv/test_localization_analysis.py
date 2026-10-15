import importlib.util
from pathlib import Path
import json
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('loc_analysis',ROOT/'scripts/pavetrack_localization_cv/analyze.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
s=importlib.util.spec_from_file_location('loc_test_fixture',Path(__file__).with_name('test_localization.py'));t=importlib.util.module_from_spec(s);s.loader.exec_module(t)


def test_exact_case_roles_tables_and_pixel_free_schematic(tmp_path):
    d=t.fixture();e=t.r.evaluate(d,t.r.labels(d),t.CFG)
    summary,table,cases=a.summarise(e,t.CFG)
    assert summary['net_targets']==4 and len(table)==4
    assert 'lost_old_target' in summary['missing_case_roles']
    assert any(c['kind']=='new_detected_target' for c in cases)
    t.r.write(tmp_path/'evaluation.json',e)
    a.render(tmp_path,e,d,t.CFG)
    for name in ['F00_decision.png','F01_locations.png','F02_schematics.png','README_analysis.md','analysis_receipt.json']:
        assert (tmp_path/'analysis'/name).stat().st_size>0
    receipt=t.r.read(tmp_path/'analysis/analysis_receipt.json')
    assert receipt['pixel_reads']==0
    for name,h in receipt['files'].items():assert t.r.sha(tmp_path/'analysis'/name)==h


def test_feasibility_stop_has_no_fake_learned_figure(tmp_path):
    a.render(tmp_path,None,{},t.CFG)
    assert not list((tmp_path/'analysis').glob('*.png'))
    assert 'No learned prediction' in (tmp_path/'analysis/README_analysis.md').read_text()


def test_real_audit_hook_allows_output_hashes_but_rejects_pixel_inputs(tmp_path):
    import subprocess,sys
    code = """import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir()
s=importlib.util.spec_from_file_location('guarded_analyzer',root/'scripts/pavetrack_localization_cv/analyze.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
s=importlib.util.spec_from_file_location('guarded_fixture',root/'tests/pavetrack_localization_cv/test_localization.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
data=t.fixture();e=t.r.evaluate(data,t.r.labels(data),t.CFG);a.r.write(out/'evaluation.json',e)
sys.addaudithook(a.r.pixel_guard);a.render(out,e,data,t.CFG)
assert (out/'analysis/analysis_receipt.json').exists()
try:
    open(out/'forbidden-source.jpg','rb')
except PermissionError:
    pass
else:
    raise AssertionError('pixel input was not blocked')
"""
    completed=subprocess.run([sys.executable,'-c',code,str(ROOT),str(tmp_path/'synthetic')],capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
