"""Explicit-substep, mixed-support contracts for fixed-weight prototypes.

This is a numerical-reference interface, not a state-sufficiency proof. It is
not an automatic converter for FYR PIDL archives. In this FEM-like family H
is current undegraded energy; alpha_bar and q_prev carry fatigue memory. H
and q_prev may decrease on unloading. Cycle/substep labels are provenance,
never a replacement for a prescribed loading action.

No function here discovers or opens an archive. The adapter accepts an explicit
loader and denies protected or unqualified records before invoking that loader.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral
from typing import Callable, Iterable, Iterator, Sequence

import torch

from s09_q4_quadrature import q4_shape_data
from s09_stage0a_transition import carrara_f


BOUNDARY_FAMILY = "clamped_tensile_y"
# This version is defined only for BOUNDARY_FAMILY; the record retains both
# identifiers so an adapter cannot label a shear family as vertical tension.
SEMANTICS = "explicit_substep_post_commit_v1"
RECOVERED_INITIAL_SEMANTICS = "explicit_recovered_initial_and_post_commit_v2"
HISTORY_NAMES = ("H", "alpha_bar", "q_prev")
SPLITS = frozenset(("train", "validation", "test", "protected"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _nonempty(value: str, name: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} must be nonempty")


def _integer(value: int, name: str, minimum: int = 0) -> None:
    _require(isinstance(value, Integral) and not isinstance(value, bool)
             and value >= minimum, f"{name} must be an integer >= {minimum}")


def _finite_scalar(value: float, name: str) -> None:
    _require(not isinstance(value, bool) and isinstance(value, (int, float))
             and math.isfinite(value), f"{name} must be a finite scalar")


def _validate_key_fields(key: StateKey) -> None:
    for name in ("trajectory_id", "condition_id", "reference_id", "mesh_id"):
        _nonempty(getattr(key, name), name)
    for name in ("cycle", "substep", "ordinal"):
        _integer(getattr(key, name), name)
    _require(key.branch in ("initial", "load", "unload", "hold"), "unknown load branch")
    _finite_scalar(key.load, "load")


@dataclass(frozen=True)
class StateKey:
    trajectory_id: str
    condition_id: str
    reference_id: str
    mesh_id: str
    cycle: int
    substep: int
    ordinal: int
    branch: str
    load: float
    timing: str = "post_history_commit"

    def validate(self) -> None:
        _validate_key_fields(self)
        _require(self.timing == "post_history_commit", "only post-history committed states are supported")


@dataclass(frozen=True)
class RecoveredInitialKey(StateKey):
    """Explicit native c1/s00 after zero-load recovery, before cyclic steps.

    This retains the producer's pre-cycle timing; it is never relabelled as a
    post-history-commit state. Later s00 aliases are not recovered initial states.
    """
    timing: str = "pre_cycle_committed"

    def validate(self) -> None:
        _validate_key_fields(self)
        _require(self.timing == "pre_cycle_committed", "recovered initial timing must remain pre-cycle committed")
        _require((self.cycle, self.substep, self.ordinal) == (1, 0, 0),
                 "recovered initial key must be native c0001_s00 at ordinal zero")
        _require(self.branch == "initial" and self.load == 0.0,
                 "recovered initial state requires initial branch and zero load")


@dataclass(frozen=True)
class Material:
    E: float
    nu: float
    Gc: float
    ell: float
    alpha_t: float
    fatigue_power: float
    residual_stiffness: float
    thickness: float

    def validate(self) -> None:
        for name in self.__dataclass_fields__:
            _finite_scalar(getattr(self, name), name)
        for name in ("E", "Gc", "ell", "alpha_t", "fatigue_power", "thickness"):
            _require(getattr(self, name) > 0, f"{name} must be positive")
        _require(-1 < self.nu < 0.5, "nu must lie strictly between -1 and 0.5")
        _require(0 <= self.residual_stiffness <= 1, "residual_stiffness must lie in [0,1]")

    def features(self, like: torch.Tensor) -> torch.Tensor:
        self.validate()
        _require(like.is_floating_point(), "material feature reference must be floating point")
        return like.new_tensor([getattr(self, name) for name in self.__dataclass_fields__])


@dataclass(frozen=True)
class Mesh:
    xy: torch.Tensor
    conn: torch.Tensor
    mesh_id: str

    def _validate_arrays(self) -> None:
        _nonempty(self.mesh_id, "mesh_id")
        _require(self.xy.ndim == 2 and self.xy.shape[1] == 2 and len(self.xy) >= 4,
                 "xy must be [node,2] with at least four nodes")
        _require(self.xy.is_floating_point() and bool(torch.isfinite(self.xy).all()),
                 "xy must contain finite floating point coordinates")
        _require(self.conn.ndim == 2 and self.conn.shape[1] == 4 and len(self.conn) > 0,
                 "conn must be nonempty [element,4]")
        _require(self.conn.dtype == torch.long, "conn must have torch.long dtype")
        _require(self.conn.device == self.xy.device, "mesh arrays must share a device")
        _require(bool((self.conn >= 0).all()) and bool((self.conn < len(self.xy)).all()),
                 "connectivity index out of range")
        ordered = torch.sort(self.conn, dim=1).values
        _require(bool((ordered[:, 1:] != ordered[:, :-1]).all()), "Q4 element repeats a node")
        _require(torch.unique(self.conn).numel() == len(self.xy), "mesh contains unsupported nodes")

    def validate(self) -> None:
        self.quadrature()

    def quadrature(self) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        self._validate_arrays()
        shape, dshape, det = q4_shape_data(self.xy, self.conn)
        _require(bool(torch.isfinite(dshape).all()) and bool(torch.isfinite(det).all()),
                 "nonfinite Q4 quadrature")
        return shape, dshape, det


@dataclass(frozen=True)
class State:
    """Committed reference state for clamped vertical tension.

    ``d_lower`` is retained separately to make archive provenance inspectable,
    but at this post-history-commit boundary it must equal accepted ``d``.
    Stale bounds and FYR's penalty-history conventions need a different
    explicit adapter; neither is silently coerced into this contract.
    """
    key: StateKey
    u: torch.Tensor
    d: torch.Tensor
    d_lower: torch.Tensor
    history: torch.Tensor

    def validate(self, mesh: Mesh, material: Material) -> None:
        _require(not isinstance(self.key, RecoveredInitialKey),
                 "recovered initial key requires explicit RecoveredInitialState")
        self.key.validate()
        self._validate_payload(mesh, material)

    def _validate_payload(self, mesh: Mesh, material: Material) -> None:
        mesh.validate()
        material.validate()
        _require(self.key.mesh_id == mesh.mesh_id, "state mesh identity mismatch")
        shapes = {"u": (len(mesh.xy), 2), "d": (len(mesh.xy),),
                  "d_lower": (len(mesh.xy),), "history": (len(mesh.conn), 4, 3)}
        for name, shape in shapes.items():
            value = getattr(self, name)
            _require(value.shape == shape, f"{name} must have shape {shape}")
            _require(value.is_floating_point() and bool(torch.isfinite(value).all()),
                     f"{name} must contain finite floating point values")
            _require(value.device == mesh.xy.device and value.dtype == mesh.xy.dtype,
                     f"{name} must share mesh dtype and device")
        _require(bool((self.d >= 0).all()) and bool((self.d <= 1).all()), "damage must lie in [0,1]")
        _require(torch.equal(self.d_lower, self.d),
                 "post-history-commit damage lower bound must equal committed damage")
        _require(bool((self.history >= 0).all()), "H, alpha_bar and q_prev must be nonnegative")
        # Exact min/max rows agree with the model's t=(y-ymin)/(ymax-ymin)
        # lifting. Eight dtype ulps at the prescribed-load scale allow only
        # floating-point roundoff, not a physical boundary mismatch. In
        # particular, no unit-sized absolute tolerance hides very small loads.
        y = mesh.xy[:, 1]
        bottom, top = y == y.min(), y == y.max()
        fixed = bottom | top
        expected = torch.zeros_like(self.u)
        expected[top, 1] = self.key.load
        precision = torch.finfo(self.u.dtype)
        tolerance = 8 * precision.eps * max(abs(self.key.load), precision.tiny)
        _require(bool((torch.abs(self.u[fixed] - expected[fixed]) <= tolerance).all()),
                 "displacement violates clamped_tensile_y boundary family")

    def fatigue(self, material: Material) -> torch.Tensor:
        """Derived factor, not a fourth independent history channel."""
        material.validate()
        return carrara_f(self.history[..., 1], material.alpha_t, material.fatigue_power)


@dataclass(frozen=True)
class RecoveredInitialState(State):
    """Recovered damage with zero displacement and reset fatigue memory.

    Source-specific code must establish native recovery provenance before
    constructing this type. Its validation checks state compatibility, not
    convergence of the recovery solve or qualification of a numerical teacher.
    """

    def validate(self, mesh: Mesh, material: Material) -> None:
        _require(isinstance(self.key, RecoveredInitialKey),
                 "recovered initial state requires explicit RecoveredInitialKey")
        self.key.validate()
        self._validate_payload(mesh, material)
        _require(bool((self.u == 0).all()), "recovered initial displacement must be exactly zero")
        _require(bool((self.history == 0).all()),
                 "recovered initial H, alpha_bar and q_prev must be exactly zero")


@dataclass(frozen=True)
class TransitionRequest:
    target: StateKey
    delta_load: float

    def validate(self, source: StateKey) -> None:
        source.validate()
        self.target.validate()
        _require(not isinstance(self.target, RecoveredInitialKey),
                 "recovered initial state can only be a transition source")
        if isinstance(source, RecoveredInitialKey):
            _require((self.target.cycle, self.target.substep) == (1, 1),
                     "recovered initial transition must target native c0001_s01")
        _finite_scalar(self.delta_load, "delta_load")
        for name in ("trajectory_id", "condition_id", "reference_id", "mesh_id"):
            _require(getattr(source, name) == getattr(self.target, name),
                     f"transition {name} mismatch")
        _require(self.target.ordinal == source.ordinal + 1, "transition must advance exactly one ordinal")
        _require((self.target.cycle, self.target.substep) > (source.cycle, source.substep),
                 "physical cycle/substep must advance")
        expected_delta = self.target.load - source.load
        _require(math.isclose(self.delta_load, expected_delta, rel_tol=1e-10, abs_tol=1e-12),
                 "delta_load disagrees with committed source and target loads")
        branch = "load" if self.delta_load > 0 else "unload" if self.delta_load < 0 else "hold"
        _require(self.target.branch == branch, "target branch disagrees with delta_load")


@dataclass(frozen=True)
class TrajectoryRecord:
    trajectory_id: str
    condition_id: str
    reference_id: str
    mesh_id: str
    split: str
    qualification_ref: str
    semantics: str = SEMANTICS
    evidence_domain: str = "synthetic"
    expected_state_count: int | None = None
    material_values: tuple[float, ...] | None = None
    boundary_family: str = BOUNDARY_FAMILY

    def validate(self) -> None:
        for name in ("trajectory_id", "condition_id", "reference_id", "mesh_id"):
            _nonempty(getattr(self, name), name)
        _require(self.split in SPLITS, "unknown trajectory split")
        _require(self.semantics in (SEMANTICS, RECOVERED_INITIAL_SEMANTICS),
                 "incompatible state semantics; explicit adapter required")
        _require(self.boundary_family == BOUNDARY_FAMILY, "unsupported boundary family")
        _require(self.evidence_domain == "synthetic", "this adapter only admits synthetic numerical references")
        if self.expected_state_count is not None:
            _integer(self.expected_state_count, "expected_state_count", 2)
        if self.material_values is not None:
            _require(len(self.material_values) == 8, "material_values must contain all eight material constants")
            Material(*self.material_values).validate()


@dataclass(frozen=True)
class SplitManifest:
    records: Sequence[TrajectoryRecord]

    def validate(self) -> None:
        trajectories: set[str] = set()
        condition_splits: dict[str, str] = {}
        _require(bool(self.records), "split manifest must not be empty")
        for record in self.records:
            record.validate()
            _require(record.trajectory_id not in trajectories, "duplicate trajectory identity")
            trajectories.add(record.trajectory_id)
            previous = condition_splits.setdefault(record.condition_id, record.split)
            _require(previous == record.split, "a complete parameter condition must stay within one split")

    def allowed_records(self, split: str) -> tuple[TrajectoryRecord, ...]:
        self.validate()
        _require(split in SPLITS, "unknown requested split")
        if split == "protected":
            raise PermissionError("protected trajectories are unavailable to this workflow")
        return tuple(record for record in self.records if record.split == split)


def iter_trajectory(
    record: TrajectoryRecord,
    loader: Callable[[TrajectoryRecord], Iterable[State]],
    mesh: Mesh,
    material: Material,
) -> Iterator[State]:
    """Stream explicit decoded states; admission requires complete exhaustion.

    The qualification pointer is an admission assertion supplied by the caller,
    not proof established by this function. An exact count is needed to check full
    coverage; a consecutive cropped window must not masquerade as a trajectory.
    The caller must validate its complete SplitManifest before selecting records.
    A yielded prefix is not an admitted trajectory: a later state, loader error,
    or final count can still fail. No training or qualification claim may use a
    partial iteration. No archive is discovered or opened here.

    Only recurrence fields from the preceding state are retained, with copies
    so an in-place loader buffer cannot change a previously accepted bound.
    Mesh validation is retained per state because frozen dataclasses do not
    make their tensor contents immutable.
    """
    record.validate()
    if record.split == "protected":
        raise PermissionError("protected trajectory denied before loader invocation")
    if not isinstance(record.qualification_ref, str) or not record.qualification_ref.strip():
        raise PermissionError("a declared qualification reference is required before loading")
    _require(record.expected_state_count is not None, "complete trajectory requires expected_state_count")
    _require(record.material_values is not None, "trajectory requires declared material_values")
    _require(record.mesh_id == mesh.mesh_id, "record mesh identity mismatch")
    mesh.validate()
    material.validate()
    expected_material = tuple(getattr(material, name) for name in material.__dataclass_fields__)
    _require(tuple(record.material_values) == expected_material, "material constants differ from manifest")
    count = 0
    old_key = old_d = old_alpha = None
    for ordinal, state in enumerate(loader(record)):
        _require(ordinal < record.expected_state_count, "trajectory state count differs from manifest")
        _require(isinstance(state, State), "loader must return State objects")
        if record.semantics == RECOVERED_INITIAL_SEMANTICS and ordinal == 0:
            _require(isinstance(state, RecoveredInitialState),
                     "v2 trajectory must begin with an explicit recovered initial state")
        else:
            _require(not isinstance(state, RecoveredInitialState),
                     "recovered initial state requires v2 semantics and the first trajectory position")
        state.validate(mesh, material)
        for name in ("trajectory_id", "condition_id", "reference_id", "mesh_id"):
            _require(getattr(state.key, name) == getattr(record, name), f"loaded {name} differs from manifest")
        _require(state.key.ordinal == ordinal, "trajectory must cover ordinals from zero without gaps")
        if ordinal:
            TransitionRequest(state.key, state.key.load - old_key.load).validate(old_key)
            _require(bool((state.d >= old_d).all()), "reference damage decreases across committed states")
            _require(bool((state.history[..., 1] >= old_alpha).all()),
                     "reference alpha_bar decreases across committed states")
        old_key = state.key
        old_d = state.d.detach().clone()
        old_alpha = state.history[..., 1].detach().clone()
        count += 1
        yield state
    _require(count == record.expected_state_count, "trajectory state count differs from manifest")


def load_trajectory(
    record: TrajectoryRecord,
    loader: Callable[[TrajectoryRecord], Iterable[State]],
    mesh: Mesh,
    material: Material,
) -> list[State]:
    """Fully exhaust validation before returning the original list-style API."""
    return list(iter_trajectory(record, loader, mesh, material))


def adapt_decoded_stage0a(
    decoded: object,
    key: StateKey,
    mesh: Mesh,
    material: Material,
    *,
    source_timing: str,
    source_semantics: str,
) -> State:
    """Adapt an already decoded native Stage-0A substep without scientific I/O.

    ``decoded`` follows ``s09_stage0a_packet.DecodedStage0AState`` by duck
    typing. The caller must explicitly establish committed timing and the
    exact state semantics; this function neither reads provenance nor opens
    MAT/HDF5. Native s01..s05 states can be adapted; s00 pre-cycle aliases are
    rejected. Adapting a single peak does not establish complete trajectory
    coverage, which the caller must qualify separately. The redundant exported
    Carrara factor is checked before being omitted.
    """
    _require(source_timing == "post_history_commit", "adapter requires post-history committed source timing")
    _require(source_semantics == SEMANTICS, "adapter requires explicit matching source semantics")
    key.validate()
    mesh.validate()
    material.validate()
    _require(key.substep in range(1, 6), "s00 pre-cycle or non-native substep cannot be adapted")
    for name in ("logical_cycle", "logical_substep", "source_state_key", "imposed_displacement",
                 "u_node", "d_node", "history_gp"):
        _require(hasattr(decoded, name), f"decoded state is missing {name}")
    _integer(decoded.logical_cycle, "decoded logical_cycle")
    _integer(decoded.logical_substep, "decoded logical_substep")
    _require(decoded.logical_cycle == key.cycle and decoded.logical_substep == key.substep,
             "decoded physical cycle/substep differs from key")
    expected_source_key = f"c{key.cycle:04d}_s{key.substep:02d}"
    _require(decoded.source_state_key == expected_source_key,
             "decoded source must be the native state; aliases are forbidden")
    _finite_scalar(decoded.imposed_displacement, "decoded imposed_displacement")
    _require(decoded.imposed_displacement == key.load, "decoded imposed displacement differs from key")

    def copy_tensor(value: object) -> torch.Tensor:
        return torch.as_tensor(value, dtype=mesh.xy.dtype, device=mesh.xy.device).detach().clone()

    u, d, history_four = (copy_tensor(value) for value in
                           (decoded.u_node, decoded.d_node, decoded.history_gp))
    _require(history_four.shape == (len(mesh.conn), 4, 4),
             "decoded history must be [element,4GP,H|alpha_bar|q_prev|f]")
    _require(bool(torch.isfinite(history_four).all()), "decoded history contains nonfinite values")
    _require(bool((history_four[..., :3] >= 0).all()), "decoded physical history must be nonnegative")
    factor = carrara_f(history_four[..., 1], material.alpha_t, material.fatigue_power)
    # Relative dtype tolerance preserves small fatigue factors; a unit-sized
    # absolute tolerance would incorrectly accept zero in their place.
    _require(bool(torch.isclose(history_four[..., 3], factor,
                               rtol=8 * torch.finfo(history_four.dtype).eps, atol=0).all()),
             "decoded fatigue factor disagrees with Carrara(alpha_bar)")
    state = State(key=key, u=u, d=d, d_lower=d.clone(), history=history_four[..., :3].clone())
    state.validate(mesh, material)
    return state
