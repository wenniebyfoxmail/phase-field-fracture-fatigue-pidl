from __future__ import annotations

import copy
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Callable


GATES = {
    "displacement_residual": 4e-4,
    "projected_phase_kkt": 4e-4,
    "consecutive_damage_inf": 1e-3,
    "primal_feasibility": 1e-12,
}
PASS = "PASS_TARGET_C5_S4_ONLY_NEEDS_SEPARATE_FULL_T2_AUTHORIZATION"


def state_sha256(state: object) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _write_json_new(path: Path, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(payload).hexdigest()


def write_evidence_create_once(result: dict[str, object], destination: Path) -> dict[str, object]:
    destination.mkdir(parents=True, exist_ok=False)
    attempts = result.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError("controller result attempts must be a list")
    inventory: list[dict[str, object]] = []
    for expected, row in enumerate(attempts, start=1):
        if not isinstance(row, dict) or row.get("attempt") != expected:
            raise ValueError("attempt ledger must be consecutive and one-based")
        attempt_root = destination / f"attempt_{expected:04d}"
        attempt_root.mkdir(exist_ok=False)
        path = attempt_root / "ATTEMPT.json"
        inventory.append({"attempt": expected, "path": path.relative_to(destination).as_posix(), "sha256": _write_json_new(path, row)})
    receipt = {
        "schema_version": "toy_road_t2_cont_evidence_v1",
        "diagnostic_only_nonproduction": True,
        "trajectory_authorized": False,
        "classification": result.get("classification"),
        "attempt_count": len(attempts),
        "attempt_inventory": inventory,
        "tot_en_role": "auxiliary_only_not_a_controller_input",
    }
    _write_json_new(destination / "T2_CONT_RESULT.json", receipt)
    return receipt


def stage_passes(stage: dict[str, object]) -> bool:
    if stage.get("newton_converged") is not True or stage.get("native_stagger_converged") is not True:
        return False
    count = stage.get("stagger_count")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
        return False
    return all(
        not isinstance(stage.get(field), bool)
        and isinstance(stage.get(field), (int, float))
        and float(stage[field]) <= limit
        for field, limit in GATES.items()
    )


def _gc(lam: Fraction) -> float:
    return float(Fraction(1, 100) - Fraction(1, 500) * lam)


def run_controller(
    solve_stage: Callable[[float, dict[str, object], float], dict[str, object]],
    entry_state: dict[str, object],
    *,
    h0: Fraction = Fraction(1, 4),
    hmin: Fraction = Fraction(1, 128),
    max_attempts: int = 24,
) -> dict[str, object]:
    accepted = copy.deepcopy(entry_state)
    frozen = {key: copy.deepcopy(accepted.get(key)) for key in ("d_lb", "history_pre")}
    attempts: list[dict[str, object]] = []
    lam, step = Fraction(0), Fraction(h0)
    for attempt_index in range(1, max_attempts + 1):
        anchor = attempt_index == 1
        trial_lam = Fraction(0) if anchor else min(Fraction(1), lam + step)
        trial_step = Fraction(0) if anchor else trial_lam - lam
        start_snapshot = copy.deepcopy(accepted)
        start_hash = state_sha256(start_snapshot)
        stage = solve_stage(_gc(trial_lam), accepted, float(trial_lam))
        if state_sha256(accepted) != start_hash:
            return {"classification": "FAIL_T2_CONT_ROLLBACK_INTEGRITY", "attempts": attempts}
        new_state = stage.get("new_state")
        if not isinstance(new_state, dict) or any(new_state.get(key) != value for key, value in frozen.items()):
            return {"classification": "FAIL_T2_CONT_ROLLBACK_INTEGRITY", "attempts": attempts}
        passed = stage_passes(stage)
        row = {
            "attempt": attempt_index,
            "lambda": float(trial_lam),
            "Gc": _gc(trial_lam),
            "step": float(trial_step),
            "start_sha256": start_hash,
            "end_sha256": state_sha256(new_state),
            "outcome": "ACCEPT" if passed else "REJECT",
            "reason": "all_gates_pass" if passed else "stage_or_gate_failure",
            "stagger_count": stage.get("stagger_count"),
            "raw_phase_residual": stage.get("raw_phase_residual"),
            **{field: stage.get(field) for field in GATES},
        }
        if not passed:
            row["rollback_sha256"] = state_sha256(start_snapshot)
            attempts.append(row)
            if anchor:
                return {"classification": "FAIL_T2_CONT_ANCHOR_NONCONVERGENCE", "attempts": attempts}
            if trial_step <= hmin:
                return {"classification": "FAIL_T2_CONT_MIN_STEP_AT_C5_S4", "attempts": attempts, "last_accepted_lambda": float(lam)}
            step = trial_step / 2
            accepted = start_snapshot
            continue
        accepted = copy.deepcopy(new_state)
        lam = trial_lam
        attempts.append(row)
        if lam == 1:
            return {"classification": PASS, "attempts": attempts, "target_lambda": 1.0, "target_gc": 0.008, "final_state_sha256": state_sha256(accepted)}
        count = int(stage["stagger_count"])
        if anchor:
            step = Fraction(h0)
        elif count <= 250:
            step = min(Fraction(1) - lam, trial_step * 2)
        elif count <= 750:
            step = min(Fraction(1) - lam, trial_step)
        else:
            step = min(Fraction(1) - lam, trial_step / 2)
        if step < hmin:
            step = hmin
    return {"classification": "FAIL_T2_CONT_ATTEMPT_CAP_AT_C5_S4", "attempts": attempts, "last_accepted_lambda": float(lam)}
