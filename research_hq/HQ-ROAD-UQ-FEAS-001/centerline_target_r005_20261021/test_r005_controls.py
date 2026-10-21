import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OWNER = HERE.parent
RUN = OWNER / "runs" / "HQ-ROAD-CENTERLINE-001-R005"


def launch_state(task_running, process_count, runner_receipt):
    return "LAUNCH_DISPATCHED_VERIFIED" if task_running or process_count or runner_receipt else "LAUNCH_STATE_UNKNOWN_NO_REPEAT"


def main():
    r3 = json.loads((OWNER / "centerline_target_r003_20261021" / "d5_protocol.json").read_text())
    r5 = json.loads((HERE / "d5_protocol.json").read_text())
    science = [
        "experiment_id", "protocol", "claim_class", "seed", "max_epochs", "train_crop", "batch_size",
        "optimizer", "loss", "model", "target", "checkpoint_rule", "evaluation", "decision_rule", "expected",
        "scientific_retry", "road420_access", "new_data_access", "paid_compute",
    ]
    assert {key:r3[key] for key in science} == {key:r5[key] for key in science}
    fingerprint = hashlib.sha256(json.dumps({key:r5[key] for key in science}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert fingerprint == r5["scientific_protocol_fingerprint_sha256"] == "a30121cc43bc1572e946baa56f70a993202076a1fdbf2ca388307cd024e1e83a"
    assert r5["run_id"] == "HQ-ROAD-CENTERLINE-001-R005"
    assert r5["launch_identity"] == "HQ-ROAD-CENTERLINE-001-R005-20261021"
    assert r5["mechanical_rechecks"]["r001_checks_preserved"] == 3
    assert r5["mechanical_rechecks"]["r002_checks_preserved"] == 1
    assert r5["mechanical_rechecks"]["r003_scientific_attempts_preserved"] == 1
    assert r5["mechanical_rechecks"]["r004_checks_preserved"] == 1
    assert r5["mechanical_rechecks"]["r004_scientific_attempts_preserved"] == 0
    assert r5["mechanical_rechecks"]["r005_max_checks"] == 1
    assert r5["package_deadline_utc"] == "2026-10-21T01:59:35Z"

    controller = (HERE / "owned_subprocess.py").read_text()
    for token in ("atomic_write", "os.replace", "duplicate launch prohibited", "taskkill.exe", "killpg", "controller_exit_code", "child_exit_code", "validate_receipt"):
        assert token in controller
    for token in ("CONTEXT_EVIDENCE_INVALID", "SAME_PROCESS", "DIRECT_CHILD_OF_OWNED_LAUNCHER",
                  "scheduled-context process is neither owned PID nor its direct child",
                  "scheduled-context executable mismatch", "scheduled-context argv mismatch",
                  "scheduled-context receipt path mismatch", "scheduled-context timestamp outside owned execution"):
        assert token in controller

    roles = {"environment", "preflight", "admission_child", "scientific_worker"}
    manifests = [json.loads((HERE/f"{role}.invocation.json").read_text()) for role in roles]
    assert {item["role"] for item in manifests} == roles
    outputs = []
    for item in manifests:
        assert item["schema"] == 1 and item["run_id"] == "HQ-ROAD-CENTERLINE-001-R005"
        assert item["approval_path"].endswith(r"HQ-ROAD-CENTERLINE-001-R005\approval_hq.json")
        assert item["lock_path"].endswith(r"centerline_target_r005_20261021\d5_data_lock.json")
        assert "Road420" not in json.dumps(item)
        outputs.extend(item[key] for key in ("receipt_path","exitcode_path","stdout_path","stderr_path"))
    assert len(outputs) == len(set(outputs))

    admission = (HERE / "d5_admission.ps1").read_text()
    assert "Get-OwnedReceipt" in admission
    assert "& $python $controller $environmentInvocation" in admission
    assert "& $python $controller $preflightInvocation" in admission
    assert "$environmentProcess.ExitCode" not in admission and "$preflightProcess.ExitCode" not in admission
    assert "Get-RequiredInteger" in admission
    assert "r002_checks_preserved = 1" in admission
    assert "r003_scientific_attempts_preserved = 1" in admission
    assert "r004_admission_checks_preserved = 1" in admission
    assert "r004_scientific_attempts_preserved = 0" in admission
    assert "PASS_SCHEDULED_CONTEXT" in admission
    assert "context_ownership -notin @('SAME_PROCESS','DIRECT_CHILD_OF_OWNED_LAUNCHER')" in admission

    wrapper = (HERE / "invoke_d5_admission_once.ps1").read_text()
    assert "WaitForExit(86000)" in wrapper
    assert "owned_control_receipt" in wrapper
    assert "$process.ExitCode" not in wrapper
    assert "Get-RequiredInteger" in wrapper
    assert "second R005 check prohibited" in wrapper

    launch = (RUN / "launch_gpu_server.cmd").read_text()
    assert "owned_subprocess.py scientific_worker.invocation.json" in launch
    assert "PYTHONWARNINGS" not in launch and "Road420" not in launch
    bootstrap = (HERE / "scheduled_context_bootstrap.py").read_text()
    for token in ("sys.path[:]", "find_spec", "PASS_SCHEDULED_CONTEXT", "runpy.run_path", "expected-skimage-sha256"):
        assert token in bootstrap
    for item in manifests:
        if item["role"] in {"environment", "preflight", "scientific_worker"}:
            assert any("scheduled_context_bootstrap.py" in arg for arg in item["command"])
    register = (RUN / "register_and_start.ps1").read_text()
    assert "New-ScheduledTaskTrigger" not in register
    assert "scientific-worker evidence already exists; repeat dispatch prohibited" in register
    assert "scientific-worker exclusive claim already exists; repeat dispatch prohibited" in register
    assert "Get-RequiredInteger" in register
    assert "LAUNCH_STATE_UNKNOWN_NO_REPEAT" in register
    assert "registered task principal mismatch; scientific task not started" in register
    assert register.index("registered task principal mismatch") < register.index("Start-ScheduledTask")
    assert launch_state(False, 0, False) == "LAUNCH_STATE_UNKNOWN_NO_REPEAT"
    assert launch_state(True, 0, False) == "LAUNCH_DISPATCHED_VERIFIED"
    print("PASS_R005_CONTROL_DELTA", fingerprint)


if __name__ == "__main__":
    main()
