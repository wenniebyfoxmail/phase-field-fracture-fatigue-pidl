"""Tiny generated arrays only: no native solve, project data, model or training."""
from dataclasses import replace

import numpy as np
import pytest

from synthetic_history_inputs import (
    structured_q4_mesh, unsettled_zero_state, build_branch_schedule,
    make_pair_contract, verify_pair_contract,
)


def mesh():
    return structured_q4_mesh(4, 4, -.25)


def zero_state():
    return unsettled_zero_state(mesh(), mesh_id="mesh", physics_id="physics")


def schedule(name="low", prefix=(.1, .1), probe=(.2,), future=(.3, .3)):
    return build_branch_schedule(trajectory_id=name, prehistory_amplitudes=prefix,
                                 probe_amplitudes=probe, future_amplitudes=future,
                                 fractions=(.5, 1., .5, 0.))


def context(steps, **kwargs):
    values = dict(source_id="generated-v1", root_state=zero_state(),
                  material={"E": 1., "Gc": .01}, boundary_dofs=np.array([0, 1, 9]),
                  boundary_unit_values=np.array([0., 0., 1.]), schedule=steps,
                  origin_step=max(s.step for s in steps if s.segment == "probe"))
    values.update(kwargs)
    return make_pair_contract(**values)


def test_mesh_native_identity_orientation_boundaries_and_notch():
    m = mesh()
    assert m.points.shape == (25, 2) and m.cells.shape == (16, 4)
    assert m.cells.dtype == np.int64 and m.crack.dtype == bool
    np.testing.assert_array_equal(m.cells[0], [0, 1, 6, 5])
    np.testing.assert_array_equal(m.points[m.crack], [[-.5, 0.], [-.25, 0.]])
    np.testing.assert_array_equal(m.points[m.bottom_nodes, 1], -.5)
    np.testing.assert_array_equal(m.points[m.top_nodes, 1], .5)
    np.testing.assert_array_equal(m.points[m.left_nodes, 0], -.5)
    np.testing.assert_array_equal(m.points[m.right_nodes, 0], .5)
    q = m.points[m.cells]
    area = .5 * np.sum(q[:, :, 0] * np.roll(q[:, :, 1], -1, axis=1)
                       - q[:, :, 1] * np.roll(q[:, :, 0], -1, axis=1), axis=1)
    assert np.all(area > 0) and np.sum(area) == 1.
    for a in (m.points, m.cells, m.crack, m.bottom_nodes):
        with pytest.raises(ValueError):
            a.setflags(write=True)


@pytest.mark.parametrize("args", [(4, 3, -.25), (True, 4, -.25),
                                  (4, 4, -.2), (4, 4, -.5), (4, 4, np.nan)])
def test_mesh_refuses_unrepresented_notch_or_centerline(args):
    with pytest.raises(ValueError):
        structured_q4_mesh(*args)


def test_unsettled_payload_is_feasible_and_does_not_claim_native_acceptance():
    m = mesh()
    s = unsettled_zero_state(m, mesh_id="backend-mesh", physics_id="backend-physics")
    np.testing.assert_array_equal(s.damage, m.crack.astype(float))
    assert s.displacement.shape == (50,)
    assert s.accumulated.shape == s.driver.shape == s.fatigue.shape == s.opaque.shape == (16, 4)
    assert not np.any(s.displacement) and not np.any(s.accumulated)
    assert not np.any(s.driver) and not np.any(s.opaque) and np.all(s.fatigue == 1.)
    assert (s.version, s.load_index, s.load_id) == (0, 0, "unsettled-zero")
    assert not hasattr(s, "certificate")


def test_explicit_unnotched_configuration_does_not_invent_damage():
    m = structured_q4_mesh(4, 4, None)
    assert m.crack_tip is None and not np.any(m.crack)
    s = unsettled_zero_state(m, mesh_id="patch", physics_id="physics")
    assert not np.any(s.damage)


def test_variable_amplitudes_have_unambiguous_phase_indices_and_direction():
    steps = schedule(prefix=(.1, .4))
    assert len(steps) == 21
    assert (steps[0].step, steps[0].cycle, steps[0].substep,
            steps[0].phase, steps[0].branch, steps[0].prescribed_load) == (1, 0, 0, "settle", "unloaded", 0.)
    assert [s.prescribed_load for s in steps[1:9]] == [.05, .1, .05, 0., .2, .4, .2, 0.]
    assert [s.branch for s in steps[1:5]] == ["loading", "loading", "unloading", "unloading"]
    assert [s.phase for s in steps[1:5]] == ["intermediate", "peak", "intermediate", "zero"]
    assert (steps[9].segment, steps[9].cycle, steps[9].segment_cycle) == ("probe", 3, 1)
    assert (steps[13].segment, steps[13].cycle, steps[13].segment_cycle) == ("future", 4, 1)
    assert all(s.prescribed_load == 0. for s in steps if s.substep == 4)
    zero = schedule(prefix=(0.,))
    assert all(s.branch == "hold" for s in zero[1:5])


@pytest.mark.parametrize("bad", [(1., .1), (.5, 0.), (1.1, 0.), (1., np.nan, 0.)])
def test_schedule_refuses_invalid_cycle_templates(bad):
    with pytest.raises(ValueError):
        build_branch_schedule(trajectory_id="x", prehistory_amplitudes=(.1,),
                              probe_amplitudes=(.2,), future_amplitudes=(.3,), fractions=bad)


@pytest.mark.parametrize("bad", [(), (-.1,), (np.inf,)])
def test_schedule_refuses_missing_or_invalid_prefix(bad):
    with pytest.raises(ValueError):
        schedule(prefix=bad)


def test_pair_allows_different_legal_prefix_and_absolute_origin_cycle():
    a = context(schedule("a", prefix=(.1,)))
    b = context(schedule("b", prefix=(.1, .3, .2)))
    assert a.prefix_id != b.prefix_id and a.schedule_id != b.schedule_id
    assert a.origin_phase == b.origin_phase
    assert a.future_suffix_id == b.future_suffix_id
    assert verify_pair_contract(a, b)


@pytest.mark.parametrize("field", ["source_id", "root_state_id", "mesh_id", "physics_id",
                                    "material_id", "boundary_id", "common_probe_id",
                                    "future_suffix_id", "settle_id", "schema"])
def test_pair_rejects_changed_context(field):
    a = context(schedule("a"))
    b = context(schedule("b", prefix=(.2, .2)))
    with pytest.raises(ValueError, match=field):
        verify_pair_contract(a, replace(b, **{field: "different"}))


def test_pair_rejects_future_probe_origin_and_boundary_changes():
    a = context(schedule("a"))
    with pytest.raises(ValueError, match="future_suffix"):
        verify_pair_contract(a, context(schedule("b", future=(.3, .4))))
    with pytest.raises(ValueError, match="common_probe"):
        verify_pair_contract(a, context(schedule("b", probe=(.25,))))
    with pytest.raises(ValueError, match="origin_phase"):
        verify_pair_contract(a, replace(context(schedule("b")), origin_phase=("changed",)))
    with pytest.raises(ValueError, match="boundary"):
        verify_pair_contract(a, context(schedule("b"), boundary_dofs=np.array([1, 0, 9]),
                                        boundary_unit_values=np.array([0., 0., 1.])))
    with pytest.raises(ValueError, match="final common-probe"):
        context(schedule("a"), origin_step=10)


def test_manual_schedule_corruption_is_rejected_before_binding():
    steps = list(schedule())
    steps[1] = replace(steps[1], prescribed_load=.9)
    with pytest.raises(ValueError, match="reproduce"):
        context(steps)
    with pytest.raises(ValueError, match="boundary"):
        context(schedule(), boundary_dofs=np.array([0, 0, 9]))
    with pytest.raises(ValueError, match="distinct"):
        verify_pair_contract(context(schedule()), context(schedule()))


def test_pair_metadata_does_not_modify_root_or_import_solver():
    before = zero_state()
    fingerprint = before.fingerprint()
    context(schedule(), root_state=before)
    assert before.fingerprint() == fingerprint
    # Source inspection keeps this module/test scope free of accidental producer calls.
    import inspect
    import synthetic_history_inputs as module
    assert "from hybrid_incremental import" not in inspect.getsource(module)
