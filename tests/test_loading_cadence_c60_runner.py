from pathlib import Path

from SENS_tensile.run_loading_cadence_c60_seed1 import (
    N_CYCLES,
    SEED,
    common_command,
    cycle_csv,
)


def test_c60_runner_command_is_locked() -> None:
    command = common_command(Path("runner.py"), "archive")
    assert N_CYCLES == 60
    assert SEED == 1
    assert command[command.index("--n-cycles-physical") + 1] == "60"
    assert command[command.index("--seed") + 1] == "1"
    assert command[command.index("--diag-physical-cycles") + 1] == cycle_csv()
    assert command[command.index("--diag-full-physical-cycles") + 1] == cycle_csv()
    assert command[command.index("--fixed-horizon")] == "--fixed-horizon"
    assert "--epochs-rprop" not in command
    assert "--epochs-lbfgs" not in command


def test_c60_cycle_list_is_complete_and_ordered() -> None:
    assert cycle_csv().split(",") == [str(value) for value in range(1, 61)]
