from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from freeze_select.structured_adapter import AdapterConfig, StructuredFieldAdapter  # noqa: E402
from freeze_select.synthetic_forecast import (  # noqa: E402
    ForecastConfig,
    generate_dynamic_truth,
    run_stage_a2,
    sample_sparse_observations,
)


def test_structured_adapter_rejects_future_damage_and_recovers_smooth_field() -> None:
    x = np.linspace(0.0, 1.0, 12)
    y = np.linspace(-0.5, 0.5, 6)
    time = np.linspace(0.0, 4.0, 9)
    rows = []
    for t in time:
        for yy in y:
            for xx in x:
                rows.append((xx, yy, t, 0.2 + 0.1 * np.cos(np.pi * xx) + 0.03 * t))
    frame = pd.DataFrame(rows, columns=["x", "y", "time", "damage_observed"])
    adapter = StructuredFieldAdapter(
        AdapterConfig(
            x_modes=3,
            y_modes=2,
            temporal_basis=6,
            ridge=1e-8,
            defect_scales=(),
            wheelpath_scales=(),
        ),
        cutoff_time=4.0,
    )
    adapter.fit(frame.iloc[::3])
    prediction = adapter.predict(frame)
    assert float(np.sqrt(np.mean(np.square(prediction - frame["damage_observed"])))) < 0.02
    future = pd.DataFrame({"x": [0.5], "y": [0.0], "time": [4.1]})
    with np.testing.assert_raises_regex(ValueError, "future damage"):
        adapter.predict(future)


def test_dynamic_generator_is_linked_to_declared_correction_and_observations_stop_at_cutoff() -> None:
    config = ForecastConfig(nx=12, ny=6, n_times=13, n_sections=4, cutoff_index=7)
    corrected = generate_dynamic_truth(config)
    fixed = generate_dynamic_truth(config, beta={})
    assert not np.allclose(corrected["d"].to_numpy(), fixed["d"].to_numpy())
    observations = sample_sparse_observations(corrected, config)
    assert observations["cycle"].max() <= config.cutoff_index
    assert "d" not in observations.columns


def test_stage_a2_smoke_writes_leakage_safe_forecast_package(tmp_path: Path) -> None:
    config = ForecastConfig(
        nx=14,
        ny=8,
        n_times=17,
        n_sections=8,
        cutoff_index=10,
        observation_rate=0.35,
        noise_sigma=0.005,
        seed=11,
        n_trials=16,
        n_windows=96,
    )
    result = run_stage_a2(
        config,
        tmp_path,
        adapter_config=AdapterConfig(x_modes=4, y_modes=3, temporal_basis=7, ridge=1e-5),
    )
    assert result["claim_class"] == "tooling-only"
    assert result["joint_training_baseline_executed"] is False
    assert {
        "claim_boundary.md",
        "decision.md",
        "forecast_metrics.csv",
        "freeze_snapshot.npz",
        "freeze_snapshot_hash.txt",
        "section_metrics.csv",
        "split_manifest.json",
        "support_summary.csv",
    }.issubset({path.name for path in tmp_path.iterdir()})
