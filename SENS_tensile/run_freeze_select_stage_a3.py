#!/usr/bin/env python3
"""Run a development-only uncertainty-aware Stage A3 case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from freeze_select.synthetic_forecast import ForecastConfig
from freeze_select.synthetic_uncertainty import run_stage_a3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--observation-rate", type=float, default=0.20)
    parser.add_argument("--noise-sigma", type=float, default=0.01)
    parser.add_argument("--n-adapters", type=int, default=8)
    parser.add_argument("--n-replicates", type=int, default=128)
    parser.add_argument("--n-trials", type=int, default=64)
    parser.add_argument("--n-windows", type=int, default=384)
    parser.add_argument("--nx", type=int, default=48)
    parser.add_argument("--ny", type=int, default=24)
    parser.add_argument("--n-times", type=int, default=41)
    parser.add_argument("--cutoff-index", type=int, default=24)
    args = parser.parse_args()
    config = ForecastConfig(
        nx=args.nx,
        ny=args.ny,
        n_times=args.n_times,
        cutoff_index=args.cutoff_index,
        seed=args.seed,
        observation_rate=args.observation_rate,
        noise_sigma=args.noise_sigma,
        n_trials=args.n_trials,
        n_windows=args.n_windows,
    )
    result = run_stage_a3(
        config,
        args.output_dir,
        n_adapters=args.n_adapters,
        n_replicates=args.n_replicates,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
