"""Explicit state-assimilation primitives for declared fracture observations.

The package contains deterministic update rules and scenario declarations only.
It does not acquire observations, read experiment payloads, or run forecasts.
"""

from .fem_mechanism_assimilation import (
    AssimilationScenario,
    CHANNEL_INDEX,
    SCENARIOS,
    assimilate_state,
    fixed_crack_corridor_probes,
    observation_masks,
    scenario_by_name,
)

__all__ = [
    "AssimilationScenario",
    "CHANNEL_INDEX",
    "SCENARIOS",
    "assimilate_state",
    "fixed_crack_corridor_probes",
    "observation_masks",
    "scenario_by_name",
]
