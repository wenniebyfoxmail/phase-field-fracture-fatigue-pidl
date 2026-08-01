from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "producer_handoffs" / "toy_to_road_independent_fem_20260731"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_source_manifest(repo: Path, relative_paths: list[str]) -> None:
    handoff = repo / "producer_handoffs" / "toy_to_road_independent_fem_20260731"
    lines = [f"{sha256(repo / relative)}  {relative}" for relative in relative_paths]
    (handoff / "SHA256SUMS.txt").write_bytes(("\n".join(sorted(lines)) + "\n").encode())


def build_launcher_fixture(tmp_path: Path) -> dict:
    repo = tmp_path / "shared"
    handoff = repo / "producer_handoffs" / "toy_to_road_independent_fem_20260731"
    handoff.mkdir(parents=True)
    shutil.copy2(HANDOFF / "launch_toy_road_case.ps1", handoff)
    (handoff / "README.md").write_text("fixture\n", newline="\n")
    parent_lock = handoff / "PARENT_LOCK.json"
    parent_lock.write_text('{"schema_version":"fixture_parent"}\n', newline="\n")
    parent_hash = sha256(parent_lock)
    case_lock = handoff / "T1_INPUT_LOCK.json"
    case_lock.write_text(
        json.dumps(
            {
                "case_id": "T1_initial_defect",
                "parent_lock_sha256": parent_hash,
            },
            separators=(",", ":"),
        )
        + "\n",
        newline="\n",
    )
    source_paths = [
        "producer_handoffs/toy_to_road_independent_fem_20260731/PARENT_LOCK.json",
        "producer_handoffs/toy_to_road_independent_fem_20260731/README.md",
        "producer_handoffs/toy_to_road_independent_fem_20260731/T1_INPUT_LOCK.json",
        "producer_handoffs/toy_to_road_independent_fem_20260731/launch_toy_road_case.ps1",
    ]
    write_source_manifest(repo, source_paths)
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "fixture@example.invalid")
    run_git(repo, "config", "user.name", "Fixture")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "fixture")

    grip = tmp_path / "grip"
    grip.mkdir()
    (grip / "source.m").write_text("fixture source\n", newline="\n")
    (grip / "runtime.mexw64").write_bytes(b"fixture runtime")
    run_git(grip, "init")
    run_git(grip, "config", "user.email", "fixture@example.invalid")
    run_git(grip, "config", "user.name", "Fixture")
    run_git(grip, "add", ".")
    run_git(grip, "commit", "-m", "fixture")

    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / "parent.bin").write_bytes(b"fixture parent")
    output = tmp_path / "output"
    output.mkdir()
    fixture_path = tmp_path / "preflight-fixture.json"
    fixture = {
        "expected_gripfith_commit": run_git(grip, "rev-parse", "HEAD"),
        "gripfith_sources": [
            {"path": "source.m", "sha256": sha256(grip / "source.m")}
        ],
        "runtime_files": [
            {
                "path": str(grip / "runtime.mexw64"),
                "sha256": sha256(grip / "runtime.mexw64"),
            }
        ],
        "parent_files": [
            {"path": "parent.bin", "sha256": sha256(parent / "parent.bin")}
        ],
        "process_inventory": [],
        "force_hardlink_failure": False,
        "required_source_paths": source_paths,
    }
    fixture_path.write_text(json.dumps(fixture), newline="\n")
    return {
        "repo": repo,
        "handoff": handoff,
        "grip": grip,
        "parent": parent,
        "output": output,
        "fixture": fixture,
        "fixture_path": fixture_path,
        "source_paths": source_paths,
        "expected_commit": run_git(repo, "rev-parse", "HEAD"),
    }


def run_launcher(
    fixture: dict,
    *,
    env: dict[str, str] | None = None,
    case_id: str = "T1_initial_defect",
    validate_run_result: Path | None = None,
) -> subprocess.CompletedProcess:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(fixture["handoff"] / "launch_toy_road_case.ps1"),
        "-SharedRepo",
        str(fixture["repo"]),
        "-GripfithRoot",
        str(fixture["grip"]),
        "-ParentRoot",
        str(fixture["parent"]),
        "-OutputParent",
        str(fixture["output"]),
        "-CaseId",
        case_id,
        "-ExpectedSourceCommit",
        fixture["expected_commit"],
        "-PreflightOnly",
        "-TestFixturePath",
        str(fixture["fixture_path"]),
    ]
    if validate_run_result is not None:
        command.extend(["-ValidateRunResultPath", str(validate_run_result)])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_parent_lock_is_latest_c83_c86_baseline() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert lock["parent_reference_id"] == "hard5_eta0_u012_5step_20260729"
    assert lock["event"] == {"first_hit": 83, "confirmed": 86}
    assert lock["physics"]["eta"] == 0.0
    assert lock["physics"]["n_substeps"] == 5
    assert lock["mesh"]["num_elem"] == 86408
    assert lock["mesh"]["num_nodes"] == 86756
    assert lock["state_semantics_id"] == "cycle_peak_coherent_v1"


def test_parent_lock_distinguishes_legacy_and_task4_mesh_hash_semantics() -> None:
    mesh = load_json(HANDOFF / "PARENT_LOCK.json")["mesh"]
    assert mesh["content_sha256"] == (
        "7ea77bf6d4621d746f174eb9c357c4bc554463eea8afb8665b00e918bcd937ab"
    )
    assert mesh["content_sha256_semantics"] == (
        "analysis_graph_npz_centroids_areas_connectivity_edge_index_v1"
    )
    assert mesh["source_sha256_semantics"] == "raw_analysis_graph_npz_bytes"
    assert mesh["source_package_evidence_sha256_semantics"] == (
        "normalized_ascii_vtk_geometry_topology_v1"
    )
    assert mesh["source_package_evidence_source_sha256"] == (
        "acdc981269024cbb111f7d468c287f2d1ca09f3735131b56aca7fa2fbaec1615"
    )
    assert mesh["task4_parent_mesh_sha256"] == (
        "4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af"
    )
    assert mesh["task4_parent_mesh_sha256_semantics"] == (
        "sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1"
    )
    evidence = mesh["task4_parent_mesh_evidence"]
    assert evidence["relative_path"] == (
        "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/peak_load_c1.vtk"
    )
    assert evidence["source_sha256"] == mesh["source_package_evidence_source_sha256"]


def test_parent_lock_keeps_physical_source_and_analysis_bundle_authoritative() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert (
        lock["physical_source_package_id"]
        == "Hard5_eta0_5step_Umax_011_012_013_20260729"
    )
    assert lock["physical_source_role"] == "consumed_physical_bytes_and_windows_paths"
    analysis_bundle = lock["authoritative_analysis_bundle"]
    assert analysis_bundle["role"] == "consumed_mac_analysis_bundle_contract"
    assert analysis_bundle["bundle_id"] == "bundle::hard5_eta0_u012_5step_20260729"
    assert (
        analysis_bundle["package_id"]
        == "Hard5_eta0_5step_Umax_0.12_20260729"
    )
    assert (
        analysis_bundle["bundle_manifest_sha256"]
        == "ce36913ed75bbf2830a3016c442953317d6e968eff074e73c988704dbec118b3"
    )
    assert "non_authoritative_logical_mac_bundle_alias" not in lock


def test_parent_lock_prohibits_road_sensor_claims_and_network_training() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    policy = lock["immutable_policy"]
    assert not policy["latent_fem_fields_are_direct_road_sensors"]
    assert not policy["pidl_network_training_authorized"]
    assert policy["claim_scope"] == "synthetic_whole_trajectory_loto_only"
    assert not policy["road_validation_authorized"]


@pytest.mark.parametrize(
    ("name", "axis"),
    [
        ("T1_INPUT_LOCK.json", "initial_defect"),
        ("T2_INPUT_LOCK.json", "material_state"),
        ("T3_INPUT_LOCK.json", "loading_history"),
    ],
)
def test_case_lock_declares_exactly_one_primary_axis(name: str, axis: str) -> None:
    lock = load_json(HANDOFF / name)
    assert lock["primary_variation_axis"] == axis
    assert lock["changed_parent_fields"] == lock["allowed_changed_parent_fields"]
    assert lock["censor_cap"] == 150


def test_t1_lock_fixes_the_initial_defect_tip() -> None:
    lock = load_json(HANDOFF / "T1_INPUT_LOCK.json")
    initial_defect = lock["candidate"]["initial_defect"]
    parent_initial_defect = lock["parent_candidate_diff"]["parent"]["initial_defect"]
    assert initial_defect["tip"] == [0.125, 0.0]
    assert initial_defect["a0_over_L"] == 0.625
    assert parent_initial_defect["a0_over_L"] == 0.5


def test_family_axis_baselines_are_the_approved_parent_values() -> None:
    family = load_json(HANDOFF / "FAMILY_INPUT_LOCK.json")
    assert family["axis_baselines"] == {
        "initial_defect": {"tip": [0.0, 0.0], "a0_over_L": 0.5},
        "material_state": {"Gc": 0.01, "Pi_ratio": 1.0},
        "loading_history": {"blocks": [[1, 150, 0.12]]},
    }


def test_t2_lock_fixes_material_state_values() -> None:
    lock = load_json(HANDOFF / "T2_INPUT_LOCK.json")
    material_state = lock["candidate"]["material_state"]
    assert material_state["Gc"] == 0.008
    assert material_state["Pi_ratio"] == 0.8


def test_t3_lock_fixes_loading_blocks() -> None:
    lock = load_json(HANDOFF / "T3_INPUT_LOCK.json")
    assert lock["candidate"]["loading_history"]["blocks"] == [
        [1, 30, 0.108],
        [31, 60, 0.126],
        [61, 150, 0.120],
    ]


def save_launcher_fixture(fixture: dict) -> None:
    fixture["fixture_path"].write_text(json.dumps(fixture["fixture"]), newline="\n")


def test_launcher_preflight_is_single_case_and_cannot_invoke_matlab(tmp_path: Path) -> None:
    fixture = build_launcher_fixture(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    sentinel = tmp_path / "matlab-was-invoked"
    (fake_bin / "matlab.cmd").write_text(
        f'@echo invoked>"{sentinel}"\n', newline="\r\n"
    )
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]

    result = run_launcher(fixture, env=env)

    assert result.returncode == 0, result.stderr + result.stdout
    assert not sentinel.exists()
    assert not (fixture["output"] / "T1_initial_defect").exists()
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt == {
        "TOY_ROAD_CASE_ID": "T1_initial_defect",
        "TOY_ROAD_LOCK_SHA256": sha256(fixture["handoff"] / "T1_INPUT_LOCK.json"),
        "TOY_ROAD_OUTPUT_ROOT": str(fixture["output"] / "T1_initial_defect"),
        "TOY_ROAD_SOURCE_COMMIT": fixture["expected_commit"],
    }


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("dirty_shared", "Shared repo is dirty"),
        ("wrong_shared_commit", "exact sealed source commit"),
        ("source_hash", "Source SHA256 mismatch"),
        ("wrong_lock_hash", "parent lock SHA-256"),
        ("wrong_grip_commit", "GRIPHFiTH commit"),
        ("dirty_grip", "GRIPHFiTH producer repo is dirty"),
        ("grip_source_hash", "GRIPHFiTH source SHA256 mismatch"),
        ("runtime_hash", "Runtime MEX/SuiteSparse/CHOLMOD SHA256 mismatch"),
        ("parent_hash", "Parent SHA256 mismatch"),
        ("running_matlab", "running MATLAB/FEM"),
        ("hardlink", "hard-link preflight"),
    ],
)
def test_launcher_preflight_fails_closed(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    fixture = build_launcher_fixture(tmp_path)
    if mutation == "dirty_shared":
        (fixture["handoff"] / "README.md").write_text("dirty\n", newline="\n")
    elif mutation == "wrong_shared_commit":
        fixture["expected_commit"] = "0" * 40
    elif mutation == "source_hash":
        readme = fixture["handoff"] / "README.md"
        readme.write_text("tampered but committed\n", newline="\n")
        run_git(fixture["repo"], "add", ".")
        run_git(fixture["repo"], "commit", "-m", "tamper source")
        fixture["expected_commit"] = run_git(fixture["repo"], "rev-parse", "HEAD")
    elif mutation == "wrong_lock_hash":
        case_lock = fixture["handoff"] / "T1_INPUT_LOCK.json"
        data = load_json(case_lock)
        data["parent_lock_sha256"] = "0" * 64
        case_lock.write_text(json.dumps(data, separators=(",", ":")) + "\n", newline="\n")
        write_source_manifest(fixture["repo"], fixture["source_paths"])
        run_git(fixture["repo"], "add", ".")
        run_git(fixture["repo"], "commit", "-m", "bad lock")
        fixture["expected_commit"] = run_git(fixture["repo"], "rev-parse", "HEAD")
    elif mutation == "wrong_grip_commit":
        (fixture["grip"] / "other.m").write_text("new commit\n", newline="\n")
        run_git(fixture["grip"], "add", ".")
        run_git(fixture["grip"], "commit", "-m", "move grip")
    elif mutation == "dirty_grip":
        (fixture["grip"] / "source.m").write_text("dirty source\n", newline="\n")
    elif mutation == "grip_source_hash":
        (fixture["grip"] / "source.m").write_text("mutated source\n", newline="\n")
        run_git(fixture["grip"], "add", ".")
        run_git(fixture["grip"], "commit", "-m", "mutate source")
        fixture["fixture"]["expected_gripfith_commit"] = run_git(
            fixture["grip"], "rev-parse", "HEAD"
        )
        save_launcher_fixture(fixture)
    elif mutation == "runtime_hash":
        (fixture["grip"] / "runtime.mexw64").write_bytes(b"mutated runtime")
        run_git(fixture["grip"], "add", ".")
        run_git(fixture["grip"], "commit", "-m", "mutate runtime")
        fixture["fixture"]["expected_gripfith_commit"] = run_git(
            fixture["grip"], "rev-parse", "HEAD"
        )
        save_launcher_fixture(fixture)
    elif mutation == "parent_hash":
        (fixture["parent"] / "parent.bin").write_bytes(b"tampered parent")
    elif mutation == "running_matlab":
        fixture["fixture"]["process_inventory"] = [
            {"name": "MATLAB.exe", "process_id": 4242, "command_line": "matlab -batch solve"}
        ]
        save_launcher_fixture(fixture)
    elif mutation == "hardlink":
        fixture["fixture"]["force_hardlink_failure"] = True
        save_launcher_fixture(fixture)

    result = run_launcher(fixture)

    assert result.returncode != 0
    assert expected.lower() in (result.stderr + result.stdout).lower()
    assert not (fixture["output"] / "T1_initial_defect").exists()


def test_launcher_refuses_existing_output_and_resume_input(tmp_path: Path) -> None:
    fixture = build_launcher_fixture(tmp_path / "existing")
    (fixture["output"] / "T1_initial_defect").mkdir()
    existing = run_launcher(fixture)
    assert existing.returncode != 0
    assert "Refusing to overwrite" in existing.stderr + existing.stdout

    resume_fixture = build_launcher_fixture(tmp_path / "resume")
    env = os.environ.copy()
    env["TOY_ROAD_RESUME"] = "checkpoint.mat"
    resume = run_launcher(resume_fixture, env=env)
    assert resume.returncode != 0
    assert "checkpoint/resume" in (resume.stderr + resume.stdout).lower()


def test_launcher_rejects_case_id_with_wrong_case(tmp_path: Path) -> None:
    fixture = build_launcher_fixture(tmp_path)
    result = run_launcher(fixture, case_id="t1_initial_defect")
    assert result.returncode != 0
    assert "ParameterArgumentValidationError" in (result.stderr + result.stdout)
    assert not (fixture["output"] / "t1_initial_defect").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        {"complete": "false"},
        {"complete": False},
        {"terminal_reason": "failed"},
        {"terminal_cycle": 0},
        {"terminal_cycle": 151},
        {"terminal_cycle": 1.5},
        {"case_id": "T2_material_state"},
        {"terminal_state_file": "states/cycle_9999.mat"},
    ],
)
def test_launcher_strictly_rejects_malformed_completion_before_matlab(
    tmp_path: Path, mutation: dict
) -> None:
    fixture = build_launcher_fixture(tmp_path)
    run_result = {
        "case_id": "T1_initial_defect",
        "complete": True,
        "status": "complete",
        "terminal_cycle": 4,
        "terminal_reason": "confirmed",
        "terminal_state_file": "states/cycle_0004.mat",
    }
    run_result.update(mutation)
    run_result_path = tmp_path / "RUN_RESULT.json"
    run_result_path.write_text(json.dumps(run_result), newline="\n")
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    sentinel = tmp_path / "matlab-was-invoked"
    (fake_bin / "matlab.cmd").write_text(
        f'@echo invoked>"{sentinel}"\n', newline="\r\n"
    )
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]

    result = run_launcher(
        fixture, env=env, validate_run_result=run_result_path
    )

    assert result.returncode != 0
    assert "RUN_RESULT.json" in (result.stderr + result.stdout)
    assert not sentinel.exists()


def test_launcher_validates_complete_result_without_invoking_matlab(tmp_path: Path) -> None:
    fixture = build_launcher_fixture(tmp_path)
    run_result_path = tmp_path / "RUN_RESULT.json"
    run_result_path.write_text(
        json.dumps(
            {
                "case_id": "T1_initial_defect",
                "complete": True,
                "status": "complete",
                "terminal_cycle": 4,
                "terminal_reason": "confirmed",
                "terminal_state_file": "states/cycle_0004.mat",
            }
        ),
        newline="\n",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    sentinel = tmp_path / "matlab-was-invoked"
    (fake_bin / "matlab.cmd").write_text(
        f'@echo invoked>"{sentinel}"\n', newline="\r\n"
    )
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]

    result = run_launcher(
        fixture, env=env, validate_run_result=run_result_path
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert not sentinel.exists()


def test_launcher_uses_no_clobber_launch_receipt_protocol() -> None:
    text = (HANDOFF / "launch_toy_road_case.ps1").read_text()
    assert "LAUNCH_RECEIPT.json" in text
    assert "[IO.FileMode]::CreateNew" in text
    assert "source_hashes" in text
    assert "finalize_toy_road_package" in text


def test_readme_fixes_scope_and_completion_contract() -> None:
    text = " ".join((HANDOFF / "README.md").read_text().split())
    required = [
        "three independent single-axis synthetic FEM trajectories",
        "strict serial execution",
        "no resume",
        "c150",
        "latent FEM fields",
        "no PIDL training",
        "no road validation",
        "F1b",
        "separate blocked diagnostic",
        "must not pre-exist",
        "RUN_RESULT.json",
        "sole completion marker",
        "LAUNCH_RECEIPT.json",
        "commit receipt protocol",
        "mesh.content_sha256",
        "not the Task 4 mesh hash",
        "4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af",
    ]
    for phrase in required:
        assert phrase.lower() in text.lower()


def test_finalizer_production_defaults_use_real_parent_mesh_lock() -> None:
    text = (HANDOFF / "finalize_toy_road_package.m").read_text()
    assert "localLoadParentMeshContract(parentLock, dependencies)" in text
    assert "mesh.num_nodes == 86756" in text
    assert "mesh.num_elem == 86408" in text
    assert "4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af" in text
    launcher = (HANDOFF / "launch_toy_road_case.ps1").read_text()
    assert "toy_road_finalizer_test_dependencies_v1" not in launcher


def test_source_manifest_covers_exact_source_bytes_once() -> None:
    manifest = HANDOFF / "SHA256SUMS.txt"
    entries = [line.split("  ", 1) for line in manifest.read_text().splitlines() if line]
    paths = [relative for _, relative in entries]
    expected = {
        path.relative_to(ROOT).as_posix() for path in HANDOFF.rglob("*.m")
    }
    expected.update(
        path.relative_to(ROOT).as_posix() for path in HANDOFF.glob("*_LOCK.json")
    )
    expected.update(
        {
            (HANDOFF / "README.md").relative_to(ROOT).as_posix(),
            (HANDOFF / "launch_toy_road_case.ps1").relative_to(ROOT).as_posix(),
            Path(__file__).resolve().relative_to(ROOT).as_posix(),
        }
    )
    assert paths == sorted(expected)
    assert len(paths) == len({path.casefold() for path in paths})
    assert "SHA256SUMS.txt" not in "\n".join(paths)
    for expected_hash, relative in entries:
        assert expected_hash == sha256(ROOT / relative)


def test_source_manifest_verifies_in_fresh_byte_preserving_copy(tmp_path: Path) -> None:
    entries = [
        line.split("  ", 1)
        for line in (HANDOFF / "SHA256SUMS.txt").read_text().splitlines()
        if line
    ]
    fresh = tmp_path / "fresh"
    for expected_hash, relative in entries:
        destination = fresh / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
        assert sha256(destination) == expected_hash
