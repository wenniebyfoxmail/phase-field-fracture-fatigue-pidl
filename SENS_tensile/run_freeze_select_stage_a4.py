from __future__ import annotations

import argparse
import json
from pathlib import Path

from freeze_select.synthetic_forecast import ForecastConfig
from freeze_select.synthetic_multi_environment import run_stage_a4


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage A4 balanced multi-environment development gate")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--observation-rate", type=float, default=0.20)
    parser.add_argument("--noise-sigma", type=float, default=0.01)
    parser.add_argument("--n-trials", type=int, default=24)
    parser.add_argument("--n-windows", type=int, default=256)
    args = parser.parse_args()
    config = ForecastConfig(
        n_sections=8,
        seed=args.seed,
        observation_rate=args.observation_rate,
        noise_sigma=args.noise_sigma,
        n_trials=args.n_trials,
        n_windows=args.n_windows,
        excitation_design="balanced_2pow3",
    )
    result = run_stage_a4(config, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
