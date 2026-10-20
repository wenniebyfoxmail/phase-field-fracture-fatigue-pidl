"""Pure input construction for a proposed matched-history synthetic experiment.

No solver, run entry point or scientific acceptance is implemented here.  The
zero-load payload only satisfies algebraic bounds: each schedule begins with
an explicit zero-settle step. The runner must verify acceptance and consistency
of those settled states before prehistory. These pair identities supplement,
never relax, hybrid_state_contract.
"""
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

import numpy as np

from hybrid_history import AcceptedState


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def _immutable(value, dtype):
    array = np.ascontiguousarray(value, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


def _identity(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty identity")
    return value


@dataclass(frozen=True)
class StructuredQ4Mesh:
    """Uniform square mesh, CCW zero-based Q4 cells and explicit notch nodes."""
    points: np.ndarray
    cells: np.ndarray
    crack_nodes: np.ndarray
    bottom_nodes: np.ndarray
    top_nodes: np.ndarray
    left_nodes: np.ndarray
    right_nodes: np.ndarray
    nx: int
    ny: int
    crack_tip: float | None

    @property
    def crack(self):
        """Boolean precrack identity mask, as required by NativeQ4Backend."""
        return self.crack_nodes


def structured_q4_mesh(nx, ny, crack_tip):
    """Generate [-.5,.5]^2; refuse off-grid tips instead of silently snapping.

    ``nx`` and ``ny`` count cells.  Even ``ny`` puts nodes exactly on y=0.
    The precrack consists of y=0 nodes from the left edge through crack_tip.
    Explicit ``crack_tip=None`` gives a separate unnotched input configuration.
    No mesh-size/length-scale or fatigue-resolution qualification is implied.
    """
    if (type(nx) is not int or type(ny) is not int or nx < 2 or ny < 2
            or ny % 2):
        raise ValueError("nx>=2 and even ny>=2 integer cell counts required")
    if crack_tip is not None and (isinstance(crack_tip, bool) or not np.isscalar(crack_tip)
            or not np.isfinite(crack_tip) or not -.5 < float(crack_tip) < .5):
        raise ValueError("crack tip must be finite and inside the square")
    x = np.linspace(-.5, .5, nx + 1)
    y = np.linspace(-.5, .5, ny + 1)
    tip = None
    tip_index = None
    if crack_tip is not None:
        hits = np.flatnonzero(np.isclose(x, float(crack_tip), rtol=0., atol=1.e-13))
        if len(hits) != 1:
            raise ValueError("crack tip must lie on an x node; no implicit snapping")
        tip_index = int(hits[0])
        # Use the exact generated coordinate, not a nearby supplied float.
        tip = float(x[tip_index])
    xx, yy = np.meshgrid(x, y, indexing="xy")
    points = np.column_stack((xx.ravel(), yy.ravel()))
    cells = []
    for row in range(ny):
        for col in range(nx):
            node = row * (nx + 1) + col
            cells.append((node, node + 1, node + nx + 2, node + nx + 1))
    crack = np.zeros(len(points), dtype=bool)
    if tip_index is not None:
        crack[(ny // 2) * (nx + 1) + np.arange(tip_index + 1)] = True
    return StructuredQ4Mesh(
        _immutable(points, np.float64), _immutable(cells, np.int64),
        _immutable(crack, bool), _immutable(np.arange(nx + 1), np.int64),
        _immutable(ny * (nx + 1) + np.arange(nx + 1), np.int64),
        _immutable(np.arange(ny + 1) * (nx + 1), np.int64),
        _immutable(np.arange(ny + 1) * (nx + 1) + nx, np.int64), nx, ny, tip)


def unsettled_zero_state(mesh, *, mesh_id, physics_id, load_id="unsettled-zero"):
    """Return a feasible *unsettled* payload in the existing state container.

    AcceptedState is the shared immutable container, not an acceptance receipt.
    d=1 only at the notch, u/A/r/opaque=0, f=1.  No history is hand-edited
    thereafter; the runner must verify each branch's zero-settle acceptance and
    common settled state. Backend identities come from the actual backend.
    """
    if not isinstance(mesh, StructuredQ4Mesh):
        raise ValueError("a generated StructuredQ4Mesh is required")
    shape = (len(mesh.cells), 4)
    return AcceptedState(np.zeros(2 * len(mesh.points)), mesh.crack.astype(float),
                         np.zeros(shape), np.zeros(shape), np.ones(shape),
                         np.zeros(shape), 0, 0, _identity(mesh_id, "mesh_id"),
                         _identity(physics_id, "physics_id"),
                         _identity(load_id, "load_id"))


@dataclass(frozen=True)
class LoadStep:
    trajectory_id: str
    step: int
    cycle: int
    segment: str
    segment_cycle: int
    substep: int
    phase: str
    branch: str
    amplitude: float
    fraction: float
    prescribed_load: float


def _finite_nonnegative_sequence(values, label, *, nonempty=True):
    a = np.asarray(values, dtype=float)
    if (a.ndim != 1 or (nonempty and not a.size) or not np.isfinite(a).all()
            or np.any(a < 0)):
        raise ValueError(f"{label} must be a finite nonnegative sequence")
    return tuple(float(x) for x in a)


def build_branch_schedule(*, trajectory_id, prehistory_amplitudes,
                          probe_amplitudes, future_amplitudes, fractions,
                          include_settle=True):
    """Expand arbitrary per-cycle nonnegative amplitudes without solving.

    All cycles use the supplied fractions, which must include a unit peak
    and end at exactly zero.  Absolute cycles count from 1 across all segments;
    segment_cycle restarts at 1 in each segment. ``phase`` identifies the
    within-cycle position (zero/peak/intermediate), while ``branch`` records
    the actual load direction (loading/unloading/hold). A zero amplitude is
    permitted and has a hold branch, even at the nominal peak substep.
    By default step 1 is a zero-load settle (cycle/substep 0). Explicitly omit
    it only for a separately accepted-root workflow whose runner checks that
    receipt. Schedule construction itself does not execute settlement.
    """
    _identity(trajectory_id, "trajectory_id")
    if type(include_settle) is not bool:
        raise ValueError("include_settle must be boolean")
    fractions = _finite_nonnegative_sequence(fractions, "fractions")
    if (len(fractions) < 2 or fractions[-1] != 0. or max(fractions) != 1.
            or any(x > 1. for x in fractions)):
        raise ValueError("fractions must include 1, stay in [0,1], and end at 0")
    groups = (("prehistory", prehistory_amplitudes),
              ("probe", probe_amplitudes), ("future", future_amplitudes))
    steps = ([LoadStep(trajectory_id, 1, 0, "settle", 0, 0, "settle",
                       "unloaded", 0., 0., 0.)] if include_settle else [])
    cycle = 0
    previous_load = 0.
    for segment, amplitudes in groups:
        amplitudes = _finite_nonnegative_sequence(amplitudes, segment)
        for local_cycle, amplitude in enumerate(amplitudes, 1):
            cycle += 1
            for substep, fraction in enumerate(fractions, 1):
                load = amplitude * fraction
                if not np.isfinite(load):
                    raise ValueError("nonfinite prescribed load")
                branch = ("loading" if load > previous_load else
                          "unloading" if load < previous_load else "hold")
                phase = "zero" if fraction == 0. else "peak" if fraction == 1. else "intermediate"
                steps.append(LoadStep(trajectory_id, len(steps) + 1, cycle,
                                      segment, local_cycle, substep, phase,
                                      branch, amplitude, fraction, load))
                previous_load = load
    return tuple(steps)


def _signature(steps):
    # Intentionally exclude absolute cycle/step and trajectory label: these
    # may differ for lawful prefixes, while common suffix positions must agree.
    return tuple((s.segment_cycle, s.substep, s.phase, s.branch, s.amplitude,
                  s.fraction, s.prescribed_load) for s in steps)


@dataclass(frozen=True)
class PairContract:
    source_id: str
    root_state_id: str
    mesh_id: str
    physics_id: str
    material_id: str
    boundary_id: str
    trajectory_id: str
    schedule_id: str
    prefix_id: str
    settle_id: str
    common_probe_id: str
    origin_phase: tuple
    future_suffix_id: str
    schema: str = "synthetic-matched-history-pair-v1"


def make_pair_contract(*, source_id, root_state, material: Mapping,
                       boundary_dofs, boundary_unit_values, schedule,
                       origin_step):
    """Bind one branch to a shared root and a common probe/future suffix.

    The common root is the immutable source state (possibly unsettled). The
    runner separately verifies zero-settle acceptance/equality and every
    committed descendant, or an already-settled root receipt when no settle is
    present. This metadata helper cannot certify those facts.
    The origin must be the final probe step; no future-dependent selection is
    performed here. Ordered boundary identity is preserved, never sorted away.
    """
    _identity(source_id, "source_id")
    if not isinstance(root_state, AcceptedState):
        raise ValueError("root_state must use the shared state container")
    if not isinstance(material, Mapping) or not material:
        raise ValueError("explicit material mapping required")
    dofs = np.asarray(boundary_dofs)
    values = np.asarray(boundary_unit_values, dtype=float)
    if (dofs.ndim != 1 or not dofs.size or not np.issubdtype(dofs.dtype, np.integer)
            or values.shape != dofs.shape or not np.isfinite(values).all()
            or len(np.unique(dofs)) != len(dofs) or np.any(dofs < 0)
            or np.any(dofs >= root_state.displacement.size)):
        raise ValueError("invalid ordered boundary dofs/unit values")
    schedule = tuple(schedule)
    if not schedule or not all(isinstance(s, LoadStep) for s in schedule):
        raise ValueError("a complete branch schedule is required")
    trajectory = schedule[0].trajectory_id
    if (any(s.trajectory_id != trajectory or s.step != i
            for i, s in enumerate(schedule, 1))
            or type(origin_step) is not int or not 0 < origin_step < len(schedule)):
        raise ValueError("branch identity, sequence or origin mismatch")
    # Reconstruct from cycle amplitudes to validate every recorded index/phase,
    # including serialized or manually constructed LoadStep instances.
    cycle_starts = [s for s in schedule if s.substep == 1]
    first_cycle = tuple(s.fraction for s in schedule if s.cycle == 1)
    reconstructed = build_branch_schedule(
        trajectory_id=trajectory,
        prehistory_amplitudes=[s.amplitude for s in cycle_starts if s.segment == "prehistory"],
        probe_amplitudes=[s.amplitude for s in cycle_starts if s.segment == "probe"],
        future_amplitudes=[s.amplitude for s in cycle_starts if s.segment == "future"],
        fractions=first_cycle, include_settle=schedule[0].segment == "settle")
    if reconstructed != schedule:
        raise ValueError("schedule fields do not reproduce the prescribed cycles")
    origin = schedule[origin_step - 1]
    future = schedule[origin_step:]
    probe = tuple(s for s in schedule[:origin_step] if s.segment == "probe")
    prefix = tuple(s for s in schedule[:origin_step] if s.segment == "prehistory")
    settle = tuple(s for s in schedule if s.segment == "settle")
    if origin.segment != "probe" or any(s.segment != "future" for s in future):
        raise ValueError("origin must be the final common-probe step")
    return PairContract(
        source_id, root_state.fingerprint(), root_state.mesh_id, root_state.physics_id,
        _digest(dict(material)), _digest({"dofs": dofs.tolist(), "unit_values": values.tolist()}),
        trajectory, _digest([(s.segment, *item) for s, item in zip(schedule, _signature(schedule))]),
        _digest(_signature(prefix)), _digest(_signature(settle)), _digest(_signature(probe)),
        (origin.segment, origin.segment_cycle, origin.substep, origin.phase,
         origin.branch, origin.fraction, origin.prescribed_load), _digest(_signature(future)))


def verify_pair_contract(a, b):
    """Require common physical/source context and suffix; allow distinct pasts.

    Passing does not assert current-observation equivalence, different hidden
    states, reachable future divergence, or accepted native transitions.
    """
    if not isinstance(a, PairContract) or not isinstance(b, PairContract):
        raise ValueError("two PairContract objects required")
    if a.trajectory_id == b.trajectory_id:
        raise ValueError("paired branches need distinct trajectory identities")
    for field in ("schema", "source_id", "root_state_id", "mesh_id", "physics_id",
                  "material_id", "boundary_id", "settle_id", "common_probe_id", "origin_phase",
                  "future_suffix_id"):
        if getattr(a, field) != getattr(b, field):
            raise ValueError(f"pair {field} mismatch")
    return True
