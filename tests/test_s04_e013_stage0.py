from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from export_s04_e013_paired_eta0 import mapped_step, registered_states


def test_recovery_offset_mapping_is_exact():
    assert mapped_step(20, 2) == 97
    assert mapped_step(20, 4) == 99
    assert mapped_step(20, 5) == 100
    assert mapped_step(60, 2) == 297
    assert mapped_step(60, 4) == 299
    assert mapped_step(60, 5) == 300
    assert mapped_step(82, 2) == 407
    assert mapped_step(82, 4) == 409
    assert mapped_step(82, 5) == 410
    assert mapped_step(83, 2) == 412
    assert mapped_step(83, 4) == 414
    assert mapped_step(83, 5) == 415


def test_registered_matrix_and_own_event_are_complete():
    states = registered_states()
    matrix = [state for state in states if state.comparison_class == "same_cycle"]
    event = [state for state in states if state.comparison_class == "own_event_first_detect"]
    assert len(matrix) == 12
    assert {(s.cycle, s.substep) for s in matrix} == {
        (cycle, substep) for cycle in (20, 60, 82, 83) for substep in (2, 4, 5)
    }
    assert len(event) == 1
    assert (event[0].cycle, event[0].substep, event[0].step) == (85, 4, 424)
