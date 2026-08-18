"""Pure fail-closed contract for the c60-to-c61 G4 prerequisite smoke."""
from __future__ import annotations

EXPECTED_STEPS = [301, 302, 303, 304, 305]
TOTAL_DISPLACEMENT_STEPS = 306


def validate_start(
    *, displacement_count, start_raw_step, configured_steps, configured_count,
    configured_start, configured_end, risk_intervention, risk_key_present,
) -> None:
    if (
        int(displacement_count) != TOTAL_DISPLACEMENT_STEPS
        or int(start_raw_step) != EXPECTED_STEPS[0]
        or configured_steps != EXPECTED_STEPS
        or int(configured_count) != TOTAL_DISPLACEMENT_STEPS
        or int(configured_start) != EXPECTED_STEPS[0]
        or int(configured_end) != EXPECTED_STEPS[-1]
        or risk_intervention != "absent"
        or bool(risk_key_present)
    ):
        raise RuntimeError("G4 prerequisite smoke execution guard rejected the run")


def validate_completion(*, actual_raw_steps, natural_exhaustion) -> None:
    if list(actual_raw_steps) != EXPECTED_STEPS:
        raise RuntimeError(
            "G4 prerequisite smoke did not execute exactly raw steps 301 through 305"
        )
    if not natural_exhaustion:
        raise RuntimeError("G4 prerequisite smoke did not end by natural schedule exhaustion")
