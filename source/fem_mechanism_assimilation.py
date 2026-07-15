"""Transparent state updates for the FEM mechanism-operator assimilation gate.

This module does not train a model and does not hide FEM state inside a learned
correction.  Each assimilation scenario explicitly declares which channels and
which elements are observed.  The update is a deterministic nudging analysis
used to determine the minimum information needed before a locked c89 forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import torch


CHANNEL_INDEX = {
    "damage": 0,
    "alpha_bar": 1,
    "fatigue_degradation": 2,
    "log10_psi_raw": 3,
}


@dataclass(frozen=True)
class AssimilationScenario:
    name: str
    description: str
    channel_masks: Mapping[str, str]
    gain: float = 1.0
    observation_class: str = "synthetic_diagnostic"
    permute_observations: bool = False

    def __post_init__(self) -> None:
        unknown = set(self.channel_masks) - set(CHANNEL_INDEX)
        if unknown:
            raise ValueError(f"unknown assimilation channels: {sorted(unknown)}")
        allowed_masks = {"all", "visible_damage", "fixed_probes"}
        unknown_masks = set(self.channel_masks.values()) - allowed_masks
        if unknown_masks:
            raise ValueError(f"unknown assimilation masks: {sorted(unknown_masks)}")
        if not 0.0 <= self.gain <= 1.0:
            raise ValueError("assimilation gain must lie in [0, 1]")


SCENARIOS: tuple[AssimilationScenario, ...] = (
    AssimilationScenario(
        "none",
        "No state update; locked operator forecast control.",
        {},
        observation_class="control",
    ),
    AssimilationScenario(
        "damage_visible",
        "Noiseless phase-field values only on the union of observed/predicted d>=0.25 support.",
        {"damage": "visible_damage"},
        observation_class="synthetic_vision_proxy",
    ),
    AssimilationScenario(
        "damage_full",
        "Noiseless full-field damage; optimistic dense-imaging diagnostic.",
        {"damage": "all"},
        observation_class="oracle_dense_damage",
    ),
    AssimilationScenario(
        "raw_fixed_probes",
        "Noiseless raw-driver log values at fixed crack-corridor probes.",
        {"log10_psi_raw": "fixed_probes"},
        observation_class="synthetic_sensor_proxy",
    ),
    AssimilationScenario(
        "damage_visible_raw_fixed_probes",
        "Visible damage support plus fixed crack-corridor raw-driver probes.",
        {"damage": "visible_damage", "log10_psi_raw": "fixed_probes"},
        observation_class="synthetic_vision_sensor_proxy",
    ),
    AssimilationScenario(
        "damage_visible_raw_fixed_probes_permuted",
        "Negative control with identical masks and reversed observed values within each channel.",
        {"damage": "visible_damage", "log10_psi_raw": "fixed_probes"},
        observation_class="negative_control",
        permute_observations=True,
    ),
    AssimilationScenario(
        "raw_full",
        "Noiseless full-field raw driver; hidden-mechanics diagnostic.",
        {"log10_psi_raw": "all"},
        observation_class="oracle_channel_ablation",
    ),
    AssimilationScenario(
        "history_fatigue_full",
        "Noiseless full-field history and fatigue degradation; hidden-memory diagnostic.",
        {"alpha_bar": "all", "fatigue_degradation": "all"},
        observation_class="oracle_channel_ablation",
    ),
    AssimilationScenario(
        "damage_raw_full",
        "Noiseless full-field damage and raw driver; mechanism-channel upper bound.",
        {"damage": "all", "log10_psi_raw": "all"},
        observation_class="oracle_channel_ablation",
    ),
    AssimilationScenario(
        "full_state_oracle",
        "Noiseless full state at declared observation cycles; forecastability ceiling.",
        {name: "all" for name in CHANNEL_INDEX},
        observation_class="oracle_ceiling",
    ),
)


def fixed_crack_corridor_probes(
    centroids: np.ndarray,
    *,
    x_count: int = 64,
    y_offsets: tuple[float, ...] = (-0.025, 0.0, 0.025),
    x_margin_fraction: float = 0.025,
) -> np.ndarray:
    """Select deterministic mesh elements nearest a fixed crack-corridor grid.

    Probe placement uses geometry only.  It does not inspect FEM damage, driver,
    history, or event labels.
    """
    xy = np.asarray(centroids, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise ValueError("centroids must have shape [elements, 2]")
    if x_count < 2:
        raise ValueError("x_count must be at least two")
    x_min, x_max = float(xy[:, 0].min()), float(xy[:, 0].max())
    margin = x_margin_fraction * (x_max - x_min)
    targets_x = np.linspace(x_min + margin, x_max - margin, x_count)
    selected: set[int] = set()
    for y in y_offsets:
        for x in targets_x:
            distance = (xy[:, 0] - x) ** 2 + (xy[:, 1] - y) ** 2
            selected.add(int(np.argmin(distance)))
    mask = np.zeros(len(xy), dtype=bool)
    mask[np.fromiter(sorted(selected), dtype=np.int64)] = True
    return mask


def observation_masks(
    forecast: torch.Tensor,
    observation: torch.Tensor,
    fixed_probes: torch.Tensor,
    *,
    visible_damage_threshold: float = 0.25,
) -> dict[str, torch.Tensor]:
    if forecast.shape != observation.shape:
        raise ValueError("forecast and observation shapes must match")
    if fixed_probes.shape != forecast.shape[:1]:
        raise ValueError("fixed probe mask must match the element axis")
    return {
        "all": torch.ones(len(forecast), dtype=torch.bool, device=forecast.device),
        "visible_damage": (
            (forecast[:, CHANNEL_INDEX["damage"]] >= visible_damage_threshold)
            | (observation[:, CHANNEL_INDEX["damage"]] >= visible_damage_threshold)
        ),
        "fixed_probes": fixed_probes.to(device=forecast.device, dtype=torch.bool),
    }


def assimilate_state(
    forecast: torch.Tensor,
    observation: torch.Tensor,
    previous_state: torch.Tensor,
    scenario: AssimilationScenario,
    fixed_probes: torch.Tensor,
    *,
    visible_damage_threshold: float = 0.25,
) -> tuple[torch.Tensor, dict[str, int | float]]:
    """Apply an explicit nudging update and reimpose state admissibility."""
    if forecast.shape != observation.shape or forecast.shape != previous_state.shape:
        raise ValueError("forecast, observation, and previous state must share a shape")
    masks = observation_masks(
        forecast,
        observation,
        fixed_probes,
        visible_damage_threshold=visible_damage_threshold,
    )
    analysis = forecast.clone()
    diagnostics: dict[str, int | float] = {
        "observed_values": 0,
        "observed_elements": 0,
        "analysis_rms_increment": 0.0,
    }
    observed_union = torch.zeros(len(forecast), dtype=torch.bool, device=forecast.device)
    for channel, mask_name in scenario.channel_masks.items():
        channel_index = CHANNEL_INDEX[channel]
        mask = masks[mask_name]
        observed_values = observation[mask, channel_index]
        if scenario.permute_observations:
            observed_values = observed_values.flip(0)
        innovation = observed_values - forecast[mask, channel_index]
        analysis[mask, channel_index] = forecast[mask, channel_index] + scenario.gain * innovation
        diagnostics["observed_values"] += int(mask.sum().item())
        observed_union |= mask

    analysis[:, 0] = torch.maximum(previous_state[:, 0], analysis[:, 0]).clamp(0.0, 1.0)
    analysis[:, 1] = torch.maximum(previous_state[:, 1], analysis[:, 1]).clamp_min(0.0)
    analysis[:, 2] = torch.minimum(previous_state[:, 2], analysis[:, 2]).clamp(0.0, 1.0)
    analysis[:, 3] = analysis[:, 3].clamp(-12.0, 6.0)
    diagnostics["observed_elements"] = int(observed_union.sum().item())
    diagnostics["analysis_rms_increment"] = float(
        torch.sqrt(torch.mean((analysis - forecast).square())).detach().cpu()
    )
    return analysis, diagnostics


def scenario_by_name(name: str) -> AssimilationScenario:
    for scenario in SCENARIOS:
        if scenario.name == name:
            return scenario
    raise KeyError(name)
