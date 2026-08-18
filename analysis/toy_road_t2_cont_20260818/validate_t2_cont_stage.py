from __future__ import annotations

import argparse
import json
from pathlib import Path


GATES = {
    "displacement_residual": 4e-4,
    "projected_phase_kkt": 4e-4,
    "consecutive_damage_inf": 1e-3,
    "primal_feasibility": 1e-12,
}


def stage_passes(stage: dict[str, object]) -> bool:
    if stage.get("newton_converged") is not True or stage.get("native_stagger_converged") is not True:
        return False
    count = stage.get("stagger_count")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
        return False
    for field, limit in GATES.items():
        value = stage.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not float(value) <= limit:
            return False
    return True


def validate(path: Path) -> dict[str, object]:
    stage = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    if not isinstance(stage, dict):
        raise ValueError("stage receipt must be one object")
    return {"passes": stage_passes(stage), "gates": GATES}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
