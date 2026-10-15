"""Render the compact saved-output replay decision figure; never fits or loads sources."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def generate(output: Path) -> dict:
    decision = json.loads((output / 'decision.json').read_text())
    with (output / 'aggregate_comparison.csv').open(newline='') as handle:
        aggregates = list(csv.DictReader(handle))
    with (output / 'percycle_comparison.csv').open(newline='') as handle:
        cycles = list(csv.DictReader(handle))
    if len(aggregates) != 4 or len(cycles) != 357:
        raise ValueError('incomplete replay tables')
    keys = [row['holdout'] for row in aggregates]
    aggregate_errors = np.array([
        max(abs(float(row['replay_R']) - float(row['saved_R'])),
            abs(float(row['replay_G']) - float(row['saved_G'])))
        for row in aggregates
    ])
    tolerance_fraction = []
    for key in keys:
        subset = [row for row in cycles if row['holdout'] == key]
        tolerance_fraction.append(max(
            max(float(row['V0_tolerance_fraction']), float(row['V1_tolerance_fraction']))
            for row in subset))
    tolerance_fraction = np.array(tolerance_fraction)
    if not np.isfinite(aggregate_errors).all() or not np.isfinite(tolerance_fraction).all():
        raise ValueError('nonfinite replay diagnostics')
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    axes[0].bar(keys, aggregate_errors, color='#4477AA')
    axes[0].axhline(1e-12, color='0.45', linestyle='--', label='allowed absolute difference')
    axes[0].set_yscale('symlog', linthresh=1e-16)
    axes[0].set_ylabel('max |replay - saved| for R/G')
    axes[0].set_title('aggregate reproduction')
    axes[0].legend(fontsize=8)
    axes[1].bar(keys, tolerance_fraction, color='#228833')
    axes[1].axhline(1.0, color='0.45', linestyle='--', label='mixed-tolerance limit')
    axes[1].set_ylabel('max per-cycle tolerance fraction')
    axes[1].set_title('357-row MSE reproduction')
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.spines[['top', 'right']].set_visible(False)
    figure.suptitle('S04-E022 frozen-model replay | lower than dashed limit required')
    figure.tight_layout()
    figure.savefig(output / 'replay_decision.png', dpi=180)
    plt.close(figure)
    note = f"""# How to read `replay_decision.png`

## How to read

The left panel shows the largest absolute difference between independently
replayed and frozen `R/G` for each holdout. The dashed line is the frozen
`1e-12` aggregate limit. The right panel shows the largest fraction of the
mixed per-cycle MSE tolerance consumed; values must remain at or below one.

## Data provenance

The figure is rendered only from `aggregate_comparison.csv`,
`percycle_comparison.csv` and `decision.json` created by the no-fit replay.
It never reads source trajectories, coefficients or confirmation data and does
not rerun a prediction.

## Limitation

Passing this figure supports arithmetic reproduction of the frozen E021 model
outputs only. It does not validate physical truth, a FEM teacher, new-amplitude
generalisation, pointwise equality at unsaved cycles, or a need for NN/PIDL
training. Frozen parent outcome: `{decision['parent_outcome']}`.
"""
    (output / 'replay_decision.md').write_text(note)
    (output / 'README_analysis.md').write_text(f"""# S04-E022 replay analysis

## Scientific question

Can an independent no-fit implementation reproduce the frozen S04-E021
physical-raw predictions and their saved error summaries from the approved
development package?

## Evidence source and reading order

The authoritative inputs to this analysis are `percycle_comparison.csv`,
`aggregate_comparison.csv` and `decision.json` produced by the replay. Read
`replay_decision.png` first, then its same-stem `replay_decision.md`, and use
the CSV/JSON tables for exact values.

## What the figure shows

The left panel compares independently replayed versus saved fold-level `R/G`;
the right panel compares all 357 saved versus replayed cycle-level MSE values.
Both panels expose the preregistered numerical limits as dashed lines.

## Cross-figure interpretation and allowed conclusion

There is one decision figure. If every bar remains below its dashed limit and
the JSON status is `REPLAY_REPRODUCED`, the frozen E021 arithmetic is
independently reproducible without fitting or parameter selection. Frozen
parent outcome: `{decision['parent_outcome']}`.

## Blocked conclusion and storyline impact

This does not validate physical truth, a FEM teacher, a new amplitude,
forecast skill, pointwise equality at states that E021 did not save, or a need
for PIDL/NN training. It only strengthens the integrity of the existing S04
directional-development result; it cannot upgrade that bounded claim.
""")
    return dict(aggregate_max_abs_difference=float(aggregate_errors.max()),
                percycle_max_tolerance_fraction=float(tolerance_fraction.max()),
                figure='replay_decision.png')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    generate(args.out.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
