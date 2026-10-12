import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from prepare_s04_e011_endpoint_tight import build


def fixture():
    driver="""function result = run_SENS_hard_recovery_native_q4_capture(cfg, options)
work_dir = string(options.work_dir);
repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
init_fatigue_fracture

strain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
RECOVERY_SENTINEL
"""
    solver="""        for i_stag = 1:SOL_STAG_PAR.max_iter
EXACT_SOURCE_ITERATION
            if stag_converged
COMMIT_SENTINEL
"""
    return driver,solver


def test_tightening_is_after_mandatory_baseline_gate_and_bounded():
    d,s=fixture();out=build(d,s,{})
    assert out.index('if ~baseline_pass')<out.index('SOL_PAR.tol_displ=1e-8;')
    assert out.count('EXACT_SOURCE_ITERATION')==2
    assert 'max_extra=10;' in out and 'baseline_iteration+max_extra' in out
    assert 'COMMIT_SENTINEL' not in out and 'RECOVERY_SENTINEL' not in out
    assert "'FAIL_INNER_OR_CONTRACT'" in out and 'last_completed' in out
    assert 'g(at_lower & at_upper)=0;' in out


def test_source_drift_fails_before_output():
    d,s=fixture()
    with pytest.raises(ValueError):build(d,s+s,{})
