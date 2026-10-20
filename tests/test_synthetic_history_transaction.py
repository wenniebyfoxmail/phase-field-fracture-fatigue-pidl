"""Artificial proposals exercise the real state contract/store, never FEM."""
from dataclasses import asdict, replace
import json

import numpy as np
import pytest

import synthetic_history_experiment as experiment
from hybrid_incremental import StepFailure, StepProposal, digest_config
from hybrid_state_contract import verify_expected
from hybrid_transaction import StateStore


@pytest.fixture
def artificial_trajectory(tmp_path, monkeypatch):
    backends = []

    class StubBackend:
        def __init__(self, kin, crack, **material):
            from native_q4_damage_qp import gauss_interpolation_matrix
            self.gp = gauss_interpolation_matrix(kin)
            self.mesh_id = "artificial-mesh"
            self.physics_id = "artificial-physics"
            backends.append(self)

    def proposal(old, dofs, values, next_load_id, settings, coupling,
                 perturb=False):
        # Deterministic algebraic payload, not mechanical equilibrium.
        u = np.zeros_like(old.displacement)
        u[dofs] = values
        if perturb:
            u[2] = .001  # A free DOF, reset on the next artificial step.
        state = replace(old, displacement=u, version=old.version + 1,
                        load_index=old.load_index + 1, load_id=next_load_id)
        certificate = dict(
            passed=True, previous_id=old.fingerprint(), state_id=state.fingerprint(),
            settings_id=digest_config(asdict(settings)),
            coupling_policy_id=digest_config(asdict(coupling)),
            mechanics=dict(reaction_dofs=dofs.tolist(), force_inf=0., force_l2=0.,
                           force_scaled=0., boundary_inf=0.),
            damage=dict(primal_inf=0., kkt_scaled_inf=0., kkt_l2=0., projected_inf=0.),
            fatigue_residual=0.)
        return StepProposal(old.fingerprint(), state, certificate, (),
                            field_evidence={
                                "f_solve_gp": state.fatigue,
                                "psi_raw_commit_gp": np.zeros_like(state.fatigue)})

    def stub_step(backend, old, dofs, values, *, next_load_id, settings,
                  coupling, **unused):
        return proposal(old, dofs, values, next_load_id, settings, coupling)

    monkeypatch.setattr(experiment, "NativeQ4Backend", StubBackend)
    monkeypatch.setattr(experiment, "solve_step", stub_step)
    spec = experiment.frozen_spec()
    spec["histories"] = {"low": [.005], "high": [.010]}
    spec["future"] = [.030]
    markers = []
    trajectory = experiment.Trajectory(
        spec, dict(id="artificial", cells=2, subdivisions=1), "low", tmp_path,
        "artificial-contract-test", lambda *args: markers.append(args))
    return trajectory, proposal, backends, markers


def test_custom_context_commits_and_exact_restart_uses_fresh_backend(artificial_trajectory):
    trajectory, _, backends, _ = artificial_trajectory
    assert len(trajectory.schedule) == 16 and trajectory.origin == 11
    trajectory.advance(len(trajectory.schedule))
    original = trajectory.old.fingerprint()
    origin, metadata = StateStore(trajectory.state_path(trajectory.origin)).load()
    verify_expected(origin, metadata, trajectory.context(origin, trajectory.origin))
    assert metadata["state_contract"]["context"]["physical"]["segment"] == "probe"
    assert metadata["state_contract"]["context"]["physical"]["phase"] == "zero"
    trajectory.replay()
    assert len(backends) == 2 and backends[0] is not backends[1]
    assert trajectory.old.fingerprint() == original


def test_restart_rejects_first_different_substep_even_if_later_would_reset(
        artificial_trajectory, monkeypatch):
    trajectory, proposal, _, markers = artificial_trajectory
    trajectory.advance(len(trajectory.schedule))
    markers.clear()

    def changed_step(backend, old, dofs, values, *, next_load_id, settings,
                     coupling, **unused):
        return proposal(old, dofs, values, next_load_id, settings, coupling,
                        perturb=old.load_index == trajectory.origin)

    monkeypatch.setattr(experiment, "solve_step", changed_step)
    with pytest.raises(RuntimeError, match="full-state restart"):
        trajectory.replay()
    # A final-only check would miss this transient artificial difference.
    assert [step for _, step in markers if step is not None] == [12]
    assert trajectory.old.load_index == 12


def test_failed_artificial_proposal_preserves_durable_old_state_and_work(
        artificial_trajectory, monkeypatch):
    trajectory, _, _, _ = artificial_trajectory
    original = trajectory.old.fingerprint()
    work = ({"kind": "artificial-fault", "status": "failed"},)

    def failed_step(*args, **kwargs):
        raise StepFailure("deliberate artificial failure", work)

    monkeypatch.setattr(experiment, "solve_step", failed_step)
    with pytest.raises(StepFailure, match="deliberate artificial failure"):
        trajectory.advance(1)
    assert trajectory.old.fingerprint() == original
    assert trajectory.store.load()[0].fingerprint() == original
    failure = json.loads((trajectory.path / "failure.json").read_text())
    assert failure["step"] == 1 and failure["accepted_state_id"] == original
    assert failure["work"] == list(work)


def test_recovery_accepts_durable_terminal_without_snapshot_or_event(artificial_trajectory, tmp_path):
    from synthetic_history_recovery import validate_prefix
    trajectory, _, _, markers = artificial_trajectory
    trajectory.advance(3)
    source = trajectory.path
    final_id = trajectory.old.fingerprint()
    trajectory.state_path(3).unlink()
    ledger = source/'steps.jsonl'
    ledger.write_text('\n'.join(ledger.read_text().splitlines()[:-1])+'\n')
    restored_root = tmp_path/'recovery'
    restored_root.mkdir()
    fresh = experiment.Trajectory(trajectory.spec, trajectory.variant, 'low', restored_root,
                                  'artificial-contract-test', lambda *args: pytest.fail('no solve'))
    markers.clear()
    states, rows = validate_prefix(fresh, source, 3)
    assert len(states) == 4 and len(rows) == 2
    assert states[-1][0].fingerprint() == final_id
    assert states[-1][2] == source/'latest.npz'
    assert not markers
    assert not (source/'states/state0003.npz').exists()  # source remains untouched


def test_recovery_rejects_missing_interior_snapshot(artificial_trajectory, tmp_path):
    from synthetic_history_recovery import validate_prefix
    trajectory, _, _, _ = artificial_trajectory
    trajectory.advance(3)
    trajectory.state_path(2).unlink()
    root = tmp_path/'recovery'; root.mkdir()
    fresh = experiment.Trajectory(trajectory.spec, trajectory.variant, 'low', root,
                                  'artificial-contract-test', lambda *args: pytest.fail('no solve'))
    with pytest.raises(RuntimeError, match='gaps'):
        validate_prefix(fresh, trajectory.path, 3)


def test_recovery_rejects_changed_schedule(artificial_trajectory, tmp_path):
    from synthetic_history_recovery import validate_prefix
    trajectory, _, _, _ = artificial_trajectory
    trajectory.advance(1)
    path=trajectory.path/'schedule.json'
    rows=json.loads(path.read_text());rows[1]['prescribed_load']+=.001
    path.write_text(json.dumps(rows))
    root=tmp_path/'recovery';root.mkdir()
    fresh=experiment.Trajectory(trajectory.spec,trajectory.variant,'low',root,
                               'artificial-contract-test',lambda *args: pytest.fail('no solve'))
    with pytest.raises(RuntimeError, match='schedule'):
        validate_prefix(fresh,trajectory.path,1)
