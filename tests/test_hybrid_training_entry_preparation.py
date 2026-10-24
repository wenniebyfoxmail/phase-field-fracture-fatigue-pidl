"""Single fixed metadata benchmark. No new scientific arrays/solve/fit."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from run_hybrid_producer import validate_card, require_enabled_execution, initial_totals

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/research/S04/hybrid_constrained_design_20261019'


def test_reconciled_training_entry():
    prep=json.loads((D/'training_entry_preparation_card_v6.json').read_text())
    c=prep['execution_template'];old=json.loads((D/'accepted_state_preparation_card_v5.json').read_text())['execution_template']
    validate_card(old);validate_card(c)
    assert c['solver']['wall_seconds']==600 and old['solver']['wall_seconds']==120
    assert {k:v for k,v in c['solver'].items() if k!='wall_seconds'}=={k:v for k,v in old['solver'].items() if k!='wall_seconds'}
    for key in ['training','criteria','phases','coupling','base_load_cycle','state0_id','inputs_sha256']:
        assert c[key]==old[key]
    assert c['run_id'] is None and c['execution_enabled'] is False
    with pytest.raises(RuntimeError,match='preparation'):require_enabled_execution(c)
    bad=deepcopy(c);bad['execution_enabled']=True
    with pytest.raises(RuntimeError,match='not authorized'):require_enabled_execution(bad)
    bad=deepcopy(c);del bad['computational_step_cap_revision']
    with pytest.raises(ValueError,match='explicit R2'):validate_card(bad)
    totals=initial_totals(c,1000.,ROOT)
    receipt=json.loads((D/'r2_reconciliation_20261024.json').read_text())
    assert abs(totals['wall_seconds']-receipt['accounting']['charged_study_wall_seconds'])<1e-8
    assert totals['gpu_seconds']==0 and receipt['remaining_gpu_hours']==12
    assert receipt['remaining_training_fits']==1 and receipt['remaining_numerical_steps']==0
    assert receipt['training_gate']['ready_to_fit_now'] is False
    lineages=[x for e in c['prior_costs'] for x in e['lineage']]
    assert len(lineages)==len(set(lineages))
    assert lineages.count('pf_hybrid_complete_20261020_r2')==1
