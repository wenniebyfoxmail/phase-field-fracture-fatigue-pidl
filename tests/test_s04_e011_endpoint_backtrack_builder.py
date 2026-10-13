import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from prepare_s04_e011_endpoint_backtrack import build
from test_s04_e011_endpoint_tight_builder import fixture


def test_joint_trials_refresh_native_raw_preserve_predecessor_and_restore_cache():
    d,s=fixture();out=build(d,s,{})
    assert out.index('if ~baseline_pass')<out.index('for trial_index=0:6')
    assert 'trial.strain_en_undgr=trial_raw;' in out
    assert out.index('trial.strain_en_undgr=trial_raw;')<out.index('trial_oracle=phase_field.audit.assemble_residual_oracle')
    assert "'First tight direction mismatch'" in out
    assert 'sys.STIFFNESS_MATRIX.KK=current_KK;' in out
    assert "status='NO_ADMISSIBLE_DESCENT_WITHIN_TRIAL_BUDGET'" in out
    assert 'metrics=current_metrics;' in out
    assert 'predecessor.cycle==options.cycle' in out and 'SOL_CYCL_VAR.n_cycle=options.cycle' in out
    assert 'COMMIT_SENTINEL' not in out and 'RECOVERY_SENTINEL' not in out
