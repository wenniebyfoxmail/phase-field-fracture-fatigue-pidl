from __future__ import annotations

import argparse
import json
from pathlib import Path

from freeze_select.synthetic_active_measure import run_stage_a5_oracle
from freeze_select.synthetic_forecast import ForecastConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage A5 oracle active-measure gate")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--n-trials", type=int, default=24)
    parser.add_argument("--n-windows", type=int, default=256)
    args = parser.parse_args()
    config = ForecastConfig(
        n_sections=8,
        seed=args.seed,
        observation_rate=0.20,
        noise_sigma=0.01,
        n_trials=args.n_trials,
        n_windows=args.n_windows,
        excitation_design="balanced_2pow3",
    )
    print(json.dumps(run_stage_a5_oracle(config, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
