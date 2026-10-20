import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = HERE.parent
RUN = OWNER / "runs" / "HQ-ROAD-CENTERLINE-001-R002"


def main():
    r1 = json.loads((OWNER / "centerline_target_20261020" / "d5_protocol.json").read_text())
    r2 = json.loads((HERE / "d5_protocol.json").read_text())
    science = [
        "experiment_id", "protocol", "claim_class", "seed", "max_epochs", "train_crop", "batch_size",
        "optimizer", "loss", "model", "target", "checkpoint_rule", "evaluation", "decision_rule", "expected",
        "scientific_retry", "road420_access", "new_data_access", "paid_compute",
    ]
    a = {key: r1[key] for key in science}
    b = {key: r2[key] for key in science}
    assert a == b
    fingerprint = hashlib.sha256(json.dumps(a, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert fingerprint == r2["scientific_protocol_fingerprint_sha256"]
    assert r2["run_id"] == "HQ-ROAD-CENTERLINE-001-R002"
    assert r2["mechanical_rechecks"]["r001_checks_preserved"] == 3
    assert r2["mechanical_rechecks"]["r002_max_checks"] == 1
    assert r2["mechanical_rechecks"]["r002_check_seconds"] == 90
    assert r2["minimum_launch_remaining_seconds"] == 1900
    assert r2["package_clock_start_utc"] == "2026-10-20T21:59:35Z"
    assert r2["package_deadline_utc"] == "2026-10-21T01:59:35Z"

    lock = json.loads((HERE / "d5_data_lock.json").read_text())
    assert lock["status"] == "FROZEN_FOR_HQ-ROAD-CENTERLINE-001-R002"
    assert lock["parent_r001_data_lock_sha256"] == "563cf2fc1410a5872086f96c9769faeaaf2d4b14e137eba52665e8d3f29c122e"
    assert lock["road420_accessed"] is False

    admission = (HERE / "d5_admission.ps1").read_text()
    for required in (
        "Test-KnownDesktopBackground", "gpu_query_raw", "gpu_compute_rows_raw", "aggregate_free_mib",
        "actual_gpu_uuid", "KNOWN_DESKTOP_BACKGROUND_NA_MEMORY", "UNKNOWN_OR_COMPETING_COMPUTE_PROCESS",
        "classification_fixture", "R002 admission receipt already exists; second R002 check prohibited",
        "original package clock cannot fit complete run", "launch receipt already exists", "$process -and",
        "observed_executable_path", "gpu_query_exit_code", "gpu_compute_query_exit_code",
    ):
        assert required in admission
    assert "if ($computeLines.Count -gt 0)" not in admission
    assert "Stop-Process" in admission  # only the owned, bounded probe children
    assert "taskkill" not in admission

    wrapper = (HERE / "invoke_d5_admission_once.ps1").read_text()
    assert "WaitForExit(83000)" in wrapper
    assert "check_limit_seconds = 90" in wrapper
    assert "r002_check_cap = 1" in wrapper
    assert "second R002 check prohibited" in wrapper

    register = (RUN / "register_and_start.ps1").read_text()
    assert "New-ScheduledTaskTrigger" not in register
    assert "New-ScheduledTaskAction" in register
    assert "New-TimeSpan -Seconds" in register
    assert "taskLimitSafetySeconds = 120" in register
    assert "package-clock/GPU binding mismatch" in register
    assert "LAUNCH_STATE_UNKNOWN_NO_REPEAT" in register
    assert "launch receipt already exists; repeat dispatch prohibited" in register

    launch = (RUN / "launch_gpu_server.cmd").read_text()
    assert "PYTHONWARNINGS" not in launch
    assert "HQ-ROAD-CENTERLINE-001-R002" in launch
    assert "HQ-ROAD-UQ-FEAS-001-R001\\best.pt" in launch
    assert "HQ-ROAD-UQ-FEAS-002-R001\\best.pt" in launch
    assert "Road420" not in launch
    print("PASS_R002_CONTROL_DELTA", fingerprint)


if __name__ == "__main__":
    main()
