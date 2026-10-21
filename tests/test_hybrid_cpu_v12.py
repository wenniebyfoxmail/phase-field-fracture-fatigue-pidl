"""Given-card and stdlib template controls, never invoke producer/native paths."""
from pathlib import Path
import copy,json
import pytest
import run_hybrid_cpu_v12_budgeted as runner

CARD=Path(__file__).resolve().parents[1]/'docs/research/S04/hybrid_constrained_design_20261019/solver_repair_v12/execution_card.json'


def active(monkeypatch):
    c=json.loads(CARD.read_text());c['execution_enabled']=True
    c['execution_authority']=dict(kind='direct_user_approval',proposal_id='FEM-BOX-KRYLOV-D21-20261021',message_id='TEST_ONLY_NOT_HUMAN_APPROVAL',approved_text='test fixture only')
    monkeypatch.setattr(runner,'time',lambda:c['package_start_epoch']+60)
    return c


def test_disabled_proposal_cannot_launch_or_validate(monkeypatch):
    c=json.loads(CARD.read_text());assert c['execution_enabled']is False and c['execution_authority']is None
    with pytest.raises(RuntimeError,match='identity/authority'):runner.validate(c)


def test_only_two_prospective_approval_metadata_fields_are_excluded_from_template_id(monkeypatch):
    c=active(monkeypatch);runner.validate(c)
    assert runner.template_id(c)==runner.template_id(json.loads(CARD.read_text()))
    bad=copy.deepcopy(c);bad['budget']['producer_retries']=1
    assert runner.template_id(bad)!=runner.template_id(c)
    with pytest.raises(RuntimeError,match='envelope'):runner.validate(bad)


@pytest.mark.parametrize('mutate',[
 lambda c:c['solver'].update(damage_tolerance=1e-6),
 lambda c:c['coupling'].update(box_subproblem_solver='pg2_optional'),
 lambda c:c['coupling'].update(subproblem_action_limit=101),
 lambda c:c['coupling'].update(max_newton_directions=9),
 lambda c:c['phases'][0].update(cycles=1),
 lambda c:c.update(inputs='/other/private'),
 lambda c:c.update(package_start_epoch=c['package_start_epoch']+1),
 lambda c:c.update(execution_authority=None),
])
def test_boundaries_not_changed_by_activation(monkeypatch,mutate):
    c=active(monkeypatch);mutate(c)
    with pytest.raises(RuntimeError):runner.validate(c)


def test_expired_window_parks_and_does_not_reset_start(monkeypatch):
    c=active(monkeypatch);monkeypatch.setattr(runner,'time',lambda:c['absolute_package_deadline_epoch'])
    with pytest.raises(RuntimeError,match='expired'):runner.validate(c)
