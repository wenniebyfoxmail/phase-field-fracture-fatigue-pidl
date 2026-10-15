import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e010_analysis',ROOT/'scripts/pavetrack_utility_cv/analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
spec=importlib.util.spec_from_file_location('e010_analysis_fixture',ROOT/'tests/pavetrack_localization_cv/test_localization.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
CFG=a.r.read(ROOT/a.r.CONTRACT/'run_config.json')


def test_render_exact_synthetic_summary_and_stop_diagram(tmp_path):
    d=f.fixture();report,e=a.r.preparation(d,CFG)
    a.r.write(tmp_path/'input_audit.json',report)
    # Fixed synthetic oracle is a plotting fixture only; no learned score or fitting.
    a.r.write(tmp_path/'evaluation.json',e)
    a.render(tmp_path,e,d,CFG)
    assert (tmp_path/'analysis/F_preparation.png').stat().st_size>1000
    assert (tmp_path/'analysis/F00_decision.png').stat().st_size>1000
    assert a.r.read(tmp_path/'analysis/summary.json')['net_targets']==4
    assert a.r.read(tmp_path/'analysis/analysis_receipt.json')['pixel_reads']==0
    stop=tmp_path/'stop';stop.mkdir();a.r.write(stop/'input_audit.json',report)
    a.render(stop,None,d,CFG)
    assert (stop/'analysis/F_preparation.png').is_file()
    assert a.r.read(stop/'analysis/analysis_receipt.json')['learned_comparisons']==0
    assert 'no learned result' in (stop/'analysis/README_analysis.md').read_text().lower() or 'neither is a learned result' in (stop/'analysis/README_analysis.md').read_text()
