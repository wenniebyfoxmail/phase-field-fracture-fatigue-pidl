#!/usr/bin/env python3
"""Render the sealed multi-trajectory readiness decision without training."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from multi_trajectory_forecast_protocol import (  # noqa: E402
    FrozenTrajectoryContractRef,
    TrajectoryAdapterRegistry,
    assess_readiness,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--producer-contract", type=Path)
    parser.add_argument("--producer-contract-sha256")
    parser.add_argument("--producer-schema-id")
    parser.add_argument("--producer-adapter-id")
    parser.add_argument(
        "--producer-split-verified",
        action="store_true",
        help="Use only after Agent2 freezes and signs leave-one-combination-out.",
    )
    parser.add_argument(
        "--capacity-manifest-verified",
        action="store_true",
        help="Use only after a parameter-count manifest passes the sealed tolerance.",
    )
    return parser.parse_args()


def render_markdown(report: dict) -> str:
    blockers = "\n".join(f"- {item}" for item in report["blockers"]) or "- none"
    risk_blockers = (
        "\n".join(f"- {item}" for item in report["risk_blockers"]) or "- none"
    )
    tasks = "\n".join(
        f"- {name}: {str(ready).lower()}"
        for name, ready in report["task_readiness"].items()
    )
    return f"""# Multi-trajectory forecast readiness

## Verdict

{report["status"]}. Training allowed: {str(report["training_allowed"]).lower()}.

- Producer contract: {report["contract_status"]}
- Independent trajectories: {report["independence_group_count"]}
- Field training allowed: {str(report["field_training_allowed"]).lower()}
- Transition training allowed: {str(report["transition_training_allowed"]).lower()}
- Risk training allowed: {str(report["risk_training_allowed"]).lower()}

## Task readiness

{tasks}

## Blockers

{blockers}

## Hazard/RUL blockers

{risk_blockers}

## Boundary

This is a tooling/readiness result. Repeated cycles from one numerical trajectory
cannot satisfy the independence gate. Rolling h1-h3 fields and transition
hazard/RUL are separate outputs; an unlimited free rollout is not a road
long-horizon forecast.
"""


def main() -> None:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    registry = TrajectoryAdapterRegistry()
    reference = FrozenTrajectoryContractRef(
        path=args.producer_contract,
        expected_sha256=args.producer_contract_sha256,
        schema_id=args.producer_schema_id,
        adapter_id=args.producer_adapter_id,
    )
    probe = registry.probe(reference)
    report = assess_readiness(
        probe,
        protocol_id=protocol["protocol_id"],
        minimum_independent_trajectories=int(
            protocol["split"]["minimum_independent_trajectories"]
        ),
        producer_split_verified=args.producer_split_verified,
        capacity_manifest_verified=args.capacity_manifest_verified,
        required_independence_groups=tuple(
            protocol["split"]["required_factorial_combinations"]
        ),
    ).to_dict()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "training_allowed": report["training_allowed"],
            }
        )
    )


if __name__ == "__main__":
    main()
