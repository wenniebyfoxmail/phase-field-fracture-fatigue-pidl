import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from prepare_s04_e011_endpoint_baseline import unique_before,build


def test_source_drift_is_rejected_before_generation():
    with pytest.raises(ValueError,match='nonunique'): unique_before('no anchor','marker')
    with pytest.raises(ValueError,match='nonunique'): unique_before('marker marker','marker')


def test_generation_cannot_enter_full_cycle_or_recovery():
    driver="""function result = run_SENS_hard_recovery_native_q4_capture(cfg, options)
work_dir = string(options.work_dir);
repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
init_fatigue_fracture

strain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
RECOVERY_SENTINEL
solve_fatigue_fracture
"""
    solver="""while FULL_CYCLE_SENTINEL
        for i_stag = 1:SOL_STAG_PAR.max_iter
EXACT_ITERATION_SENTINEL
            if stag_converged
COMMIT_SENTINEL
end
"""
    out=build(driver,solver,{'dummy.m':'abc'})
    assert out.count('EXACT_ITERATION_SENTINEL')==1
    for forbidden in ('FULL_CYCLE_SENTINEL','RECOVERY_SENTINEL','COMMIT_SENTINEL','solve_fatigue_fracture'):
        assert forbidden not in out
    assert "Refusing existing output root" in out
    assert "history_commits',0" in out
