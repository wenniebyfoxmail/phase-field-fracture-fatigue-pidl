from __future__ import annotations

import csv
import json
import importlib.util
import hashlib
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import h5py
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis" / "toy_road_t3_rev_20260824"
REGISTRY = ROOT / "docs/toy_road_p0_repeatability_20260802/QUALIFIED_TRAJECTORY_REGISTRY_20260824.json"
BASE = ROOT / "producer_handoffs/toy_road_p0_repeatability_20260803"


def repository_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def load_module(name: str):
    path = ROOT / "analysis/toy_road_t3_rev_20260824" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def seal_marker(module, seal_path: Path) -> Path:
    return module.seal_consumption_marker(hashlib.sha256(seal_path.read_bytes()).hexdigest())


def load_registry(path: Path) -> dict[str, object]:
    return strict_json(path)


def test_t3_review_and_trajectory_registry_are_non_authorizing() -> None:
    receipt = (ROOT / "docs/toy_road_p0_repeatability_20260802/"
               "t3_loading_history_20260818/"
               "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md").read_text()
    registry = strict_json(REGISTRY)
    assert "PASS, with one provenance-layer discrepancy disclosed" in receipt
    assert "97/97" in receipt and "2,960,514,298" in receipt
    assert "LOCAL_MIRROR_NOT_YET_BUILT" in receipt
    assert "ONEDRIVE_UPLOAD_VERIFIED" in receipt
    assert registry["authorization_capability"] is None
    assert registry["trajectories"]["P0_parent"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T1_initial_defect"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T3_loading_history"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T2_material_state"]["status"] == \
        "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"


def test_extension_adds_only_t3_rev_and_preserves_base(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    before = module.inventory_tree(BASE)
    result = module.build_extension(BASE, tmp_path / "extension", "a" * 40)
    after = module.inventory_tree(BASE)
    assert before == after
    assert result["case_id"] == "T3_rev_loading_order"
    assert result["loading_blocks"] == [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.120]]
    assert result["base_source_manifest_sha256"] == \
        "61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e"
    assert set(result["changed_source_files"]) == set(module.ALLOWED_SHADOW_FILES)
    assert {
        path.relative_to(tmp_path / "extension").as_posix()
        for path in (tmp_path / "extension").rglob("*")
        if path.is_file()
    } == {
        *module.ALLOWED_SHADOW_FILES,
        "EXTENSION_SOURCE_MANIFEST.json",
        "SOURCE_DIFF_INVENTORY.json",
    }


def test_extension_rejects_duplicate_json_and_unexpected_base_text(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    bad = tmp_path / "base"
    shutil.copytree(BASE, bad)
    path = bad / "build_toy_road_family_case.m"
    path.write_text(path.read_text().replace("T3_loading_history", "T3_changed", 1))
    with pytest.raises(module.ExtensionError, match="base source identity|exact patch count"):
        module.build_extension(bad, tmp_path / "extension", "a" * 40)


@pytest.mark.parametrize("bad_payload", [
    '{"case_id":"T3_rev_loading_order","case_id":"duplicate"}',
    '{"loading_blocks":NaN}',
    '{"resume_allowed":0}',
])
def test_extension_contract_rejects_noncanonical_json(tmp_path: Path, bad_payload: str) -> None:
    module = load_module("build_t3_rev_extension")
    path = tmp_path / "bad.json"
    path.write_text(bad_payload)
    with pytest.raises(module.ExtensionError):
        module.read_strict_contract(path)


@pytest.mark.parametrize(("field", "value", "error"), [
    ("follow_on_authorized", 0, "follow_on_authorized must be a JSON boolean"),
    ("resume_allowed", 0, "resume_allowed must be a JSON boolean"),
    ("loading_blocks", [[1.0, 30, 0.126], [31, 60, 0.108], [61, 150, 0.12]],
     "loading_blocks\\[0\\]\\[0\\] must be a JSON integer"),
])
def test_extension_contract_rejects_complete_type_confusion(
        tmp_path: Path, field: str, value: object, error: str) -> None:
    module = load_module("build_t3_rev_extension")
    contract = json.loads(
        (ROOT / "analysis/toy_road_t3_rev_20260824/T3_REV_CONTRACT.json").read_text()
    )
    contract[field] = value
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))
    with pytest.raises(module.ExtensionError, match=error):
        module.read_strict_contract(path)


def test_diff_verifier_rejects_fixed_point_threshold_change(tmp_path: Path) -> None:
    """A numerical solver change cannot be presented as a T3-rev overlay."""
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, "a" * 40)
    solver = extension / "solve_toy_road_family_case.m"
    solver.write_text(solver.read_text(encoding="utf-8").replace("1e-3", "2e-3", 1),
                      encoding="utf-8")

    with pytest.raises(verify.DiffError, match="unclassified|numerical"):
        verify.verify_extension_diff(BASE, extension)


def test_diff_verifier_accepts_exact_generated_extension(tmp_path: Path) -> None:
    """The generated T3-rev overlay leaves all numerical dependencies unchanged."""
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, repository_head())

    result = verify.verify_extension_diff(BASE, extension)

    assert result == {
        "status": "PASS",
        "numerical_algorithm_changed": False,
        "allowed_shadow_files": list(builder.ALLOWED_SHADOW_FILES),
    }


@pytest.mark.parametrize(("field", "value"), [
    ("schema_version", "tampered_schema"),
    ("case_id", "P0_parent"),
    ("repo_commit", "75eaf67ada8b3629142a85a51bc06779e557b619"),
    ("base_source_commit", "0" * 40),
    ("base_source_manifest_sha256", "0" * 64),
    ("contract_sha256", "0" * 64),
    ("source_diff_inventory_sha256", "0" * 64),
])
def test_diff_verifier_rejects_tampered_manifest_claim(
        tmp_path: Path, field: str, value: str) -> None:
    """Every manifest identity claim must independently bind the overlay."""
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, repository_head())
    path = extension / "EXTENSION_SOURCE_MANIFEST.json"
    manifest = strict_json(path)
    manifest[field] = value
    path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    with pytest.raises(verify.DiffError):
        verify.verify_extension_diff(BASE, extension)


def test_diff_verifier_rejects_tampered_shadow_hash(tmp_path: Path) -> None:
    """The manifest must bind each generated shadow to its actual bytes."""
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, repository_head())
    path = extension / "EXTENSION_SOURCE_MANIFEST.json"
    manifest = strict_json(path)
    shadow_files = manifest["shadow_files"]
    assert isinstance(shadow_files, list)
    shadow_files[0]["sha256"] = "0" * 64
    path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    with pytest.raises(verify.DiffError):
        verify.verify_extension_diff(BASE, extension)


def test_diff_verifier_rejects_tampered_hunk_inventory(tmp_path: Path) -> None:
    """The hunk inventory must describe the exact generated source changes."""
    builder = load_module("build_t3_rev_extension")
    verify = load_module("verify_extension_diff")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, repository_head())
    path = extension / "SOURCE_DIFF_INVENTORY.json"
    inventory = strict_json(path)
    hunks = inventory["hunks"]
    assert isinstance(hunks, list)
    hunks[0]["classification"] = "role_allowlist"
    path.write_text(json.dumps(inventory, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    with pytest.raises(verify.DiffError):
        verify.verify_extension_diff(BASE, extension)


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def build_test_seal(
        tmp_path: Path, *, injected_review_authorization: bool = False,
        destination: Path | None = None, t3_adjudication: Path | None = None) -> dict[str, object]:
    """Build a real seal from a clean miniature repository and generated overlay."""
    builder = load_module("build_t3_rev_extension")
    seal_builder = load_module("build_t3_rev_seal")
    repo = tmp_path / "repo"
    base = repo / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    terminal = repo / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence"
    shutil.copytree(BASE, base)
    terminal.mkdir(parents=True)
    shutil.copy2(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/TERMINAL_MANIFEST.json",
        terminal / "TERMINAL_MANIFEST.json",
    )
    shutil.copy2(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
        "T3_SIBLING_TERMINAL_ADJUDICATION.json",
        terminal / "T3_SIBLING_TERMINAL_ADJUDICATION.json",
    )
    predecessor_docs = repo / "docs" / "toy_road_p0_repeatability_20260802"
    review = predecessor_docs / "t3_loading_history_20260818" / \
        "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md"
    review.parent.mkdir(parents=True)
    shutil.copy2(
        ROOT / "docs/toy_road_p0_repeatability_20260802/t3_loading_history_20260818/"
        "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md",
        review,
    )
    registry = predecessor_docs / "QUALIFIED_TRAJECTORY_REGISTRY_20260824.json"
    shutil.copy2(REGISTRY, registry)
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "test@example.invalid"], repo)
    _git(["config", "user.name", "Seal Test"], repo)
    _git(["add", "."], repo)
    _git(["commit", "-qm", "test fixture"], repo)
    commit = _git(["rev-parse", "HEAD"], repo)
    extension = tmp_path / "extension"
    builder.build_extension(base, extension, commit)

    review = tmp_path / "T3_INDEPENDENT_REVIEW_RECEIPT.md"
    receipt = (ROOT / "docs/toy_road_p0_repeatability_20260802/"
               "t3_loading_history_20260818/"
               "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md").read_text(encoding="utf-8")
    if injected_review_authorization:
        receipt = receipt.replace("This receipt is non-authorizing.",
                                  "This receipt is authorizing.")
    review.write_text(receipt, encoding="utf-8")
    return seal_builder.build_seal(
        repo, extension,
        t3_adjudication or ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
        "T3_SIBLING_TERMINAL_ADJUDICATION.json",
        review, REGISTRY, destination or tmp_path / "seal",
    )


def test_seal_binds_extension_and_exactly_one_case(tmp_path: Path) -> None:
    """A valid, verified composite producer receives one non-reusable capability."""
    seal = build_test_seal(tmp_path)
    assert seal["case_id"] == "T3_rev_loading_order"
    assert seal["authorization_capability"] == "exactly_one_T3_rev_loading_order_execution"
    assert seal["resume_allowed"] is False
    assert seal["follow_on_authorized"] is False
    extension_identity = seal["extension_identity"]
    assert isinstance(extension_identity, dict)
    assert extension_identity["base_source_commit"] == "7c56ff383187cdee2f45e1b15d707f148f386302"
    assert extension_identity["verification"]["status"] == "PASS"
    physics = seal["physics_closure"]
    assert isinstance(physics, dict)
    assert physics["only_loading_blocks_differ"] is True
    assert physics["first_60_histogram_equal_to_t3"] is True


def test_seal_rejects_authorizing_review_receipt(tmp_path: Path) -> None:
    """The archived review is evidence only and cannot grant execution capability."""
    with pytest.raises(RuntimeError, match="review receipt is non-authorizing"):
        build_test_seal(tmp_path, injected_review_authorization=True)


def test_seal_rejects_tampered_extension_manifest(tmp_path: Path) -> None:
    """A mutable manifest claim cannot replace authoritative overlay verification."""
    builder = load_module("build_t3_rev_extension")
    seal_builder = load_module("build_t3_rev_seal")
    repo = tmp_path / "repo"
    base = repo / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    terminal = repo / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence"
    shutil.copytree(BASE, base)
    terminal.mkdir(parents=True)
    shutil.copy2(ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/TERMINAL_MANIFEST.json",
                 terminal / "TERMINAL_MANIFEST.json")
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "test@example.invalid"], repo)
    _git(["config", "user.name", "Seal Test"], repo)
    _git(["add", "."], repo)
    _git(["commit", "-qm", "test fixture"], repo)
    extension = tmp_path / "extension"
    builder.build_extension(base, extension, _git(["rev-parse", "HEAD"], repo))
    manifest_path = extension / "EXTENSION_SOURCE_MANIFEST.json"
    manifest = strict_json(manifest_path)
    manifest["base_source_commit"] = "0" * 40
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    review = ROOT / "docs/toy_road_p0_repeatability_20260802/t3_loading_history_20260818/" \
        "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md"
    with pytest.raises(seal_builder.SealError, match="extension verification"):
        seal_builder.build_seal(
            repo, extension,
            ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
            "T3_SIBLING_TERMINAL_ADJUDICATION.json",
            review, REGISTRY, tmp_path / "seal",
        )


def test_seal_is_create_once_and_does_not_clobber(tmp_path: Path) -> None:
    """A consumed seal root cannot be reused or overwritten."""
    destination = tmp_path / "seal"
    destination.mkdir()
    sentinel = destination / "preexisting.txt"
    sentinel.write_text("preserve me", encoding="utf-8")
    with pytest.raises(RuntimeError, match="destination already exists"):
        build_test_seal(tmp_path, destination=destination)
    assert sentinel.read_text(encoding="utf-8") == "preserve me"


def _tampered_t3_adjudication(tmp_path: Path, mutate) -> Path:
    path = tmp_path / "T3_SIBLING_TERMINAL_ADJUDICATION.json"
    payload = strict_json(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
        "T3_SIBLING_TERMINAL_ADJUDICATION.json"
    )
    mutate(payload)
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return path


def _assert_runtime_mapping_rejected(adjudication: Path) -> None:
    seal_builder = load_module("build_t3_rev_seal")
    terminal = seal_builder.read_json(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/TERMINAL_MANIFEST.json"
    )
    with pytest.raises(seal_builder.SealError, match="execution identity|runtime identity"):
        seal_builder._require_t3_adjudication(seal_builder.read_json(adjudication), terminal)


def test_seal_rejects_modified_published_adjudication_bytes(tmp_path: Path) -> None:
    """A semantic lookalike cannot replace the inventory-bound T3 adjudication bytes."""
    adjudication = _tampered_t3_adjudication(tmp_path, lambda payload: payload.update({
        "review_note": "headline fields intentionally retained",
    }))
    with pytest.raises(RuntimeError, match="published T3 adjudication hash"):
        build_test_seal(tmp_path, t3_adjudication=adjudication)


def test_seal_rejects_mutated_absolute_runtime_path_order(tmp_path: Path) -> None:
    """The T3 MATLAB path order is a qualified runtime identity, not pass-through data."""
    def mutate(payload: dict[str, object]) -> None:
        execution = payload["execution"]
        assert isinstance(execution, dict)
        matlab = execution["matlab"]
        assert isinstance(matlab, dict)
        paths = matlab["absolute_path_order"]
        assert isinstance(paths, list)
        paths[0] = "C:\\tampered\\runtime-overlay"

    adjudication = _tampered_t3_adjudication(tmp_path, mutate)
    _assert_runtime_mapping_rejected(adjudication)
    with pytest.raises(RuntimeError, match="published T3 adjudication hash|runtime identity"):
        build_test_seal(tmp_path, t3_adjudication=adjudication)


@pytest.mark.parametrize("mutate", [
    lambda runtime: runtime.pop("thread_settings_evidence"),
    lambda runtime: runtime.update({"unqualified_runtime_field": "unexpected"}),
])
def test_seal_rejects_missing_or_extra_runtime_identity_fields(tmp_path: Path, mutate) -> None:
    """The seal admits only the complete, exact qualified runtime mapping."""
    def mutate_adjudication(payload: dict[str, object]) -> None:
        execution = payload["execution"]
        assert isinstance(execution, dict)
        mutate(execution)

    adjudication = _tampered_t3_adjudication(tmp_path, mutate_adjudication)
    _assert_runtime_mapping_rejected(adjudication)
    with pytest.raises(RuntimeError, match="published T3 adjudication hash|runtime identity"):
        build_test_seal(tmp_path, t3_adjudication=adjudication)


def test_seal_rejects_runtime_boolean_integer_confusion(tmp_path: Path) -> None:
    """A JSON integer cannot stand in for the qualified single-execution boolean."""
    def mutate(payload: dict[str, object]) -> None:
        execution = payload["execution"]
        assert isinstance(execution, dict)
        execution["single_execution"] = 1

    adjudication = _tampered_t3_adjudication(tmp_path, mutate)
    _assert_runtime_mapping_rejected(adjudication)


def _launcher_inputs(module, tmp_path: Path) -> dict[str, Path]:
    """Make immutable-looking inputs; MATLAB itself is always mocked."""
    builder = load_module("build_t3_rev_extension")
    repo = tmp_path / "repo"
    base = repo / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    shutil.copytree(BASE, base)
    terminal = repo / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence"
    terminal.mkdir(parents=True)
    shutil.copy2(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/TERMINAL_MANIFEST.json",
        terminal / "TERMINAL_MANIFEST.json",
    )
    shutil.copy2(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
        "T3_SIBLING_TERMINAL_ADJUDICATION.json",
        terminal / "T3_SIBLING_TERMINAL_ADJUDICATION.json",
    )
    predecessor_docs = repo / "docs" / "toy_road_p0_repeatability_20260802"
    review = predecessor_docs / "t3_loading_history_20260818" / \
        "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md"
    review.parent.mkdir(parents=True)
    shutil.copy2(
        ROOT / "docs/toy_road_p0_repeatability_20260802/t3_loading_history_20260818/"
        "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md",
        review,
    )
    registry = predecessor_docs / "QUALIFIED_TRAJECTORY_REGISTRY_20260824.json"
    shutil.copy2(REGISTRY, registry)
    initial = repo / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801" / "runtime"
    initial.mkdir(parents=True)
    shutil.copy2(
        ROOT / "producer_handoffs/rebuilt_initial_mex_qualification_20260801/runtime/initial.mexw64",
        initial / "initial.mexw64",
    )
    qualified_build = initial.parent / "build"
    qualified_build.mkdir()
    shutil.copy2(
        ROOT / "producer_handoffs/rebuilt_initial_mex_qualification_20260801/build/SOURCE_HASHES.json",
        qualified_build / "SOURCE_HASHES.json",
    )
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "test@example.invalid"], repo)
    _git(["config", "user.name", "Launcher Test"], repo)
    _git(["add", "."], repo)
    _git(["commit", "-qm", "test fixture"], repo)
    commit = _git(["rev-parse", "HEAD"], repo)
    extension = tmp_path / "extension"
    builder.build_extension(base, extension, commit)
    seal_builder = load_module("build_t3_rev_seal")
    seal_destination = tmp_path / "seal"
    seal_builder.build_seal(
        repo, extension, terminal / "T3_SIBLING_TERMINAL_ADJUDICATION.json",
        review, registry, seal_destination,
    )
    seal_path = seal_destination / "T3_REV_SEAL.json"
    template = tmp_path / "template" / "receipts"
    template.mkdir(parents=True)
    shutil.copy2(
        ROOT / "docs/toy_road_p0_repeatability_20260802/t2_material_state_failure_20260817/"
        "artifacts/receipts/T2_EXECUTION_INPUT_LOCK.json",
        template / "T2_EXECUTION_INPUT_LOCK.json",
    )
    matlab = tmp_path / "matlab.exe"
    matlab.write_bytes(b"test executable")
    griphfith = tmp_path / "griphfith"
    (griphfith / "Sources").mkdir(parents=True)
    for binary in (
            griphfith / "Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64",
            griphfith / "Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64"):
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_bytes(binary.name.encode("ascii"))
    suite_root = tmp_path / "suite"
    cholmod = suite_root / "CHOLMOD/MATLAB/cholmod2.mexw64"
    cholmod.parent.mkdir(parents=True)
    cholmod.write_bytes(b"cholmod2")
    module.SUITESPARSE_ROOT = suite_root
    module.AUTHORIZATION_STATE_ROOT = tmp_path / "authorization-state"
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "sens_mesh.m").write_bytes(b"test qualified sens mesh")
    return {
        "repo_root": repo,
        "run_root": tmp_path / "run",
        "seal_path": seal_path,
        "extension_root": extension,
        "template_run": template.parent,
        "griphfith_root": griphfith,
        "input_assets_root": assets,
        "matlab": matlab,
    }


def call_launcher(module, run_root: Path, tmp_path: Path) -> dict[str, object]:
    inputs = _launcher_inputs(module, tmp_path)
    inputs["run_root"] = run_root
    return module.launch_t3_rev(**inputs)


@pytest.mark.parametrize("section", ["predecessor_evidence", "physics_closure"])
def test_seal_evidence_revalidation_rejects_complete_canonical_tampering(
        tmp_path: Path, section: str) -> None:
    """Canonical lookalike seals cannot alter predecessor hashes or physics closure."""
    launcher = load_module("launch_t3_rev")
    inputs = _launcher_inputs(launcher, tmp_path)
    seal_builder = load_module("build_t3_rev_seal")
    seal = strict_json(inputs["seal_path"])
    seal_builder.require_seal_evidence(
        inputs["repo_root"], inputs["extension_root"], seal)
    if section == "predecessor_evidence":
        seal[section]["qualified_trajectory_registry_sha256"] = "0" * 64
    else:
        seal[section]["first_60_histogram_equal_to_t3"] = False
    with pytest.raises(seal_builder.SealError, match="predecessor|physics"):
        seal_builder.require_seal_evidence(
            inputs["repo_root"], inputs["extension_root"], seal)


def _allow_test_matlab_identity(
        module, monkeypatch: pytest.MonkeyPatch, *, allow_input_assets: bool = True) -> None:
    seal_builder = load_module("build_t3_rev_seal")
    monkeypatch.setattr(
        module, "executable_sha256",
        lambda _path: seal_builder.EXPECTED_EXECUTION["matlab"]["executable_sha256"],
        raising=False,
    )
    monkeypatch.setattr(
        module, "runtime_binary_sha256",
        lambda _paths: dict(seal_builder.EXPECTED_EXECUTION["four_binary_sha256"]),
        raising=False,
    )
    monkeypatch.setattr(module, "require_qualified_runtime_paths", lambda *args: None, raising=False)
    monkeypatch.setattr(module, "require_qualified_griphfith_sources", lambda *args: None, raising=False)
    monkeypatch.setattr(module, "require_materialized_runtime_overlay", lambda *args: None, raising=False)
    if allow_input_assets:
        monkeypatch.setattr(
            module, "input_asset_sha256",
            lambda _path: module.EXPECTED_INPUT_ASSET_SHA256["sens_mesh.m"],
            raising=False,
        )


def test_launcher_rejects_substituted_griphfith_tree_before_root_or_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Identical-looking bytes from a substitute checkout do not satisfy the sealed path."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    inputs["matlab"] = Path(r"C:\Program Files\MATLAB\R2025b\bin\matlab.exe")
    seal_builder = load_module("build_t3_rev_seal")
    monkeypatch.setattr(
        module, "executable_sha256",
        lambda _path: seal_builder.EXPECTED_EXECUTION["matlab"]["executable_sha256"],
    )
    with pytest.raises(module.LaunchError, match="qualified.*path|GRIPHFiTH"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_sealed_runtime_identity_pins_exact_matlab_executable_path() -> None:
    seal_builder = load_module("build_t3_rev_seal")
    assert seal_builder.EXPECTED_EXECUTION["matlab_executable_path"] == (
        r"C:\Program Files\MATLAB\R2025b\bin\matlab.exe"
    )


def test_runtime_path_binding_rejects_reparse_alias_even_when_sealed_text_matches(
        tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    real = tmp_path / "real-griphfith"
    (real / "Sources").mkdir(parents=True)
    alias = tmp_path / "griphfith-alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    matlab = tmp_path / "matlab.exe"
    matlab.write_bytes(b"identity only")
    seal_builder = load_module("build_t3_rev_seal")
    runtime = json.loads(json.dumps(seal_builder.EXPECTED_EXECUTION))
    runtime["matlab_executable_path"] = str(matlab.absolute())
    runtime["matlab"]["absolute_path_order"][2:] = [
        str(alias.absolute() / "Sources"),
        str(module.SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "AMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "COLAMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "CCOLAMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "CAMD" / "MATLAB"),
    ]
    with pytest.raises(module.LaunchError, match="reparse|symlink|canonical"):
        module.require_qualified_runtime_paths(runtime, matlab.absolute(), alias.absolute())


def test_launcher_rejects_non_mex_source_mutation_before_root_or_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every qualified MATLAB/C/C++/header source, not just binaries, is byte-bound."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    real_source_validator = module.require_qualified_griphfith_sources
    _allow_test_matlab_identity(module, monkeypatch)
    monkeypatch.setattr(module, "require_qualified_griphfith_sources", real_source_validator)
    evidence = strict_json(
        inputs["repo_root"] / "producer_handoffs" /
        "rebuilt_initial_mex_qualification_20260801" / "build" / "SOURCE_HASHES.json"
    )
    records = evidence["locked_git_tree_inventory"]
    assert isinstance(records, list) and len(records) == 221
    source_repo = Path(r"C:\q4diag\griphfith-pf-rebuild-355d4c83")
    if not source_repo.is_dir():
        pytest.skip("qualified GRIPHFiTH Git object database is unavailable")
    for record in records:
        relative = record["path"]
        payload = subprocess.check_output([
            "git", "-C", str(source_repo), "show",
            f"355d4c83fefc2db88c32031a2dd2623b3de85c89:{relative}",
        ])
        target = inputs["griphfith_root"] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    mutated = inputs["griphfith_root"] / "Sources" / "+phase_field" / "System.m"
    assert mutated.is_file()
    mutated.write_bytes(mutated.read_bytes() + b"\n% mutation\n")
    with pytest.raises(module.LaunchError, match="qualified source.*System.m|System.m.*SHA-256"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_tampered_extension_shadow_leaves_no_root_or_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    shadow = inputs["extension_root"] / manifest["shadow_files"][0]["path"]
    shadow.write_bytes(shadow.read_bytes() + b"\n% tampered after sealing\n")
    with pytest.raises(module.LaunchError, match="extension shadow|extension source verification"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_protocol_construction_failure_leaves_no_root_or_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    def reject(*args, **kwargs):
        raise module.LaunchError("injected authoritative protocol failure")
    monkeypatch.setattr(module, "build_future_execution_lock", reject, raising=False)
    with pytest.raises(module.LaunchError, match="protocol failure"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_io_failure_after_root_claim_is_consumed_prepared_no_launch(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Preparation I/O failure is terminal for the root and cannot masquerade as preflight."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    monkeypatch.setattr(
        module, "materialize_runtime_overlay",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected storage failure")),
    )
    with pytest.raises(module.PreparedLaunchError, match="consumed/prepared"):
        module.launch_t3_rev(**inputs)
    assert inputs["run_root"].is_dir()
    assert seal_marker(module, inputs["seal_path"]).is_file()
    receipt = strict_json(inputs["run_root"] / "receipts" / "PREPARED_NO_LAUNCH.json")
    assert receipt["status"] == "PREPARED_NO_LAUNCH"
    assert receipt["resume_allowed"] is False


@pytest.mark.parametrize("mutation", ["changed", "extra", "missing", "reparse"])
def test_final_overlay_closure_rejects_post_materialization_mutation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    real_overlay_validator = module.require_materialized_runtime_overlay
    _allow_test_matlab_identity(module, monkeypatch)
    monkeypatch.setattr(module, "require_materialized_runtime_overlay", real_overlay_validator)
    real_final = module.require_final_launch_inputs

    def mutate_overlay(*args, **kwargs):
        overlay = inputs["run_root"] / ".toy-road-runtime-overlay"
        manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
        target = overlay / manifest["shadow_files"][0]["path"]
        if mutation == "changed":
            target.write_bytes(target.read_bytes() + b"\n% post-materialization mutation\n")
        elif mutation == "extra":
            (overlay / "unexpected.m").write_text("% extra", encoding="utf-8")
        elif mutation == "missing":
            target.unlink()
        else:
            replacement = tmp_path / "replacement.m"
            replacement.write_bytes(target.read_bytes())
            target.unlink()
            try:
                target.symlink_to(replacement)
            except OSError:
                pytest.skip("file symlink creation is unavailable")
        return real_final(*args, **kwargs)

    monkeypatch.setattr(module, "require_final_launch_inputs", mutate_overlay)
    with pytest.raises(module.PreparedLaunchError, match="consumed/prepared"):
        module.launch_t3_rev(**inputs)
    assert not (inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()


def test_exact_materialized_overlay_closure_is_accepted(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    real_overlay_validator = module.require_materialized_runtime_overlay
    _allow_test_matlab_identity(module, monkeypatch)
    monkeypatch.setattr(module, "require_materialized_runtime_overlay", real_overlay_validator)

    class Process:
        pid = 7531

    monkeypatch.setattr(module, "Popen", lambda *a, **k: Process())
    assert module.launch_t3_rev(**inputs)["status"] == "LAUNCHED"


def test_identical_seal_copies_share_one_global_content_addressed_claim(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 8642

    popen_calls = 0
    def fake_popen(*args, **kwargs):
        nonlocal popen_calls
        popen_calls += 1
        return Process()

    monkeypatch.setattr(module, "Popen", fake_popen)
    inputs = _launcher_inputs(module, tmp_path)
    copied_seal = tmp_path / "copied" / "T3_REV_SEAL.json"
    copied_seal.parent.mkdir()
    shutil.copy2(inputs["seal_path"], copied_seal)
    original_seal_bytes = inputs["seal_path"].read_bytes()
    module.launch_t3_rev(**inputs)
    inputs["seal_path"].write_bytes(b"temporarily changed")
    inputs["seal_path"].write_bytes(original_seal_bytes)
    replay = dict(inputs)
    replay["seal_path"] = copied_seal
    replay["run_root"] = tmp_path / "replay-run"
    with pytest.raises(module.LaunchError, match="seal.*consumed"):
        module.launch_t3_rev(**replay)
    assert popen_calls == 1
    assert not replay["run_root"].exists()


def test_credential_publication_failure_after_popen_is_fail_closed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 9753

    monkeypatch.setattr(module, "Popen", lambda *a, **k: Process())
    real_link = module.os.link
    def fail_credential_link(source, target, *args, **kwargs):
        if Path(target).name == "T3_REV_LAUNCH_RECEIPT.json":
            raise OSError("link failed")
        return real_link(source, target, *args, **kwargs)

    monkeypatch.setattr(module.os, "link", fail_credential_link)
    with pytest.raises(module.LaunchCredentialError, match="credential"):
        module.launch_t3_rev(**inputs)
    receipts = inputs["run_root"] / "receipts"
    assert not (receipts / "T3_REV_LAUNCH_RECEIPT.json").exists()
    failed = strict_json(receipts / "LAUNCH_CREDENTIAL_FAILED.json")
    assert failed["status"] == "LAUNCH_CREDENTIAL_FAILED"
    assert failed["process_started"] is True


def test_seal_mutation_immediately_before_consumption_cannot_claim(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    original_bytes = inputs["seal_path"].read_bytes()
    original_sha256 = hashlib.sha256(original_bytes).hexdigest()
    real_materialize = module.materialize_runtime_overlay

    def mutate_after_materialization(*args, **kwargs):
        real_materialize(*args, **kwargs)
        inputs["seal_path"].write_bytes(original_bytes + b"\n")

    monkeypatch.setattr(module, "materialize_runtime_overlay", mutate_after_materialization)
    with pytest.raises(module.PreparedLaunchError, match="seal bytes changed"):
        module.launch_t3_rev(**inputs)
    assert not module.seal_consumption_marker(original_sha256).exists()


def test_stale_wrong_nonce_receipt_conflict_never_becomes_valid(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 1472

    stale_bytes = json.dumps({"launch_nonce": "0" * 64}).encode("utf-8")

    def stale_popen(args, **kwargs):
        batch = args[2]
        assert hashlib.sha256(stale_bytes).hexdigest() not in batch
        return Process()

    monkeypatch.setattr(module, "Popen", stale_popen)
    real_link = module.os.link
    def inject_conflict_at_publish(source, target, *args, **kwargs):
        if Path(target).name == "T3_REV_LAUNCH_RECEIPT.json":
            Path(target).write_bytes(stale_bytes)
        return real_link(source, target, *args, **kwargs)

    monkeypatch.setattr(module.os, "link", inject_conflict_at_publish)
    with pytest.raises(module.LaunchCredentialError, match="credential"):
        module.launch_t3_rev(**inputs)
    receipts = inputs["run_root"] / "receipts"
    assert (receipts / "T3_REV_LAUNCH_RECEIPT.json").read_bytes() == stale_bytes
    assert strict_json(receipts / "LAUNCH_CREDENTIAL_FAILED.json")["status"] == "LAUNCH_CREDENTIAL_FAILED"


def test_post_publish_temp_cleanup_failure_does_not_reverse_success(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 2583

    monkeypatch.setattr(module, "Popen", lambda *a, **k: Process())
    real_unlink = Path.unlink
    def fail_temp_cleanup(path, *args, **kwargs):
        if path.name.startswith(".T3_REV_LAUNCH_RECEIPT.json") and path.name.endswith(".tmp"):
            raise RuntimeError("cleanup failed after publish")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temp_cleanup)
    assert module.launch_t3_rev(**inputs)["status"] == "LAUNCHED"
    receipt = inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    assert receipt.is_file()


def test_pid_write_failure_after_popen_never_publishes_pass(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 3694

    popen_calls = 0

    def fake_popen(*args, **kwargs):
        nonlocal popen_calls
        popen_calls += 1
        return Process()

    def fail_pid_write(*args, **kwargs):
        raise OSError("injected launcher.pid failure")

    monkeypatch.setattr(module, "Popen", fake_popen)
    monkeypatch.setattr(module, "write_launcher_pid", fail_pid_write, raising=False)
    with pytest.raises(module.LaunchCredentialError, match="credential"):
        module.launch_t3_rev(**inputs)
    receipts = inputs["run_root"] / "receipts"
    assert popen_calls == 1
    assert not (receipts / "T3_REV_LAUNCH_RECEIPT.json").exists()
    assert strict_json(receipts / "LAUNCH_CREDENTIAL_FAILED.json")["status"] == "LAUNCH_CREDENTIAL_FAILED"


@pytest.mark.parametrize("failing_handle", ["stdout", "stderr"])
def test_log_close_failure_after_popen_never_publishes_pass(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failing_handle: str) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 4705

    class LogHandle:
        def __init__(self, name: str) -> None:
            self.name = name
            self.close_attempted = False

        def close(self) -> None:
            self.close_attempted = True
            if self.name == failing_handle:
                raise OSError(f"injected {self.name} close failure")

    stdout = LogHandle("stdout")
    stderr = LogHandle("stderr")
    monkeypatch.setattr(module, "open_launch_logs", lambda _run_root: (stdout, stderr))
    monkeypatch.setattr(module, "Popen", lambda *a, **k: Process())
    with pytest.raises(module.LaunchCredentialError, match="credential"):
        module.launch_t3_rev(**inputs)
    receipts = inputs["run_root"] / "receipts"
    assert stdout.close_attempted
    assert stderr.close_attempted
    assert not (receipts / "T3_REV_LAUNCH_RECEIPT.json").exists()
    assert strict_json(receipts / "LAUNCH_CREDENTIAL_FAILED.json")["status"] == "LAUNCH_CREDENTIAL_FAILED"


@pytest.mark.parametrize("variant", ["extra_lf", "key_order", "whitespace"])
def test_semantically_equal_noncanonical_seal_copy_cannot_replay(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, variant: str) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    value = strict_json(inputs["seal_path"])
    if variant == "extra_lf":
        payload = inputs["seal_path"].read_bytes() + b"\n"
    elif variant == "key_order":
        payload = (json.dumps(dict(reversed(list(value.items()))), separators=(",", ":")) + "\n").encode()
    else:
        payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    variant_path = tmp_path / f"seal-{variant}.json"
    variant_path.write_bytes(payload)
    attempt = dict(inputs)
    attempt["seal_path"] = variant_path
    attempt["run_root"] = tmp_path / f"run-{variant}"
    with pytest.raises(module.LaunchError, match="canonical JSON encoding"):
        module.launch_t3_rev(**attempt)
    assert not attempt["run_root"].exists()


def test_busy_refusal_precedes_root_creation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An occupied experiment machine cannot consume a fresh run root."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [{"ProcessId": 1, "Name": "MATLAB.exe"}])
    run = tmp_path / "run"
    with pytest.raises(module.BusyExperimentError):
        call_launcher(module, run, tmp_path)
    assert not run.exists()


def test_second_busy_check_prevents_popen_and_records_consumed_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A process that appears during setup consumes the root without a launch."""
    module = load_module("launch_t3_rev")
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    run = tmp_path / "run"
    inputs["run_root"] = run
    checks = iter([[], [{"ProcessId": 2, "Name": "MATLAB.exe"}]])
    monkeypatch.setattr(module, "matlab_processes", lambda: next(checks))
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    with pytest.raises(module.BusyExperimentError, match="final process check"):
        module.launch_t3_rev(**inputs)
    receipt = strict_json(run / "receipts" / "BUSY_NO_LAUNCH.json")
    assert receipt["status"] == "BUSY_NO_LAUNCH"
    assert receipt["resume_allowed"] is False
    assert not (run / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    with pytest.raises(FileExistsError):
        module.launch_t3_rev(**inputs)
    different_root = dict(inputs)
    different_root["run_root"] = tmp_path / "different-run"
    with pytest.raises(module.LaunchError, match="seal.*consumed"):
        module.launch_t3_rev(**different_root)


def test_final_revalidation_precedes_race_closing_busy_check(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A process appearing during final input checks is observed before logs or credentials."""
    module = load_module("launch_t3_rev")
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    events: list[str] = []
    busy = False
    real_final = module.require_final_launch_inputs

    def processes():
        events.append("busy")
        return ([{"ProcessId": 73, "Name": "MATLAB.exe"}] if busy else [])

    def final_inputs(*args, **kwargs):
        nonlocal busy
        events.append("final_inputs")
        real_final(*args, **kwargs)
        busy = True

    monkeypatch.setattr(module, "matlab_processes", processes)
    monkeypatch.setattr(module, "require_final_launch_inputs", final_inputs)
    monkeypatch.setattr(module, "open_launch_logs", lambda _root: pytest.fail("logs opened"))
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    with pytest.raises(module.BusyExperimentError, match="final process check"):
        module.launch_t3_rev(**inputs)
    assert events == ["busy", "final_inputs", "busy"]
    assert seal_marker(module, inputs["seal_path"]).is_file()
    busy_receipt = strict_json(inputs["run_root"] / "receipts" / "BUSY_NO_LAUNCH.json")
    assert busy_receipt["status"] == "BUSY_NO_LAUNCH"
    assert not (inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()
    assert not (inputs["run_root"] / "T3_REV.stdout.log").exists()


def test_two_root_concurrent_claim_has_no_pass_receipt_for_loser(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 5317

    monkeypatch.setattr(module, "Popen", lambda *a, **k: Process())
    inputs = _launcher_inputs(module, tmp_path)
    claims = threading.Barrier(2)
    real_consume = module.consume_seal

    def simultaneous_consume(seal_path, run_root, expected_sha256, expected_bytes):
        claims.wait(timeout=10)
        return real_consume(seal_path, run_root, expected_sha256, expected_bytes)

    monkeypatch.setattr(module, "consume_seal", simultaneous_consume)
    candidates = []
    for name in ("first-run", "second-run"):
        candidate = dict(inputs)
        candidate["run_root"] = tmp_path / name
        candidates.append(candidate)

    def attempt(candidate):
        try:
            return module.launch_t3_rev(**candidate)
        except Exception as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, candidates))
    assert sum(isinstance(item, dict) for item in outcomes) == 1
    assert sum(isinstance(item, module.PreparedLaunchError) for item in outcomes) == 1
    marker = strict_json(seal_marker(module, inputs["seal_path"]))
    winning_root = Path(marker["run_root"])
    losing_root = next(Path(item["run_root"]) for item in candidates if Path(item["run_root"]).resolve() != winning_root)
    assert (winning_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").is_file()
    assert not (losing_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()
    assert strict_json(losing_root / "receipts" / "PREPARED_NO_LAUNCH.json")["status"] == "PREPARED_NO_LAUNCH"


@pytest.mark.parametrize("failure", ["logs", "popen"])
def test_late_no_launch_failure_invalidates_pass_credential(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str) -> None:
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    if failure == "logs":
        monkeypatch.setattr(
            module, "open_launch_logs",
            lambda _root: (_ for _ in ()).throw(OSError("injected log failure")),
            raising=False,
        )
    else:
        monkeypatch.setattr(
            module, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("injected Popen failure"))
        )
    with pytest.raises(module.PreparedLaunchError, match="consumed/prepared"):
        module.launch_t3_rev(**inputs)
    receipt = inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    assert not receipt.exists()
    invalidated = inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.INVALIDATED.json"
    assert not invalidated.exists()
    assert strict_json(inputs["run_root"] / "receipts" / "PREPARED_NO_LAUNCH.json")["status"] == "PREPARED_NO_LAUNCH"


def test_extension_mutation_between_preflight_and_final_check_has_no_pass_receipt(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    shadow = inputs["extension_root"] / manifest["shadow_files"][0]["path"]
    real_final = module.require_final_launch_inputs

    def mutate_during_final_revalidation(*args, **kwargs):
        shadow.write_bytes(shadow.read_bytes() + b"\n% raced mutation\n")
        return real_final(*args, **kwargs)

    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "require_final_launch_inputs", mutate_during_final_revalidation)
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    with pytest.raises(module.LaunchError, match="extension|shadow|final"):
        module.launch_t3_rev(**inputs)
    assert not (inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()
    assert strict_json(inputs["run_root"] / "receipts" / "PREPARED_NO_LAUNCH.json")["status"] == "PREPARED_NO_LAUNCH"


def test_launcher_popen_uses_locked_paths_and_environment(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The sole launch boundary passes the T3-rev lock and qualified path order."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    captured: dict[str, object] = {}

    class Process:
        pid = 4321

    def fake_popen(*args, **kwargs):
        lock = strict_json(
            tmp_path / "run" / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json"
        )
        assert all(not Path(path).exists() for path in lock["writable_roots"].values())
        assert not (tmp_path / "run" / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").exists()
        assert "toy_road_wait_for_launch_receipt(" in args[0][2]
        captured["args"] = args
        captured["kwargs"] = kwargs
        return Process()

    inputs = _launcher_inputs(module, tmp_path)
    inputs["run_root"] = tmp_path / "run"
    _allow_test_matlab_identity(module, monkeypatch)
    monkeypatch.setattr(module, "Popen", fake_popen)
    result = module.launch_t3_rev(**inputs)
    assert result["status"] == "LAUNCHED"
    args = captured["args"]
    kwargs = captured["kwargs"]
    assert isinstance(args, tuple) and args[0][1] == "-batch"
    assert isinstance(kwargs, dict)
    assert kwargs["creationflags"] == 0x08000000 | 0x00000200
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["TOY_ROAD_CASE_ROLE"] == "T3_rev_loading_order"
    assert env["OMP_NUM_THREADS"] == "1"
    lock = strict_json(tmp_path / "run" / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    assert set(lock) == {
        "authorization_scope", "case_id", "case_physics_contract_sha256",
        "family_contract_sha256", "launch_timestamp_utc", "no_clobber_receipt_id",
        "protocol_version", "resume_allowed", "runtime_expectations",
        "runtime_lock_sha256", "schema_version", "source_commit",
        "source_manifest_sha256", "writable_roots",
    }
    assert set(lock["writable_roots"]) == {
        "output", "work", "temp", "tmp", "pref", "cache", "matlab_startup_pref",
    }
    generated_protocol = module.load_protocol(
        inputs["extension_root"] / "toy_road_protocol.py", "test_generated_protocol"
    )
    generated_protocol.validate_execution_input_lock(lock, "T3_rev_loading_order")
    lock_path = tmp_path / "run" / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json"
    assert lock_path.read_bytes() == generated_protocol.canonical_json_bytes(lock)
    simulated_measurement = {
        "execution_input_lock_sha256": generated_protocol.canonical_json_sha256(lock),
    }
    assert simulated_measurement["execution_input_lock_sha256"] == hashlib.sha256(
        lock_path.read_bytes()
    ).hexdigest()
    assert env["TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256"] == simulated_measurement[
        "execution_input_lock_sha256"
    ]
    assert lock["runtime_lock_sha256"] == "a53a1431b6f7a1b56f44f3faccb410ba11a4b9a6ef4f1a16b30258936bd0f8d7"
    template_lock = strict_json(inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json")
    assert lock["source_commit"] == template_lock["source_commit"]
    assert lock["family_contract_sha256"] != template_lock["family_contract_sha256"]
    assert lock["case_physics_contract_sha256"] != template_lock["case_physics_contract_sha256"]
    assert env["TOY_ROAD_FAMILY_CONTRACT_SHA256"] == lock["family_contract_sha256"]
    assert env["TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256"] == lock["case_physics_contract_sha256"]
    expected_paths = [
        str(tmp_path / "run" / ".toy-road-runtime-overlay"),
        str(inputs["repo_root"] / "producer_handoffs" / "toy_road_p0_repeatability_20260803"),
        str(tmp_path / "griphfith" / "Sources"),
        str(module.SUITESPARSE_ROOT / "CHOLMOD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "AMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "COLAMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "CCOLAMD" / "MATLAB"),
        str(module.SUITESPARSE_ROOT / "CAMD" / "MATLAB"),
    ]
    matlab = lock["runtime_expectations"]["matlab"]
    assert matlab["absolute_path_order"] == expected_paths
    receipt = strict_json(tmp_path / "run" / "receipts" / "T3_REV_LAUNCH_RECEIPT.json")
    module.require_bridge_authorization_receipt(receipt)
    receipt_bytes = (tmp_path / "run" / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").read_bytes()
    batch = captured["args"][0][2]
    assert hashlib.sha256(receipt_bytes).hexdigest() in batch
    assert receipt["launch_nonce"] in batch
    assert receipt["seal_sha256"] in batch
    assert receipt["execution_input_lock_sha256"] in batch
    assert receipt["run_root"] in batch
    assert receipt["authorization_scope"] == "production_authorized"
    assert receipt["authorized_entrypoint"] == "run_toy_road_runtime_bridge"
    assert receipt["follow_on_authorized"] is False
    assert receipt["extension_root"] == str(inputs["extension_root"])
    assert receipt["thread_environment"] == {
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_DYNAMIC": "FALSE",
    }
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    expected_shadow = {
        item["path"]: item["sha256"] for item in manifest["shadow_files"]
    }
    assert receipt["extension_shadow_sha256"] == expected_shadow
    overlay = tmp_path / "run" / ".toy-road-runtime-overlay"
    for relative, digest in expected_shadow.items():
        assert hashlib.sha256((overlay / relative).read_bytes()).hexdigest() == digest


def test_launcher_rejects_tampered_extension_identity_before_root_creation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A mutable extension manifest cannot bypass the seal's composite identity."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    inputs = _launcher_inputs(module, tmp_path)
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    manifest["base_source_commit"] = "0" * 40
    (inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    with pytest.raises(module.LaunchError, match="extension|composite"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


def test_seal_consumption_marker_is_atomic_across_run_roots(tmp_path: Path) -> None:
    """Concurrent claims for one seal leave exactly one immutable owner marker."""
    module = load_module("launch_t3_rev")
    module.AUTHORIZATION_STATE_ROOT = tmp_path / "authorization-state"
    seal = tmp_path / "T3_REV_SEAL.json"
    seal.write_text("{}", encoding="utf-8")
    roots = [tmp_path / "first", tmp_path / "second"]
    seal_bytes = seal.read_bytes()
    seal_sha256 = hashlib.sha256(seal_bytes).hexdigest()

    def claim(root: Path) -> tuple[str, object]:
        try:
            return ("claimed", module.consume_seal(seal, root, seal_sha256, seal_bytes))
        except module.LaunchError as error:
            return ("blocked", str(error))

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(claim, roots))
    assert [state for state, _ in outcomes].count("claimed") == 1
    assert [state for state, _ in outcomes].count("blocked") == 1
    marker = seal_marker(module, seal)
    marker_value = strict_json(marker)
    assert marker_value["seal_sha256"] == hashlib.sha256(seal.read_bytes()).hexdigest()
    assert marker_value["case_id"] == "T3_rev_loading_order"
    assert marker_value["run_root"] in {str(path.resolve()) for path in roots}


def test_launcher_consumes_one_seal_across_different_fresh_roots(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A successful process claim cannot be replayed into a second fresh root."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    _allow_test_matlab_identity(module, monkeypatch)

    class Process:
        pid = 2468

    monkeypatch.setattr(module, "Popen", lambda *args, **kwargs: Process())
    inputs = _launcher_inputs(module, tmp_path)
    module.launch_t3_rev(**inputs)
    second = dict(inputs)
    second["run_root"] = tmp_path / "second-fresh-root"
    monkeypatch.setattr(module, "Popen", lambda *args, **kwargs: pytest.fail("Popen called"))
    with pytest.raises(module.LaunchError, match="seal.*consumed"):
        module.launch_t3_rev(**second)
    assert not second["run_root"].exists()


def test_launcher_rejects_tampered_matlab_executable_before_root_creation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The executable itself, not merely its claimed template identity, is sealed."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    with pytest.raises(module.LaunchError, match="MATLAB executable"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


@pytest.mark.parametrize("mutate", [
    lambda matlab: matlab.update({"release": "R2025a Update 5"}),
    lambda matlab: matlab.update({"update": True}),
])
def test_launcher_rejects_template_matlab_release_or_update_type_tampering(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutate) -> None:
    """The template admits only the complete type-sensitive qualified MATLAB mapping."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    path = inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    payload = strict_json(path)
    runtime = payload["runtime_expectations"]
    assert isinstance(runtime, dict)
    matlab = runtime["matlab"]
    assert isinstance(matlab, dict)
    mutate(matlab)
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(
            module.LaunchError,
            match="MATLAB identity|authoritative protocol|qualified predecessor",
    ):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


def test_launcher_rejects_extra_template_runtime_mapping_before_root_creation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An unsealed runtime field cannot silently accompany the expected mapping."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    path = inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    payload = strict_json(path)
    runtime = payload["runtime_expectations"]
    assert isinstance(runtime, dict)
    runtime["unsealed_extra"] = "forbidden"
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(module.LaunchError, match="template runtime identity|authoritative protocol"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


@pytest.mark.parametrize("target", ["initial", "AMOR", "AT1_HISTORY_FATIGUE", "cholmod2"])
def test_launcher_rejects_each_tampered_runtime_binary_before_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str) -> None:
    """All four runtime binaries are byte-bound before root or seal consumption."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    seal_builder = load_module("build_t3_rev_seal")
    bad = dict(seal_builder.EXPECTED_EXECUTION["four_binary_sha256"])
    bad[target] = "0" * 64
    monkeypatch.setattr(module, "runtime_binary_sha256", lambda _paths: bad)
    with pytest.raises(module.LaunchError, match="runtime binary"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


@pytest.mark.parametrize("mutate", [
    lambda lock: lock.update({"authorization_scope": "test_only"}),
    lambda lock: lock.update({"protocol_version": "wrong"}),
    lambda lock: lock.update({"unexpected": "extra"}),
    lambda lock: lock.pop("writable_roots"),
    lambda lock: lock.update({"resume_allowed": 0}),
])
def test_launcher_rejects_tampered_template_schema_before_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutate) -> None:
    """The predecessor lock is a complete typed input, never a pass-through object."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    path = inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    lock = strict_json(path)
    mutate(lock)
    path.write_text(json.dumps(lock, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(module.LaunchError, match="template execution lock|template runtime"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_published_template_lock_is_accepted_by_authoritative_base_protocol(
        tmp_path: Path) -> None:
    """The exact qualified T2 predecessor remains a valid base-protocol lock."""
    module = load_module("launch_t3_rev")
    inputs = _launcher_inputs(module, tmp_path)
    base_protocol = module.load_protocol(
        inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803" / "toy_road_protocol.py",
        "test_base_protocol",
    )
    lock = strict_json(inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json")
    base_protocol.validate_execution_input_lock(lock, "T2_material_state")


@pytest.mark.parametrize(("name", "mutate"), [
    ("nested_roots", lambda lock: lock["writable_roots"].update({
        "temp": lock["writable_roots"]["output"] + "\\nested",
    })),
    ("case_folded_root_collision", lambda lock: lock["writable_roots"].update({
        "temp": lock["writable_roots"]["output"].upper(),
    })),
    ("relative_root", lambda lock: lock["writable_roots"].update({"temp": "relative/temp"})),
    ("timestamp", lambda lock: lock.update({"launch_timestamp_utc": "not-a-timestamp"})),
    ("no_clobber", lambda lock: lock.update({"no_clobber_receipt_id": ""})),
    ("case", lambda lock: lock.update({"case_id": "T3_loading_history"})),
    ("source_commit", lambda lock: lock.update({"source_commit": "0" * 40})),
    ("source_manifest", lambda lock: lock.update({"source_manifest_sha256": "0" * 64})),
    ("family_contract", lambda lock: lock.update({"family_contract_sha256": "0" * 64})),
    ("case_contract", lambda lock: lock.update({"case_physics_contract_sha256": "0" * 64})),
])
def test_launcher_rejects_malformed_or_substituted_template_identity_before_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, mutate) -> None:
    """Protocol-invalid or non-qualified predecessor identities never consume the seal."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    path = inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
    lock = strict_json(path)
    mutate(lock)
    path.write_text(json.dumps(lock, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(module.LaunchError, match="template execution lock|qualified predecessor"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists(), name
    assert not seal_marker(module, inputs["seal_path"]).exists(), name


@pytest.mark.parametrize("mutation", ["missing", "tampered"])
def test_launcher_rejects_missing_or_tampered_sens_mesh_before_consumption(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str) -> None:
    """The qualified read-only mesh bytes are closed before root or seal consumption."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch, allow_input_assets=False)
    mesh = inputs["input_assets_root"] / "sens_mesh.m"
    if mutation == "missing":
        mesh.unlink()
    else:
        mesh.write_bytes(b"tampered sens mesh")
    with pytest.raises(module.LaunchError, match="input asset.*sens_mesh"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_launcher_rejects_tampered_input_asset_qualification_evidence(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A mutable mesh-hash claim cannot replace the sealed qualification inventory."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    evidence = (
        inputs["repo_root"] / "producer_handoffs" /
        "rebuilt_initial_mex_qualification_20260801" / "build" / "SOURCE_HASHES.json"
    )
    payload = strict_json(evidence)
    inventory = payload["locked_git_tree_inventory"]
    assert isinstance(inventory, list)
    mesh_entry = next(
        item for item in inventory
        if item["path"] == "Dependencies/meshes/sens_mesh.m"
    )
    mesh_entry["sha256"] = "0" * 64
    evidence.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    committed_identity = strict_json(
        inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json"
    )["repo_commit"]
    monkeypatch.setattr(module, "clean_repository_commit", lambda _repo: committed_identity)
    with pytest.raises(module.LaunchError, match="input asset qualification evidence"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()
    assert not seal_marker(module, inputs["seal_path"]).exists()


def test_launcher_requires_clean_committed_repository(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A fresh root cannot be consumed by uncommitted launch source."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    (inputs["repo_root"] / "uncommitted-launch-change.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(module.LaunchError, match="clean"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


@pytest.mark.parametrize("target", ["seal", "template_lock"])
def test_launcher_rejects_tampered_seal_or_runtime_input_before_root_creation(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str) -> None:
    """Neither a mutable capability nor a borrowed runtime lock can be substituted."""
    module = load_module("launch_t3_rev")
    monkeypatch.setattr(module, "matlab_processes", lambda: [])
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    inputs = _launcher_inputs(module, tmp_path)
    if target == "seal":
        payload = strict_json(inputs["seal_path"])
        payload["authorization_capability"] = "unbounded"
        inputs["seal_path"].write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
    else:
        path = inputs["template_run"] / "receipts" / "T2_EXECUTION_INPUT_LOCK.json"
        payload = strict_json(path)
        payload["runtime_lock_sha256"] = "0" * 64
        path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(module.LaunchError, match="seal|runtime|qualified predecessor"):
        module.launch_t3_rev(**inputs)
    assert not inputs["run_root"].exists()


def test_launcher_has_single_nonresume_case_scope() -> None:
    text = (ANALYSIS / "launch_t3_rev.py").read_text(encoding="utf-8")
    assert '"TOY_ROAD_CASE_ROLE": "T3_rev_loading_order"' in text
    assert '"TOY_ROAD_CASE_ROLE": "T2_material_state"' not in text
    assert '"resume_allowed": False' in text
    for forbidden in ("T2-CONT", "retry_experiment", "follow_on_case"):
        assert forbidden not in text


def test_launcher_cli_maps_documented_flags_to_exact_launch_keywords(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The public CLI spelling must call the Python launch boundary without keyword drift."""
    module = load_module("launch_t3_rev")
    values = {
        "repo_root": tmp_path / "repo",
        "run_root": tmp_path / "run",
        "seal_path": tmp_path / "seal.json",
        "extension_root": tmp_path / "extension",
        "template_run": tmp_path / "template",
        "griphfith_root": tmp_path / "griphfith",
        "input_assets_root": tmp_path / "assets",
        "matlab": tmp_path / "matlab.exe",
    }
    captured: dict[str, object] = {}

    def fake_launch(**kwargs):
        captured.update(kwargs)
        return {"status": "DRY_RUN", "pid": 0}

    monkeypatch.setattr(module, "launch_t3_rev", fake_launch)
    monkeypatch.setattr(module, "Popen", lambda *a, **k: pytest.fail("Popen called"))
    monkeypatch.setattr(sys, "argv", [
        "launch_t3_rev.py",
        "--repo-root", str(values["repo_root"]),
        "--run-root", str(values["run_root"]),
        "--seal", str(values["seal_path"]),
        "--extension-root", str(values["extension_root"]),
        "--template-run", str(values["template_run"]),
        "--gripfith-root", str(values["griphfith_root"]),
        "--input-assets-root", str(values["input_assets_root"]),
        "--matlab", str(values["matlab"]),
    ])
    assert module.main() == 0
    assert captured == values
    assert json.loads(capsys.readouterr().out) == {"pid": 0, "status": "DRY_RUN"}


def _order_rows(*signals: tuple[int, float, float]) -> list[dict[str, float]]:
    """Small, explicit reduction fixture for the predeclared T3/T3-rev boundary."""
    return [
        {"cycle": float(cycle), "max_abs": maximum, "relative_l2": relative}
        for cycle, maximum, relative in signals
    ]


def test_predeclared_order_effect_classes() -> None:
    """The c60 boundary separates unresolved, persistent, and transient order effects."""
    module = load_module("analyze_t3_rev")
    tolerance = {"max_abs": 1e-12, "relative_l2": 1e-12}
    assert module.classify_order_effect(_order_rows(
        (60, 1e-12, 1e-12), (61, 0.0, 0.0), (62, 0.0, 0.0),
    ), tolerance) == "ORDER_EFFECT_NOT_RESOLVED_WITHIN_TOLERANCE"
    assert module.classify_order_effect(_order_rows(
        (60, 2e-12, 0.0), (61, 0.0, 2e-12), (62, 0.0, 0.0),
    ), tolerance) == "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"
    assert module.classify_order_effect(_order_rows(
        (60, 2e-12, 0.0), (61, 1e-12, 1e-12), (62, 0.0, 0.0),
    ), tolerance) == "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"


def test_order_effect_requires_consecutive_post_c60_rows() -> None:
    """Missing evidence is unavailable; it is never treated as a converged trajectory."""
    module = load_module("analyze_t3_rev")
    tolerance = {"max_abs": 1e-12, "relative_l2": 1e-12}
    assert module.classify_order_effect(_order_rows(
        (60, 2e-12, 0.0), (62, 0.0, 0.0),
    ), tolerance) == "UNAVAILABLE"


@pytest.mark.parametrize("rows, tolerance", [
    (_order_rows((60, 0.0, 0.0), (61, 0.0, 0.0), (61, 0.0, 0.0)),
     {"max_abs": 1e-12, "relative_l2": 1e-12}),
    (_order_rows((60, 0.0, 0.0), (61, 0.0, 0.0)),
     {"max_abs": 1e-12, "relative_l2": 1e-12, "extra": 0.0}),
])
def test_order_effect_rejects_duplicate_rows_and_extra_tolerances(
        rows: list[dict[str, float]], tolerance: dict[str, float]) -> None:
    """A tampered reduction or tolerance object cannot silently change the decision rule."""
    with pytest.raises(ValueError):
        load_module("analyze_t3_rev").classify_order_effect(rows, tolerance)


@pytest.mark.parametrize("terminal, expected", [
    ({"terminal_reason": "confirmed_penetration", "terminal_cycle": 80,
      "first_hit_cycle": 77, "confirmed_cycle": 80},
     "PASS_CONFIRMED_FRACTURE_TRAJECTORY"),
    ({"terminal_reason": "right_censored", "terminal_cycle": 150,
      "first_hit_cycle": None, "confirmed_cycle": None},
     "PASS_NO_CONFIRMED_FRACTURE_BY_C150"),
    ({"terminal_reason": "coupled_fixed_point_nonconvergence", "cycle": 64, "substep": 4},
     "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE"),
    ({"terminal_reason": "newton_nonconvergence", "cycle": 64, "substep": 4},
     "FAIL_NEWTON_NONCONVERGENCE"),
    ({"terminal_reason": "startup_failure"}, "FAIL_STARTUP"),
    ({"terminal_reason": "runtime_failure"}, "FAIL_RUNTIME"),
])
def test_terminal_classes_remain_distinct(terminal: dict[str, object], expected: str) -> None:
    """Terminal outcomes cannot be collapsed into a generic unsuccessful result."""
    assert load_module("validate_t3_rev_terminal").classify_terminal(terminal) == expected


@pytest.mark.parametrize("terminal", [
    {"terminal_reason": "right_censored", "terminal_cycle": 149},
    {"terminal_reason": "right_censored", "terminal_cycle": 150,
     "first_hit_cycle": 149, "confirmed_cycle": None},
    {"terminal_reason": "confirmed", "terminal_cycle": 80,
     "first_hit_cycle": 77, "confirmed_cycle": 80},
    {"terminal_reason": "confirmed_penetration", "terminal_cycle": 80,
     "first_hit_cycle": 76, "confirmed_cycle": 80},
    {"terminal_reason": "coupled_fixed_point_nonconvergence", "cycle": True, "substep": 4},
    {"terminal_reason": "unclassified_failure"},
])
def test_terminal_classification_rejects_wrong_cycle_type_and_unknown_reason(
        terminal: dict[str, object]) -> None:
    """Type/semantic substitutions cannot turn a failure into an accepted terminal result."""
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError):
        module.classify_terminal(terminal)


def test_terminal_validator_requires_authoritative_canonical_lock_bytes(tmp_path: Path) -> None:
    """Whitespace-equivalent JSON cannot replace the bytes hashed into the launch credential."""
    module = load_module("validate_t3_rev_terminal")

    class Protocol:
        @staticmethod
        def canonical_json_bytes(value: object) -> bytes:
            assert value == {"case_id": "T3_rev_loading_order"}
            return b'{"case_id":"T3_rev_loading_order"}'

    path = tmp_path / "lock.json"
    path.write_bytes(b'{"case_id":"T3_rev_loading_order"}')
    module.require_canonical_lock_bytes(Protocol(), path, {"case_id": "T3_rev_loading_order"})
    path.write_bytes(b'{ "case_id": "T3_rev_loading_order" }\n')
    with pytest.raises(module.TerminalValidationError, match="canonical"):
        module.require_canonical_lock_bytes(Protocol(), path, {"case_id": "T3_rev_loading_order"})


def test_order_effect_rejects_reconfigured_tolerance_and_uses_own_event_boundary() -> None:
    """The published 1e-12 rule is immutable, and a significant own event is persistent."""
    module = load_module("analyze_t3_rev")
    rows = [
        {"cycle": 60.0, "max_abs": 2e-12, "relative_l2": 0.0},
        {"cycle": 61.0, "max_abs": 0.0, "relative_l2": 0.0},
        {"cycle": 62.0, "max_abs": 0.0, "relative_l2": 0.0},
        {"comparison": "own_event_confirmed", "cycle": 62.0,
         "max_abs": 2e-12, "relative_l2": 0.0},
    ]
    exact = {"max_abs": 1e-12, "relative_l2": 1e-12}
    assert module.classify_order_effect(rows, exact) == \
        "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    with pytest.raises(ValueError, match="exact"):
        module.classify_order_effect(rows[:3], {"max_abs": 1e-13, "relative_l2": 1e-12})


def test_csv_writer_has_deterministic_union_schema_for_mixed_availability(tmp_path: Path) -> None:
    """Unavailable and fully reduced rows share a deterministic, non-dropping CSV schema."""
    module = load_module("analyze_t3_rev")
    path = tmp_path / "mixed.csv"
    module._write_csv(path, [
        {"comparison": "same_cycle", "cycle": 60, "availability": "UNAVAILABLE"},
        {"comparison": "same_cycle", "cycle": 61, "availability": "AVAILABLE", "field": "damage", "max_abs": 0.0},
    ])
    assert path.read_text(encoding="utf-8").splitlines() == [
        "comparison,cycle,availability,field,max_abs",
        "same_cycle,60,UNAVAILABLE,,",
        "same_cycle,61,AVAILABLE,damage,0.0",
    ]


@pytest.mark.parametrize(("classification", "expected"), [
    ("PASS_CONFIRMED_FRACTURE_TRAJECTORY", "PASS_TERMINAL_ADJUDICATION"),
    ("PASS_NO_CONFIRMED_FRACTURE_BY_C150", "PASS_TERMINAL_ADJUDICATION"),
    ("FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE", "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE"),
    ("FAIL_NEWTON_NONCONVERGENCE", "FAIL_NEWTON_NONCONVERGENCE"),
    ("FAIL_STARTUP", "FAIL_STARTUP"),
    ("FAIL_RUNTIME", "FAIL_RUNTIME"),
])
def test_terminal_adjudication_status_is_outcome_specific(
        classification: str, expected: str) -> None:
    """Failure evidence produces a failure adjudication, never a blanket PASS receipt."""
    assert load_module("validate_t3_rev_terminal").terminal_adjudication_status(classification) == expected


def test_terminal_validator_requires_exact_canonical_seal_bytes(tmp_path: Path) -> None:
    """The seal digest is meaningful only for the builder's canonical bytes."""
    module = load_module("validate_t3_rev_terminal")
    payload = {"a": 1}
    path = tmp_path / "seal.json"
    path.write_bytes(b'{"a":1}\n')
    assert module.require_canonical_seal_bytes(path, payload) == hashlib.sha256(b'{"a":1}\n').hexdigest()
    path.write_bytes(b'{ "a": 1 }\n')
    with pytest.raises(module.TerminalValidationError, match="canonical"):
        module.require_canonical_seal_bytes(path, payload)


def test_order_effect_two_late_differences_then_terminal_convergence_is_transient() -> None:
    """The terminal converged suffix, not the count of earlier differences, controls transience."""
    module = load_module("analyze_t3_rev")
    rows = _order_rows(
        (60, 2e-12, 0.0),
        (61, 0.0, 2e-12),
        (62, 1e-12, 1e-12),
    )
    assert module.classify_order_effect(rows, module.EXACT_TOLERANCES) == \
        "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"


def test_order_effect_event_timing_delta_is_persistent_even_when_fields_match() -> None:
    """A shifted first-hit or confirmation cycle is itself a persistent order effect."""
    module = load_module("analyze_t3_rev")
    rows = [
        *_order_rows((60, 0.0, 0.0), (61, 0.0, 0.0), (62, 0.0, 0.0)),
        {
            "comparison": "own_event_first_hit",
            "cycle": 62.0,
            "left_cycle": 60.0,
            "right_cycle": 61.0,
            "max_abs": 0.0,
            "relative_l2": 0.0,
        },
        {
            "comparison": "own_event_confirmed",
            "cycle": 62.0,
            "left_cycle": 62.0,
            "right_cycle": 62.0,
            "max_abs": 0.0,
            "relative_l2": 0.0,
        },
    ]
    assert module.classify_order_effect(rows, module.EXACT_TOLERANCES) == \
        "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"


def test_order_effect_early_difference_with_converged_terminal_suffix_is_transient() -> None:
    """A real early order effect can converge before the terminal boundary."""
    module = load_module("analyze_t3_rev")
    rows = _order_rows(
        (20, 2e-12, 0.0),
        (60, 0.0, 0.0),
        (61, 0.0, 0.0),
        (62, 0.0, 0.0),
    )
    assert module.classify_order_effect(rows, module.EXACT_TOLERANCES) == \
        "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"


def test_order_effect_is_unavailable_when_an_own_event_boundary_is_unavailable() -> None:
    """Missing own-event evidence cannot be discarded from the scientific classification."""
    module = load_module("analyze_t3_rev")
    rows = [
        *_order_rows((60, 0.0, 0.0), (61, 0.0, 0.0), (62, 0.0, 0.0)),
        {"comparison": "own_event_first_hit", "cycle": None,
         "left_cycle": None, "right_cycle": None, "availability": "UNAVAILABLE"},
    ]
    assert module.classify_order_effect(rows, module.EXACT_TOLERANCES) == "UNAVAILABLE"


def _write_canonical_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii"))


def _matlab_dataset(group: h5py.Group, name: str, value: np.ndarray) -> None:
    stored = np.transpose(value, axes=tuple(reversed(range(value.ndim)))) if value.ndim else value
    dataset = group.create_dataset(name, data=stored)
    dataset.attrs["MATLAB_class"] = np.bytes_("double")


def _matlab_char(group: h5py.Group, name: str, value: str) -> h5py.Dataset:
    codes = np.asarray([ord(character) for character in value], dtype=np.uint16).reshape(-1, 1)
    dataset = group.create_dataset(name, data=codes)
    dataset.attrs["MATLAB_class"] = np.bytes_("char")
    return dataset


def _write_state0(path: Path) -> None:
    with h5py.File(path, "w") as handle:
        group = handle.create_group("state0")
        group.attrs["MATLAB_class"] = np.bytes_("struct")
        _matlab_dataset(group, "d_node", np.full((4, 1), 0.09, dtype=np.float64))
        _matlab_dataset(group, "alpha_bar_gp", np.zeros((1, 4), dtype=np.float64))


def _write_mesh(path: Path, identities: dict[str, str]) -> None:
    coordinates = np.asarray([
        [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0],
    ], dtype=np.float64)
    connectivity = np.asarray([[1.0, 2.0, 3.0, 4.0]], dtype=np.float64)
    with h5py.File(path, "w") as handle:
        group = handle.create_group("mesh_geometry")
        group.attrs["MATLAB_class"] = np.bytes_("struct")
        _matlab_dataset(group, "node_coords", coordinates)
        _matlab_dataset(group, "connectivity", connectivity)
        _matlab_char(group, "mesh_sha256", identities["mesh_sha256"])
        _matlab_char(group, "connectivity_sha256", identities["connectivity_sha256"])
        _matlab_char(group, "mesh_sha256_semantics", identities["mesh_sha256_semantics"])
        _matlab_char(group, "element_ordering_id", identities["element_ordering_id"])
        _matlab_char(group, "gp_ordering_id", identities["gp_ordering_id"])


def _toy_mesh_identity() -> dict[str, str]:
    coordinates = np.asarray([
        [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0],
    ], dtype="<f8")
    connectivity = np.asarray([[1, 2, 3, 4]], dtype="<i8")
    connectivity_bytes = connectivity.tobytes(order="F")
    return {
        "mesh_sha256": hashlib.sha256(
            coordinates.tobytes(order="F") + connectivity_bytes).hexdigest(),
        "connectivity_sha256": hashlib.sha256(connectivity_bytes).hexdigest(),
        "mesh_sha256_semantics": "sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1",
        "element_ordering_id": "q4_connectivity_1_based_v1",
        "gp_ordering_id": "q4_2x2_native_order_v1",
    }


def _write_cycle_shard(
        path: Path, cycle: int, identities: dict[str, str], execution_digest: str,
        *, offset: float = 0.0) -> None:
    damage_steps = np.linspace(0.0, 4e-5, 5, dtype=np.float64)
    d_node = np.tile(0.09 + 1e-3 * cycle + damage_steps + offset, (4, 1))
    d_gp = np.broadcast_to(d_node.mean(axis=0).reshape(1, 1, 5), (1, 4, 5)).copy()
    alpha = np.broadcast_to(
        (1e-3 * cycle + np.linspace(0.0, 4e-5, 5)).reshape(1, 1, 5),
        (1, 4, 5),
    ).copy()
    f_alpha = np.minimum(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    raw = np.broadcast_to(np.arange(1.0, 6.0).reshape(1, 1, 5), (1, 4, 5)).copy()
    g_gp = (1.0 - d_gp) ** 2
    with h5py.File(path, "w") as handle:
        group = handle.create_group("shard")
        group.attrs["MATLAB_class"] = np.bytes_("struct")
        values = {
            "cycle": np.asarray([[float(cycle)]], dtype=np.float64),
            "d_node": d_node,
            "d_gp": d_gp,
            "alpha_bar_gp": alpha,
            "f_alpha_gp": f_alpha,
            "psi_raw_gp": raw,
            "g_gp": g_gp,
            "psi_active_gp": g_gp * raw,
            "psi_raw_cyclemax_gp": np.max(raw, axis=2),
            "substep_ordinal": np.arange(1.0, 6.0).reshape(1, 5),
            "load_factor": np.asarray([[0.25, 0.5, 0.75, 1.0, 0.0]]),
            "raw_step_zero_based": (5 * (cycle - 1) + np.arange(5.0)).reshape(1, 5),
        }
        for name, value in values.items():
            _matlab_dataset(group, name, value)
        refs = handle.create_group("#refs#")
        loading = _matlab_char(refs, "loading", "loading")
        unloading = _matlab_char(refs, "unloading", "unloading")
        branch = np.empty((5, 1), dtype=h5py.ref_dtype)
        branch[:4, 0] = loading.ref
        branch[4, 0] = unloading.ref
        cell = group.create_dataset("branch", data=branch)
        cell.attrs["MATLAB_class"] = np.bytes_("cell")
        for name in (
                "mesh_sha256", "element_ordering_id", "gp_ordering_id",
                "state_semantics_id", "runtime_lock_sha256",
                "family_contract_sha256", "case_physics_contract_sha256"):
            _matlab_char(group, name, identities[name])
        _matlab_char(group, "execution_input_lock_sha256", execution_digest)


def _matlab_filled_dataset(
        group: h5py.Group, name: str, logical_shape: tuple[int, ...], value: float) -> None:
    """Create a dimensionally faithful MATLAB array without materializing stored chunks."""
    stored_shape = tuple(reversed(logical_shape))
    dataset = group.create_dataset(
        name, shape=stored_shape, dtype=np.float64, chunks=True, fillvalue=float(value),
    )
    dataset.attrs["MATLAB_class"] = np.bytes_("double")


def _write_dimensional_state0(path: Path, n_node: int, n_elem: int) -> None:
    with h5py.File(path, "w") as handle:
        group = handle.create_group("state0")
        group.attrs["MATLAB_class"] = np.bytes_("struct")
        _matlab_filled_dataset(group, "d_node", (n_node, 1), 0.09)
        _matlab_filled_dataset(group, "alpha_bar_gp", (n_elem, 4), 0.0)


def _write_dimensional_cycle_shard(
        path: Path, cycle: int, identities: dict[str, str], execution_digest: str,
        n_node: int, n_elem: int) -> None:
    """Write exact production row counts using HDF5 fill values for compact fixtures."""
    damage = 0.09 + 1e-3 * cycle
    alpha = 1e-3 * cycle
    f_alpha = min(1.0, (1.0 - ((alpha - 0.5) / (alpha + 0.5))) ** 2)
    g_value = (1.0 - damage) ** 2
    with h5py.File(path, "w") as handle:
        group = handle.create_group("shard")
        group.attrs["MATLAB_class"] = np.bytes_("struct")
        for name, logical_shape, value in (
                ("d_node", (n_node, 5), damage),
                ("d_gp", (n_elem, 4, 5), damage),
                ("alpha_bar_gp", (n_elem, 4, 5), alpha),
                ("f_alpha_gp", (n_elem, 4, 5), f_alpha),
                ("psi_raw_gp", (n_elem, 4, 5), 1.0),
                ("g_gp", (n_elem, 4, 5), g_value),
                ("psi_active_gp", (n_elem, 4, 5), g_value),
                ("psi_raw_cyclemax_gp", (n_elem, 4), 1.0)):
            _matlab_filled_dataset(group, name, logical_shape, value)
        for name, value in {
            "cycle": np.asarray([[float(cycle)]], dtype=np.float64),
            "substep_ordinal": np.arange(1.0, 6.0).reshape(1, 5),
            "load_factor": np.asarray([[0.25, 0.5, 0.75, 1.0, 0.0]]),
            "raw_step_zero_based": (5 * (cycle - 1) + np.arange(5.0)).reshape(1, 5),
        }.items():
            _matlab_dataset(group, name, value)
        refs = handle.create_group("#refs#")
        loading = _matlab_char(refs, "loading", "loading")
        unloading = _matlab_char(refs, "unloading", "unloading")
        branch = np.empty((5, 1), dtype=h5py.ref_dtype)
        branch[:4, 0] = loading.ref
        branch[4, 0] = unloading.ref
        cell = group.create_dataset("branch", data=branch)
        cell.attrs["MATLAB_class"] = np.bytes_("cell")
        for name in (
                "mesh_sha256", "element_ordering_id", "gp_ordering_id",
                "state_semantics_id", "runtime_lock_sha256",
                "family_contract_sha256", "case_physics_contract_sha256"):
            _matlab_char(group, name, identities[name])
        _matlab_char(group, "execution_input_lock_sha256", execution_digest)


def _terminal_manifest_entries(root: Path) -> list[dict[str, str]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
        if path.is_file() and path.name != "TERMINAL_MANIFEST.json"
    ]


def _write_package_checksum(root: Path) -> None:
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file()
         and path.name not in {"SHA256SUMS.txt", "TERMINAL_MANIFEST.json"}),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    (root / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
            for path in paths
        ),
        encoding="ascii",
        newline="\n",
    )


def _reclose_completed_package(root: Path) -> None:
    """Reclose a mutated completed fixture so semantic checks, not stale hashes, decide it."""
    manifest = strict_json(root / "TERMINAL_MANIFEST.json")
    snapshot = root / "INPUT_SNAPSHOT.json"
    if snapshot.is_file():
        manifest["physical_input_sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    _write_package_checksum(root)
    manifest["files"] = _terminal_manifest_entries(root)
    _write_canonical_json(root / "TERMINAL_MANIFEST.json", manifest)


def _generated_terminal_protocol(tmp_path: Path):
    builder = load_module("build_t3_rev_extension")
    extension = tmp_path / "extension"
    builder.build_extension(BASE, extension, "a" * 40)
    manifest = strict_json(extension / "EXTENSION_SOURCE_MANIFEST.json")
    protocol_digest = next(
        item["sha256"] for item in manifest["shadow_files"]
        if item["path"] == "toy_road_protocol.py"
    )
    launch = load_module("launch_t3_rev")
    protocol = launch.load_protocol(
        extension / "toy_road_protocol.py", "test_terminal_generated_protocol", protocol_digest
    )
    return extension, protocol


def _build_authenticated_terminal_package(
        protocol, root: Path, *, terminal_cycle: int, right_censored: bool,
        forbidden_first_hit: int | None = None, offset: float = 0.0,
        offsets: dict[int, float] | None = None,
        execution_lock: dict[str, object] | None = None,
        case_id: str = "T3_rev_loading_order", include_mesh: bool = False,
        case_physics: dict[str, object] | None = None,
        input_assets_root: Path | None = None,
        component_identities: dict[str, str] | None = None) -> Path:
    root.mkdir(parents=True)
    (root / "substeps").mkdir()
    (root / "qualification").mkdir()
    family = "1" * 64
    case = "2" * 64
    runtime = "3" * 64
    source = "4" * 40
    lock = execution_lock or protocol.build_execution_input_lock(
        authorization_scope="production_authorized",
        role=case_id,
        family_contract_sha256=family,
        case_physics_contract_sha256=case,
        source_commit=source,
        runtime_lock_sha256=runtime,
        source_manifest_sha256="5" * 64,
        runtime_expectations={
            "matlab": {
                "release": "R2025b", "update": "Update 5", "version": "25.2.0.3177638",
                "computer": "PCWIN64", "executable_sha256": "6" * 64,
                "blas": "locked BLAS", "lapack": "locked LAPACK",
                "absolute_path_order": [str(root.parent / f"path-{index}") for index in range(8)],
            },
            "binary_sha256": {
                "initial": "7" * 64, "AMOR": "8" * 64,
                "AT1_HISTORY_FATIGUE": "9" * 64, "cholmod2": "a" * 64,
            },
        },
        roots={name: str(root.parent / name) for name in (
            "output", "work", "temp", "tmp", "pref", "cache", "matlab_startup_pref"
        )},
        launch_timestamp_utc="2026-08-24T12:00:00Z",
        no_clobber_receipt_id="terminal-package-fixture",
    )
    lock_bytes = protocol.canonical_json_bytes(lock)
    (root / "EXECUTION_INPUT_LOCK.json").write_bytes(lock_bytes)
    execution_digest = hashlib.sha256(lock_bytes).hexdigest()
    mesh_identity = _toy_mesh_identity()
    identities = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "source_commit": str(lock["source_commit"]),
        "mesh_sha256": mesh_identity["mesh_sha256"],
        "element_ordering_id": mesh_identity["element_ordering_id"],
        "gp_ordering_id": mesh_identity["gp_ordering_id"],
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": str(lock["runtime_lock_sha256"]),
        "family_contract_sha256": str(lock["family_contract_sha256"]),
        "case_physics_contract_sha256": str(lock["case_physics_contract_sha256"]),
        "physical_input_sha256": "c" * 64,
        "solver_sha256": "d" * 64,
        "recovery_sha256": "e" * 64,
        "exporter_sha256": "f" * 64,
        "numerical_gate_contract_sha256": "0" * 64,
        "event_contract_sha256": "1" * 64,
    }
    if component_identities is not None:
        identities.update({
            name: value for name, value in component_identities.items()
            if name in identities
        })
    _write_state0(root / "STATE0.mat")
    _write_state0(root / "state0_analysis.mat")
    mesh_file_identity = {**mesh_identity, **{
        name: (component_identities or identities)[name] for name in (
            "mesh_sha256", "connectivity_sha256", "mesh_sha256_semantics",
            "element_ordering_id", "gp_ordering_id")
        if name in (component_identities or identities)
    }}
    _write_mesh(root / "mesh_geometry.mat", mesh_file_identity)
    snapshot = {
        "schema_version": "toy_road_p0_input_snapshot_v1",
        "authorization_scope": "production_authorized",
        "case_id": case_id,
        "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": execution_digest,
        "input_assets_root": str((input_assets_root or root.parent / "input-assets").resolve()),
        "mesh_sha256": identities["mesh_sha256"],
        "changed_axes": ["loading.blocks"],
        "case_physics": case_physics or {"mesh": mesh_file_identity},
        "fresh_state0": True,
        "resume_allowed": False,
        "line_search": False,
        "cycle_jump": False,
    }
    _write_canonical_json(root / "INPUT_SNAPSHOT.json", snapshot)
    identities["physical_input_sha256"] = hashlib.sha256(
        (root / "INPUT_SNAPSHOT.json").read_bytes()).hexdigest()
    matlab = lock["runtime_expectations"]["matlab"]
    _write_canonical_json(root / "RUNTIME_RECEIPT.json", {
        "status": "PASS", "authorization_scope": "production_authorized",
        "case_id": case_id, "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "matlab_version": f'{matlab["version"]} ({matlab["release"]}) {matlab["update"]}',
        "computer": matlab["computer"], "blas": matlab["blas"], "lapack": matlab["lapack"],
    })
    for cycle in range(1, terminal_cycle + 1):
        _write_cycle_shard(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            cycle,
            identities,
            execution_digest,
            offset=(offsets or {}).get(cycle, offset),
        )
    trace_rows = [
        ["production_authorized", case_id, 5, 4, 1, 1,
         2e-4, 8e-4, 3e-4, 8e-4, 1e-13],
        ["production_authorized", case_id, 5, 4, 2, 2,
         1e-5, 6e-4, 2e-5, 3e-5, 0.0],
    ]
    trace = root / "qualification" / "C5_STAGGER_TRACE.csv"
    trace.write_text(
        ",".join(protocol.TRACE_COLUMNS) + "\n"
        + "".join(",".join(str(value) for value in row) + "\n" for row in trace_rows),
        encoding="ascii", newline="\n",
    )
    final = trace_rows[-1]
    _write_canonical_json(root / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json", {
        "authorization_scope": "production_authorized", "case_id": case_id,
        "cycle": 5, "substep_ordinal": 4, "status": "PASS", "passed": True,
        "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
        "trace_row_count": 2, "reassembly_count": 2,
        "final_stagger_iteration": 2, "final_reassembly_ordinal": 2,
        "final_displacement_residual": final[6], "final_raw_phase_residual": final[7],
        "final_projected_phase_kkt": final[8], "final_consecutive_stagger_delta": final[9],
        "final_primal_feasibility": final[10], "displacement_residual_threshold": 4e-4,
        "projected_phase_kkt_threshold": 4e-4, "consecutive_stagger_delta_threshold": 1e-3,
        "primal_feasibility_threshold": 1e-12,
    })
    first_hit = forbidden_first_hit if right_censored else terminal_cycle - 3
    confirmed = None if right_censored else terminal_cycle
    event = {
        "authorization_scope": "production_authorized", "case_id": case_id,
        "first_hit_cycle": first_hit, "confirmed_cycle": confirmed,
        "terminal_cycle": terminal_cycle, "peak_substep_ordinal": 4,
        "cycle_shard": f"substeps/cycle_{terminal_cycle:04d}.mat",
        "cycle_shard_sha256": hashlib.sha256(
            (root / "substeps" / f"cycle_{terminal_cycle:04d}.mat").read_bytes()
        ).hexdigest(),
    }
    _write_canonical_json(root / "EVENT_METADATA.json", event)
    _write_canonical_json(root / "TERMINAL_RESULT.json", {
        "authorization_scope": "production_authorized", "case_id": case_id,
        "terminal_reason": "right_censored" if right_censored else "confirmed_penetration",
        "terminal_cycle": terminal_cycle, "first_hit_cycle": first_hit,
        "confirmed_cycle": confirmed,
    })
    _write_package_checksum(root)
    manifest = {
        "authorization_scope": "production_authorized", "case_id": case_id,
        **identities, "execution_input_lock_sha256": execution_digest,
        "files": _terminal_manifest_entries(root),
    }
    _write_canonical_json(root / "TERMINAL_MANIFEST.json", manifest)
    return root


def test_right_censored_terminal_authentication_reuses_authoritative_components(tmp_path: Path) -> None:
    """A genuine c150 package authenticates without pretending a hit or confirmation occurred."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "right-censored", terminal_cycle=150, right_censored=True
    )
    receipt = load_module("validate_t3_rev_terminal").authenticate_completed_package(protocol, root)
    assert receipt["status"] == "PASS"
    assert receipt["case_id"] == "T3_rev_loading_order"
    assert receipt["package_root"] == str(root.resolve())


def test_right_censored_terminal_authentication_rejects_a_hidden_hit(tmp_path: Path) -> None:
    """Hash-closed c150 bytes still fail when event metadata claims a first hit."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "bad-right-censored", terminal_cycle=150,
        right_censored=True, forbidden_first_hit=149,
    )
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="right-censored"):
        module.authenticate_completed_package(protocol, root)


def test_confirmed_terminal_authentication_keeps_authoritative_event_semantics(tmp_path: Path) -> None:
    """The c150 variant does not weaken the generated protocol's confirmed-package path."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "confirmed", terminal_cycle=5, right_censored=False
    )
    receipt = load_module("validate_t3_rev_terminal").authenticate_completed_package(protocol, root)
    assert receipt["status"] == "PASS"


def _write_pass_runtime_measurement(protocol, run_root: Path) -> dict[str, object]:
    receipts = run_root / "receipts"
    lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
    launch_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    lock = strict_json(lock_path)
    expectations = lock["runtime_expectations"]
    measurement = {
        "schema_version": "toy_road_runtime_measurement_v1",
        "protocol_version": protocol.PROTOCOL_VERSION,
        "authorization_scope": "production_authorized",
        "status": "PASS",
        "producer_entrypoint_authorized": True,
        "execution_input_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "matlab": expectations["matlab"],
        "binary_sha256": expectations["binary_sha256"],
        "authorized_entrypoint": "main_toy_road_family_case",
        "upstream_authorized_entrypoint": "run_toy_road_runtime_bridge",
        "upstream_launch_receipt_path": str(launch_path),
        "upstream_launch_receipt_sha256": hashlib.sha256(launch_path.read_bytes()).hexdigest(),
        "case_id": lock["case_id"],
        "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
    }
    _write_canonical_json(receipts / "T3_REV_RUNTIME_MEASUREMENT.json", measurement)
    protocol.validate_runtime_measurement(lock, measurement)
    return measurement


def _rev_completed_identity_kwargs(inputs: dict[str, Path]) -> dict[str, object]:
    case_contract = strict_json(
        inputs["extension_root"] / "CASE_PHYSICS_CONTRACTS.json"
    )["cases"]["T3_rev_loading_order"]
    published = strict_json(
        inputs["repo_root"] / "analysis" / "toy_road_t3_mechanism_20260819" /
        "evidence" / "TERMINAL_MANIFEST.json"
    )
    identities = {
        name: published[name] for name in (
            "solver_sha256", "recovery_sha256", "exporter_sha256",
            "numerical_gate_contract_sha256", "event_contract_sha256",
        )
    }
    identities.update({
        name: case_contract["physics"]["mesh"][name] for name in (
            "mesh_sha256", "connectivity_sha256", "mesh_sha256_semantics",
            "element_ordering_id", "gp_ordering_id",
        )
    })
    return {
        "case_physics": case_contract["physics"],
        "input_assets_root": inputs["input_assets_root"],
        "component_identities": identities,
    }


def _launched_terminal_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    launch = load_module("launch_t3_rev")
    inputs = _launcher_inputs(launch, tmp_path)
    launch.SUITESPARSE_ROOT = Path(r"C:\SuiteSparse\SuiteSparse-dev")
    inputs["griphfith_root"] = Path(r"C:\q4diag\griphfith-pf-rebuild-355d4c83")
    monkeypatch.setattr(launch, "matlab_processes", lambda: [])
    overlay_validator = launch.require_materialized_runtime_overlay
    _allow_test_matlab_identity(launch, monkeypatch)

    class Process:
        pid = 2468

    monkeypatch.setattr(launch, "Popen", lambda *args, **kwargs: Process())
    launch.launch_t3_rev(**inputs)
    monkeypatch.setattr(launch, "require_materialized_runtime_overlay", overlay_validator)
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    protocol_digest = next(
        item["sha256"] for item in manifest["shadow_files"]
        if item["path"] == "toy_road_protocol.py"
    )
    protocol = launch.load_protocol(
        inputs["extension_root"] / "toy_road_protocol.py",
        "launched_terminal_fixture_protocol",
        protocol_digest,
    )
    _write_pass_runtime_measurement(protocol, inputs["run_root"])
    lock = strict_json(inputs["run_root"] / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    _build_authenticated_terminal_package(
        protocol,
        inputs["run_root"] / "output",
        terminal_cycle=5,
        right_censored=False,
        execution_lock=lock,
        **_rev_completed_identity_kwargs(inputs),
    )
    for path in lock["writable_roots"].values():
        Path(path).mkdir(parents=True, exist_ok=True)
    return launch, protocol, inputs


def test_terminal_validator_authenticates_complete_launch_to_package_chain(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A real launch lock, overlay, PASS measurement, and package form one bound chain."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    module = load_module("validate_t3_rev_terminal")
    result = module._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"],
        seal_path=inputs["seal_path"],
        run_root=inputs["run_root"],
        launch=launch,
    )
    assert result["status"] == "PASS_TERMINAL_ADJUDICATION"
    assert result["terminal_authentication"]["package_root"] == str(
        (inputs["run_root"] / "output").resolve()
    )
    assert result["authorization_capability"] is None
    assert result["follow_on_authorized"] is False


@pytest.mark.parametrize("missing", [
    "INPUT_SNAPSHOT.json", "RUNTIME_RECEIPT.json", "mesh_geometry.mat",
])
def test_completed_authentication_requires_each_production_identity_artifact(
        tmp_path: Path, missing: str) -> None:
    """A hash-closed completed package still needs every producer identity artifact."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "completed", terminal_cycle=5, right_censored=False,
    )
    (root / missing).unlink()
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="production identity artifact"):
        module.authenticate_completed_package(protocol, root)


def test_completed_authentication_rejects_short_matlab_version_token(tmp_path: Path) -> None:
    """Completed output follows the same archived full-version receipt schema as failures."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "completed", terminal_cycle=5, right_censored=False,
    )
    receipt = strict_json(root / "RUNTIME_RECEIPT.json")
    receipt["matlab_version"] = "25.2.0.3177638"
    _write_canonical_json(root / "RUNTIME_RECEIPT.json", receipt)
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="runtime receipt"):
        module.authenticate_completed_package(protocol, root)


def test_completed_authentication_rejects_reclosed_mesh_array_tamper(tmp_path: Path) -> None:
    """Mesh metadata cannot hide changed geometry bytes in a reclosed package."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "completed", terminal_cycle=5, right_censored=False,
    )
    with h5py.File(root / "mesh_geometry.mat", "r+") as handle:
        handle["mesh_geometry/connectivity"][0, 0] = 2.0
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="mesh bytes|mesh.*identity"):
        module.authenticate_completed_package(protocol, root)


def test_completed_chain_rejects_reclosed_altered_physical_identity(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Rehashing a changed case snapshot cannot detach it from the sealed case contract."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    output = inputs["run_root"] / "output"
    snapshot = strict_json(output / "INPUT_SNAPSHOT.json")
    snapshot["case_physics"]["loading"]["blocks"][0][2] = 0.127
    _write_canonical_json(output / "INPUT_SNAPSHOT.json", snapshot)
    _reclose_completed_package(output)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="physical|case contract"):
        module._validate_terminal(
            output,
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_completed_chain_rejects_reclosed_altered_source_identity(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A replacement source claim cannot be made authoritative by rehashing the package."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    output = inputs["run_root"] / "output"
    snapshot = strict_json(output / "INPUT_SNAPSHOT.json")
    snapshot["source_commit"] = "0" * 40
    _write_canonical_json(output / "INPUT_SNAPSHOT.json", snapshot)
    manifest = strict_json(output / "TERMINAL_MANIFEST.json")
    manifest["source_commit"] = "0" * 40
    _write_canonical_json(output / "TERMINAL_MANIFEST.json", manifest)
    _reclose_completed_package(output)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="source|physical|identity"):
        module._validate_terminal(
            output,
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def _prepare_numerical_failure(
        protocol, inputs: dict[str, Path], classification: str, *,
        cycle: int = 6, substep: int = 4,
        newton_layer: str = "phase_newton") -> None:
    run_root = inputs["run_root"]
    output = run_root / "output"
    lock_path = run_root / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json"
    launch_path = run_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    measurement_path = run_root / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    lock = strict_json(lock_path)
    cases = strict_json(inputs["extension_root"] / "CASE_PHYSICS_CONTRACTS.json")
    case_contract = cases["cases"]["T3_rev_loading_order"]
    terminal_files = (
        "TERMINAL_RESULT.json", "EVENT_METADATA.json", "TERMINAL_MANIFEST.json",
        "SHA256SUMS.txt", "EXECUTION_INPUT_LOCK.json",
    )
    (output / "STATE0.mat").unlink()
    for name in terminal_files:
        (output / name).unlink(missing_ok=True)
    execution_digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    mesh_identity = case_contract["physics"]["mesh"]
    mesh_sha = mesh_identity["mesh_sha256"]
    shard_identities = {
        "mesh_sha256": mesh_sha,
        "element_ordering_id": mesh_identity["element_ordering_id"],
        "gp_ordering_id": mesh_identity["gp_ordering_id"],
        "state_semantics_id": "five_substep_post_commit_history_v1",
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
    }
    shutil.copy2(
        ROOT / "docs" / "toy_road_p0_repeatability_20260802" /
        "t2_material_state_failure_20260817" / "artifacts" / "output" /
        "mesh_geometry.mat",
        output / "mesh_geometry.mat",
    )
    with h5py.File(output / "mesh_geometry.mat", "r+") as handle:
        n_node = handle["mesh_geometry/node_coords"].shape[1]
        n_elem = handle["mesh_geometry/connectivity"].shape[1]
        connectivity_codes = np.asarray(
            [ord(character) for character in mesh_identity["connectivity_sha256"]],
            dtype=np.uint16,
        ).reshape(-1, 1)
        handle["mesh_geometry/connectivity_sha256"][...] = connectivity_codes
    _write_dimensional_state0(output / "state0_analysis.mat", n_node, n_elem)
    completed = cycle - 1
    for shard_path in (output / "substeps").glob("cycle_*.mat"):
        shard_path.unlink()
    for completed_cycle in range(1, completed + 1):
        shard_path = output / "substeps" / f"cycle_{completed_cycle:04d}.mat"
        _write_dimensional_cycle_shard(
            shard_path, completed_cycle, shard_identities, execution_digest,
            n_node, n_elem,
        )
    snapshot = {
        "schema_version": "toy_road_p0_input_snapshot_v1",
        "authorization_scope": "production_authorized",
        "case_id": "T3_rev_loading_order",
        "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "family_contract_sha256": lock["family_contract_sha256"],
        "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        "execution_input_lock_sha256": execution_digest,
        "input_assets_root": str(inputs["input_assets_root"]),
        "mesh_sha256": mesh_sha,
        "changed_axes": ["loading.blocks"],
        "case_physics": case_contract["physics"],
        "fresh_state0": True,
        "resume_allowed": False,
        "line_search": False,
        "cycle_jump": False,
    }
    _write_canonical_json(output / "INPUT_SNAPSHOT.json", snapshot)
    expectations = lock["runtime_expectations"]["matlab"]
    full_matlab_version = (
        f'{expectations["version"]} ({expectations["release"]}) '
        f'{expectations["update"]}'
    )
    _write_canonical_json(output / "RUNTIME_RECEIPT.json", {
        "status": "PASS", "authorization_scope": "production_authorized",
        "case_id": "T3_rev_loading_order", "source_commit": lock["source_commit"],
        "runtime_lock_sha256": lock["runtime_lock_sha256"],
        "matlab_version": full_matlab_version, "computer": expectations["computer"],
        "blas": expectations["blas"], "lapack": expectations["lapack"],
    })
    if classification == "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE":
        terminal_reason = "coupled_fixed_point_nonconvergence"
        layer = "coupled_damage_fixed_point"
        newton_failure = False
        error_identifier = "toyRoadP0:StaggeredSolveFailed"
        error_message = f"Stagger convergence failed at cycle {cycle} substep {substep}."
    else:
        terminal_reason = "newton_nonconvergence"
        layer = newton_layer
        newton_failure = True
        if layer == "displacement_newton":
            error_identifier = "toyRoadP0:DisplacementSolveFailed"
            error_message = "The displacement Newton solve failed."
        else:
            error_identifier = "toyRoadP0:PhaseSolveFailed"
            error_message = "The phase Newton solve failed."

    trace = output / "qualification" / "C5_STAGGER_TRACE.csv"
    receipt = output / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
    c5_trace_required = cycle > 5 or (cycle == 5 and substep >= 4)
    c5_pass_required = cycle > 5 or (cycle == 5 and substep == 5)
    if not c5_trace_required:
        trace.unlink(missing_ok=True)
        receipt.unlink(missing_ok=True)
    elif not c5_pass_required:
        receipt.unlink(missing_ok=True)
        if substep == 4 and classification == "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE":
            source_trace = ROOT / "docs" / "toy_road_p0_repeatability_20260802" / \
                "t2_material_state_failure_20260817" / "artifacts" / "output" / \
                "qualification" / "C5_STAGGER_TRACE.csv"
            trace.write_text(
                source_trace.read_text(encoding="ascii").replace(
                    "T2_material_state", "T3_rev_loading_order"),
                encoding="ascii", newline="\n",
            )
        elif substep == 4:
            trace.write_text(
                ",".join(protocol.TRACE_COLUMNS) + "\n", encoding="ascii", newline="\n",
            )
    _write_canonical_json(output / "RUN_RESULT.json", {
        "authorization_scope": "production_authorized", "case_id": "T3_rev_loading_order",
        "complete": False, "status": "failed", "error_identifier": error_identifier,
        "error_message": error_message,
    })
    with (run_root / "T3_REV.stderr.log").open("ab") as stream:
        stream.write((error_message + "\n").encode("utf-8"))
    required_relatives = [
        "launcher.pid", "T3_REV.stdout.log", "T3_REV.stderr.log",
        "output/INPUT_SNAPSHOT.json", "output/mesh_geometry.mat", "output/RUN_RESULT.json",
        "output/RUNTIME_RECEIPT.json", "output/state0_analysis.mat",
        "receipts/T3_REV_EXECUTION_INPUT_LOCK.json", "receipts/T3_REV_LAUNCH_RECEIPT.json",
        "receipts/T3_REV_RUNTIME_MEASUREMENT.json",
        *[f"output/substeps/cycle_{item:04d}.mat" for item in range(1, completed + 1)],
    ]
    if c5_trace_required:
        required_relatives.append("output/qualification/C5_STAGGER_TRACE.csv")
    if c5_pass_required:
        required_relatives.append("output/qualification/C5_NUMERICAL_GATE_RECEIPT.json")
    package = run_root / "T3_REV_FAILURE_PACKAGE"
    package.mkdir()
    artifacts: list[dict[str, object]] = []
    for relative in required_relatives:
        source = run_root / Path(relative)
        target = package / "artifacts" / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        artifacts.append({
            "path": f"artifacts/{Path(relative).as_posix()}",
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    artifacts.sort(key=lambda item: str(item["path"]))
    artifact_aggregate = hashlib.sha256(json.dumps(
        artifacts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "toy_road_t3_rev_immutable_failure_package_v1",
        "case_id": "T3_rev_loading_order", "status": classification,
        "source_run_root": str(run_root), "artifact_file_count": len(artifacts),
        "artifact_aggregate_sha256": artifact_aggregate, "artifacts": artifacts,
    }
    failure = {
        "schema_version": "toy_road_t3_rev_failure_classification_v1",
        "case_id": "T3_rev_loading_order", "status": classification,
        "failure_cycle": cycle, "failure_substep": substep, "failure_layer": layer,
        "newton_failure": newton_failure, "fixed_point_tolerance": 1e-3,
        "stagger_iteration_cap": 1000, "completed_cycle_shards": completed,
        "automatic_retry_performed": False,
    }
    identities = {
        "schema_version": "toy_road_t3_rev_failure_identity_v1",
        "producer": {
            "source_commit": lock["source_commit"],
            "source_manifest_sha256": lock["source_manifest_sha256"],
            "family_contract_sha256": lock["family_contract_sha256"],
            "case_physics_contract_sha256": lock["case_physics_contract_sha256"],
        },
        "runtime": {
            "runtime_lock_sha256": lock["runtime_lock_sha256"],
            "matlab": lock["runtime_expectations"]["matlab"],
            "binary_sha256": lock["runtime_expectations"]["binary_sha256"],
            "thread_settings": strict_json(inputs["seal_path"])["runtime_identity"]["thread_settings"],
        },
        "input": {
            "execution_input_lock_sha256": execution_digest,
            "input_snapshot_sha256": hashlib.sha256((output / "INPUT_SNAPSHOT.json").read_bytes()).hexdigest(),
            "mesh_sha256": mesh_sha, "output_root": str(output), "run_root": str(run_root),
        },
        "launch": {
            "seal_sha256": hashlib.sha256(inputs["seal_path"].read_bytes()).hexdigest(),
            "launch_receipt_sha256": hashlib.sha256(launch_path.read_bytes()).hexdigest(),
            "runtime_measurement_sha256": hashlib.sha256(measurement_path.read_bytes()).hexdigest(),
            "extension_source_manifest_sha256": hashlib.sha256(
                (inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json").read_bytes()
            ).hexdigest(),
        },
    }
    _write_canonical_json(package / "PACKAGE_MANIFEST.json", manifest)
    _write_canonical_json(package / "FAILURE_CLASSIFICATION.json", failure)
    _write_canonical_json(package / "SOURCE_RUNTIME_INPUT_IDENTITIES.json", identities)
    sums_paths = sorted(
        (path for path in package.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"),
        key=lambda path: path.relative_to(package).as_posix(),
    )
    (package / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(package).as_posix()}\n"
        for path in sums_paths
    ), encoding="ascii", newline="\n")
    terminal = {
        "schema_version": "toy_road_t3_rev_terminal_failure_v1",
        "status": classification, "case_id": "T3_rev_loading_order",
        "terminal_reason": terminal_reason,
        "failure_phase": "producer_after_pass_runtime_measurement",
        "cycle": cycle, "substep": substep,
        "seal_sha256": identities["launch"]["seal_sha256"],
        "run_root": str(run_root),
        "launch_receipt_sha256": identities["launch"]["launch_receipt_sha256"],
        "runtime_measurement_sha256": identities["launch"]["runtime_measurement_sha256"],
        "failure_package_manifest_sha256": hashlib.sha256(
            (package / "PACKAGE_MANIFEST.json").read_bytes()
        ).hexdigest(),
    }
    _write_canonical_json(run_root / "receipts" / "T3_REV_TERMINAL_FAILURE.json", terminal)


def _reclose_failure_package(inputs: dict[str, Path]) -> None:
    """Reclose a deliberately mutated failure fixture so semantic validators are reached."""
    run_root = inputs["run_root"]
    package = run_root / "T3_REV_FAILURE_PACKAGE"
    manifest_path = package / "PACKAGE_MANIFEST.json"
    manifest = strict_json(manifest_path)
    artifacts = manifest["artifacts"]
    for item in artifacts:
        path = package / item["path"]
        item["bytes"] = path.stat().st_size
        item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["artifact_aggregate_sha256"] = hashlib.sha256(json.dumps(
        artifacts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    _write_canonical_json(manifest_path, manifest)
    sums_paths = sorted(
        (path for path in package.rglob("*")
         if path.is_file() and path.name != "SHA256SUMS.txt"),
        key=lambda path: path.relative_to(package).as_posix(),
    )
    (package / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(package).as_posix()}\n" for path in sums_paths
    ), encoding="ascii", newline="\n")
    terminal_path = run_root / "receipts" / "T3_REV_TERMINAL_FAILURE.json"
    terminal = strict_json(terminal_path)
    terminal["failure_package_manifest_sha256"] = hashlib.sha256(
        manifest_path.read_bytes()).hexdigest()
    _write_canonical_json(terminal_path, terminal)


@pytest.mark.parametrize(("classification", "cycle", "substep", "newton_layer"), [
    ("FAIL_NEWTON_NONCONVERGENCE", 5, 1, "phase_newton"),
    ("FAIL_NEWTON_NONCONVERGENCE", 5, 2, "displacement_newton"),
    ("FAIL_NEWTON_NONCONVERGENCE", 5, 3, "phase_newton"),
    ("FAIL_NEWTON_NONCONVERGENCE", 5, 4, "displacement_newton"),
    ("FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE", 5, 4, "phase_newton"),
    ("FAIL_NEWTON_NONCONVERGENCE", 5, 5, "displacement_newton"),
    ("FAIL_NEWTON_NONCONVERGENCE", 6, 4, "phase_newton"),
])
def test_terminal_validator_authenticates_exact_numerical_failure_package(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, classification: str,
        cycle: int, substep: int, newton_layer: str) -> None:
    """Numerical failures remain distinct and require a closed immutable dossier."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(
        protocol, inputs, classification, cycle=cycle, substep=substep,
        newton_layer=newton_layer,
    )
    output = inputs["run_root"] / "output"
    expect_trace = cycle > 5 or (cycle == 5 and substep >= 4)
    assert (output / "qualification" / "C5_STAGGER_TRACE.csv").is_file() is expect_trace
    expect_pass_receipt = cycle > 5 or (cycle == 5 and substep == 5)
    assert (output / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json").is_file() \
        is expect_pass_receipt
    assert (output / "substeps" / "cycle_0005.mat").is_file() is (cycle > 5)
    module = load_module("validate_t3_rev_terminal")
    result = module._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
        run_root=inputs["run_root"], launch=launch,
    )
    assert result["classification"] == classification
    assert result["status"] == classification
    assert result["phase_evidence"]["failure_package_sha256"]
    expected_authenticated_substep = substep if cycle == 5 and substep in {4, 5} else None
    assert result["phase_evidence"]["substep_authenticated"] is (
        expected_authenticated_substep is not None)
    assert result["phase_evidence"]["authenticated_substep"] == expected_authenticated_substep
    assert result["phase_evidence"]["self_reported_substep"] == substep


def test_numerical_failure_requires_archived_full_matlab_version_receipt(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The production receipt uses MATLAB's full archived `version` string."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    live = inputs["run_root"] / "output" / "RUNTIME_RECEIPT.json"
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / \
        "output" / "RUNTIME_RECEIPT.json"
    for path in (live, copied):
        receipt = strict_json(path)
        assert receipt["matlab_version"] == "25.2.0.3177638 (R2025b) Update 5"
        receipt["matlab_version"] = "25.2.0.3177638"
        _write_canonical_json(path, receipt)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="runtime receipt"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_post_c5_newton_substep_remains_self_reported_after_reclosure(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A package-local substep rewrite cannot manufacture independent exact evidence."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(
        protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE", cycle=6, substep=1,
    )
    package_failure = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / \
        "FAILURE_CLASSIFICATION.json"
    failure = strict_json(package_failure)
    failure["failure_substep"] = 3
    _write_canonical_json(package_failure, failure)
    terminal_path = inputs["run_root"] / "receipts" / "T3_REV_TERMINAL_FAILURE.json"
    terminal = strict_json(terminal_path)
    terminal["substep"] = 3
    _write_canonical_json(terminal_path, terminal)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    result = module._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
        run_root=inputs["run_root"], launch=launch,
    )
    assert result["classification"] == "FAIL_NEWTON_NONCONVERGENCE"
    assert result["phase_evidence"]["self_reported_substep"] == 3
    assert result["phase_evidence"]["substep_authenticated"] is False
    assert result["phase_evidence"]["authenticated_substep"] is None


@pytest.mark.parametrize("tamper", ["copied_artifact", "undeclared_shard"])
def test_terminal_validator_rejects_tampered_numerical_failure_closure(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tamper: str) -> None:
    """A closed-looking receipt cannot admit altered bytes or arbitrary extra shards."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    package = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE"
    if tamper == "copied_artifact":
        with (package / "artifacts" / "T3_REV.stderr.log").open("ab") as stream:
            stream.write(b"tampered\n")
    else:
        extra = package / "artifacts" / "output" / "substeps" / "cycle_0006.mat"
        shutil.copy2(inputs["run_root"] / "output" / "substeps" / "cycle_0005.mat", extra)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="failure package"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_terminal_validator_rejects_mesh_connectivity_metadata_mismatch(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The mesh's connectivity digest must equal both computed bytes and the case identity."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    live_mesh = inputs["run_root"] / "output" / "mesh_geometry.mat"
    copied_mesh = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / \
        "output" / "mesh_geometry.mat"
    for path in (live_mesh, copied_mesh):
        with h5py.File(path, "r+") as handle:
            handle["mesh_geometry/connectivity_sha256"][...] = np.asarray(
                [ord(character) for character in "0" * 64], dtype=np.uint16,
            ).reshape(-1, 1)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="mesh arrays/identity"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_numerical_failure_rejects_state0_rows_detached_from_authenticated_mesh(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A package-local tiny state cannot authenticate against the production mesh."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    live = inputs["run_root"] / "output" / "state0_analysis.mat"
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / \
        "output" / "state0_analysis.mat"
    for path in (live, copied):
        path.unlink()
        _write_state0(path)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="mesh/state dimensions"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


@pytest.mark.parametrize(("field", "logical_shape"), [
    ("d_node", (4, 5)),
    ("alpha_bar_gp", (1, 4, 5)),
])
def test_numerical_failure_rejects_shard_rows_detached_from_authenticated_mesh(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str,
        logical_shape: tuple[int, ...]) -> None:
    """Every sequential shard keeps the authenticated node and element row counts."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    relative = Path("output/substeps/cycle_0003.mat")
    live = inputs["run_root"] / relative
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative
    for path in (live, copied):
        with h5py.File(path, "r+") as handle:
            group = handle["shard"]
            del group[field]
            _matlab_filled_dataset(group, field, logical_shape, 0.1)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="shape|physical state"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


@pytest.mark.parametrize(("field", "stored_index", "value", "expected_error"), [
    ("d_node", (0, 0), -0.1, "state0 damage"),
    ("d_node", (0, 0), 1.1, "state0 damage"),
    ("d_node", (0, 0), float("nan"), "finite"),
    ("alpha_bar_gp", (0, 0), -0.1, "state0 alpha"),
])
def test_numerical_failure_rejects_state0_outside_authoritative_state_bounds(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str,
        stored_index: tuple[int, int], value: float, expected_error: str) -> None:
    """Reclosing cannot admit invalid initial damage or fatigue history."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    relative = Path("output/state0_analysis.mat")
    live = inputs["run_root"] / relative
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative
    for path in (live, copied):
        with h5py.File(path, "r+") as handle:
            handle[f"state0/{field}"][stored_index] = value
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match=expected_error):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


@pytest.mark.parametrize(("field", "regressed_value"), [
    ("d_node", 0.0915),
    ("alpha_bar_gp", 0.0015),
])
def test_numerical_failure_rejects_sequential_shard_state_regression(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str,
        regressed_value: float) -> None:
    """The qualified protocol preserves damage/history irreversibility across shards."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    relative = Path("output/substeps/cycle_0003.mat")
    live = inputs["run_root"] / relative
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative
    for path in (live, copied):
        with h5py.File(path, "r+") as handle:
            handle[f"shard/{field}"][0, 0] = regressed_value
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="chronology"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def _set_cumulative_shard_field(path: Path, field: str, value: float) -> None:
    """Mutate one irreversible field while preserving its qualified constitutive identity."""
    with h5py.File(path, "r+") as handle:
        if field == "d_node":
            stored_damage = np.asarray(handle["shard/d_node"])
            stored_damage[:, 0] = value
            handle["shard/d_node"][...] = stored_damage
            damage = stored_damage.T
            gauss = 1 / np.sqrt(3)
            points = np.asarray([
                [-gauss, -gauss], [gauss, -gauss],
                [gauss, gauss], [-gauss, gauss],
            ])
            operator = np.asarray([
                0.25 * np.asarray([
                    (1 - xi) * (1 - eta), (1 + xi) * (1 - eta),
                    (1 + xi) * (1 + eta), (1 - xi) * (1 + eta),
                ])
                for xi, eta in points
            ])
            with h5py.File(path.parent.parent / "mesh_geometry.mat", "r") as mesh_handle:
                connectivity = np.asarray(
                    mesh_handle["mesh_geometry/connectivity"]
                ).T.astype(np.int64) - 1
            element_damage = damage[connectivity]
            gp_damage = np.einsum("gj,ejs->egs", operator, element_damage)
            stored_gp_damage = np.transpose(gp_damage, (2, 1, 0))
            handle["shard/d_gp"][...] = stored_gp_damage
            g_value = (1.0 - stored_gp_damage) ** 2
            handle["shard/g_gp"][...] = g_value
            handle["shard/psi_active_gp"][...] = (
                g_value * np.asarray(handle["shard/psi_raw_gp"])
            )
        elif field == "alpha_bar_gp":
            handle["shard/alpha_bar_gp"][...] = value
            f_alpha = min(1.0, (1.0 - ((value - 0.5) / (value + 0.5))) ** 2)
            handle["shard/f_alpha_gp"][...] = f_alpha
        elif field == "d_gp":
            # The captured GP field is derived from d_node.  Keep that identity exact
            # so this fixture reaches the independent GP running-maximum check.
            handle["shard/d_node"][...] = value
            handle["shard/d_gp"][...] = value
            g_value = (1.0 - value) ** 2
            handle["shard/g_gp"][...] = g_value
            handle["shard/psi_active_gp"][...] = (
                g_value * np.asarray(handle["shard/psi_raw_gp"])
            )


def _stored_final_shard_sample(path: Path, field: str) -> float:
    with h5py.File(path, "r") as handle:
        stored = np.asarray(handle[f"shard/{field}"])
    return float(stored[-1].reshape(-1)[0])


def _set_gp_damage_with_constitutive_fields(path: Path, value: float) -> None:
    with h5py.File(path, "r+") as handle:
        handle["shard/d_gp"][...] = value
        g_value = (1.0 - value) ** 2
        handle["shard/g_gp"][...] = g_value
        handle["shard/psi_active_gp"][...] = (
            g_value * np.asarray(handle["shard/psi_raw_gp"])
        )


def _set_uniform_damage_with_constitutive_fields(path: Path, value: float) -> None:
    """Keep the captured Q4 nodal-to-GP identity exact while mutating damage."""
    with h5py.File(path, "r+") as handle:
        handle["shard/d_node"][...] = value
        handle["shard/d_gp"][...] = value
        g_value = (1.0 - value) ** 2
        handle["shard/g_gp"][...] = g_value
        handle["shard/psi_active_gp"][...] = (
            g_value * np.asarray(handle["shard/psi_raw_gp"])
        )


@pytest.mark.parametrize(("field", "peak"), [
    ("d_node", 0.09104),
    ("d_gp", 0.09104),
    ("alpha_bar_gp", 0.00104),
])
@pytest.mark.parametrize("right_censored", [False, True])
def test_completed_package_rejects_accumulated_sub_tolerance_state_regression(
        tmp_path: Path, field: str, peak: float, right_censored: bool) -> None:
    """Pairwise-small regressions cannot accumulate below a completed trajectory maximum."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / f"completed-drift-{right_censored}",
        terminal_cycle=150 if right_censored else 5, right_censored=right_censored,
    )
    for cycle, multiplier in ((2, 0.75), (3, 1.5)):
        _set_cumulative_shard_field(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            field, peak - multiplier * protocol.THRESHOLD,
        )
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="running maximum|trajectory envelope"):
        module.authenticate_completed_package(protocol, root)


@pytest.mark.parametrize("right_censored", [False, True])
def test_completed_package_accepts_running_envelope_tolerance_boundary(
        tmp_path: Path, right_censored: bool) -> None:
    """A completed trajectory exactly one threshold below its maximum remains admissible."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / f"completed-boundary-{right_censored}",
        terminal_cycle=150 if right_censored else 5, right_censored=right_censored,
    )
    peak_damage = _stored_final_shard_sample(
        root / "substeps" / "cycle_0001.mat", "d_gp")
    for cycle, multiplier in ((2, 0.5), (3, 1.0)):
        _set_uniform_damage_with_constitutive_fields(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            peak_damage - multiplier * protocol.THRESHOLD,
        )
    peak_alpha = _stored_final_shard_sample(
        root / "substeps" / "cycle_0001.mat", "alpha_bar_gp")
    for cycle, multiplier in ((2, 0.5), (3, 1.0)):
        _set_cumulative_shard_field(
            root / "substeps" / f"cycle_{cycle:04d}.mat",
            "alpha_bar_gp", peak_alpha - multiplier * protocol.THRESHOLD,
        )
    _reclose_completed_package(root)
    receipt = load_module("validate_t3_rev_terminal").authenticate_completed_package(
        protocol, root)
    assert receipt["status"] == "PASS"


@pytest.mark.parametrize("gp_damage", [-2e-12, 1.0 + 2e-12])
def test_completed_package_rejects_gp_damage_outside_task6_absolute_bounds(
        tmp_path: Path, gp_damage: float) -> None:
    """Task 6 applies the exact protocol threshold to every damage sample."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / "completed-gp-bounds", terminal_cycle=5, right_censored=False,
    )
    _set_gp_damage_with_constitutive_fields(
        root / "substeps" / "cycle_0002.mat", gp_damage)
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="trajectory envelope"):
        module.authenticate_completed_package(protocol, root)


@pytest.mark.parametrize("right_censored", [False, True])
def test_completed_package_rejects_gp_damage_not_interpolated_from_authenticated_nodes(
        tmp_path: Path, right_censored: bool) -> None:
    """The sealed capture source makes Q4 nodal-to-GP interpolation independently checkable."""
    _, protocol = _generated_terminal_protocol(tmp_path)
    root = _build_authenticated_terminal_package(
        protocol, tmp_path / f"completed-gp-interpolation-{right_censored}",
        terminal_cycle=150 if right_censored else 5, right_censored=right_censored,
    )
    baseline = _stored_final_shard_sample(
        root / "substeps" / "cycle_0002.mat", "d_gp")
    _set_gp_damage_with_constitutive_fields(
        root / "substeps" / "cycle_0002.mat", baseline + 5e-12)
    _reclose_completed_package(root)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="Q4 nodal-to-GP interpolation"):
        module.authenticate_completed_package(protocol, root)


@pytest.mark.parametrize(("field", "peak"), [
    ("d_node", 0.092),
    ("d_gp", 0.092),
    ("alpha_bar_gp", 0.002),
])
def test_numerical_failure_rejects_accumulated_sub_tolerance_state_regression(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, peak: float) -> None:
    """Failure-package chronology is measured against the running componentwise maximum."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    for cycle, multiplier in ((3, 0.75), (4, 1.5)):
        relative = Path(f"output/substeps/cycle_{cycle:04d}.mat")
        for path in (
                inputs["run_root"] / relative,
                inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative):
            _set_cumulative_shard_field(
                path, field, peak - multiplier * protocol.THRESHOLD)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="running maximum|trajectory envelope"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_numerical_failure_accepts_running_envelope_tolerance_boundary(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Failure evidence exactly at the accumulated tolerance boundary remains admissible."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    peak_damage = _stored_final_shard_sample(
        inputs["run_root"] / "output" / "substeps" / "cycle_0002.mat", "d_gp")
    for cycle, multiplier in ((3, 0.5), (4, 1.0)):
        relative = Path(f"output/substeps/cycle_{cycle:04d}.mat")
        for path in (
                inputs["run_root"] / relative,
                inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative):
            _set_uniform_damage_with_constitutive_fields(
                path, peak_damage - multiplier * protocol.THRESHOLD)
    peak_alpha = _stored_final_shard_sample(
        inputs["run_root"] / "output" / "substeps" / "cycle_0002.mat",
        "alpha_bar_gp",
    )
    for cycle, multiplier in ((3, 0.5), (4, 1.0)):
        relative = Path(f"output/substeps/cycle_{cycle:04d}.mat")
        for path in (
                inputs["run_root"] / relative,
                inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative):
            _set_cumulative_shard_field(
                path, "alpha_bar_gp", peak_alpha - multiplier * protocol.THRESHOLD)
    _reclose_failure_package(inputs)
    result = load_module("validate_t3_rev_terminal")._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
        run_root=inputs["run_root"], launch=launch,
    )
    assert result["classification"] == "FAIL_NEWTON_NONCONVERGENCE"


def test_numerical_failure_rejects_gp_damage_not_interpolated_from_authenticated_nodes(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Failure shards retain the same sealed Q4 capture identity as completed shards."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    relative = Path("output/substeps/cycle_0003.mat")
    baseline = _stored_final_shard_sample(inputs["run_root"] / relative, "d_gp")
    for path in (
            inputs["run_root"] / relative,
            inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / relative):
        _set_gp_damage_with_constitutive_fields(path, baseline + 5e-12)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="Q4 nodal-to-GP interpolation"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_numerical_failure_rejects_out_of_range_mesh_connectivity_before_hash_claim(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Integer Q4 connectivity must index an authenticated node row."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(protocol, inputs, "FAIL_NEWTON_NONCONVERGENCE")
    live = inputs["run_root"] / "output" / "mesh_geometry.mat"
    copied = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / \
        "output" / "mesh_geometry.mat"
    for path in (live, copied):
        with h5py.File(path, "r+") as handle:
            node_count = handle["mesh_geometry/node_coords"].shape[1]
            handle["mesh_geometry/connectivity"][0, 0] = float(node_count + 1)
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="connectivity indices"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_terminal_validator_rejects_reclosed_c5_failure_trace_that_passed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An iteration-cap receipt cannot claim failure after its final c5 delta converged."""
    launch, protocol, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_numerical_failure(
        protocol, inputs, "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE",
        cycle=5, substep=4,
    )
    live_trace = inputs["run_root"] / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
    copied_trace = inputs["run_root"] / "T3_REV_FAILURE_PACKAGE" / "artifacts" / \
        "output" / "qualification" / "C5_STAGGER_TRACE.csv"
    for path in (live_trace, copied_trace):
        lines = path.read_text(encoding="ascii").splitlines()
        final = lines[-1].split(",")
        final[protocol.TRACE_COLUMNS.index("consecutive_stagger_delta")] = "0.0005"
        lines[-1] = ",".join(final)
        path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    _reclose_failure_package(inputs)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="nonconvergence"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def _prepare_phase_failure(inputs: dict[str, Path], phase: str) -> None:
    run_root = inputs["run_root"]
    receipts = run_root / "receipts"
    output = run_root / "output"
    for path in list(output.iterdir()):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    lock = strict_json(receipts / "T3_REV_EXECUTION_INPUT_LOCK.json")
    writable_roots = [Path(value) for value in lock["writable_roots"].values()]
    if phase == "runtime_qualification_before_producer":
        for path in writable_roots:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
    else:
        for path in writable_roots:
            path.mkdir(parents=True, exist_ok=True)
    measurement_path = receipts / "T3_REV_RUNTIME_MEASUREMENT.json"
    classification = "FAIL_RUNTIME"
    terminal_reason = "runtime_failure"
    identifiers = {
        "runtime_qualification_before_producer": "toyRoadP0:RuntimeQualificationFailed",
        "producer_after_pass_runtime_measurement": "toyRoadP0:MissingInputAsset",
    }
    if phase == "runtime_qualification_before_producer":
        message = "Measured absolute MATLAB path precedence differs from the lock. First mismatch index: 1."
        lock_path = receipts / "T3_REV_EXECUTION_INPUT_LOCK.json"
        lock = strict_json(lock_path)
        expected = lock["runtime_expectations"]["matlab"]["absolute_path_order"]
        actual = [r"C:\unexpected\runtime-overlay", *expected[1:]]
        _write_canonical_json(measurement_path, {
            "schema_version": "toy_road_runtime_measurement_v1",
            "protocol_version": lock["protocol_version"],
            "authorization_scope": lock["authorization_scope"],
            "status": "FAIL", "producer_entrypoint_authorized": False,
            "execution_input_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            "first_failed_predicate": "matlab_path_precedence",
            "first_mismatch_index": 1,
            "expected_absolute_path": expected, "actual_absolute_path": actual,
            "expected_normalized_path": expected, "actual_normalized_path": actual,
            "matlab_identifier": "toyRoadP0:RuntimeQualificationFailed",
            "message": "Measured absolute MATLAB path precedence differs from the lock.",
        })
    else:
        message = "The locked SENS mesh source is absent: " + str(
            inputs["input_assets_root"] / "sens_mesh.m")
    with (run_root / "T3_REV.stderr.log").open("ab") as stream:
        stream.write((message + "\n").encode("utf-8"))
    launch_path = receipts / "T3_REV_LAUNCH_RECEIPT.json"
    _write_canonical_json(receipts / "T3_REV_TERMINAL_FAILURE.json", {
        "schema_version": "toy_road_t3_rev_terminal_failure_v1", "status": classification,
        "case_id": "T3_rev_loading_order", "terminal_reason": terminal_reason,
        "failure_phase": phase, "cycle": None, "substep": None,
        "error_identifier": identifiers[phase], "error_message": message,
        "seal_sha256": hashlib.sha256(inputs["seal_path"].read_bytes()).hexdigest(),
        "run_root": str(run_root),
        "launch_receipt_sha256": hashlib.sha256(launch_path.read_bytes()).hexdigest(),
        "runtime_measurement_sha256": hashlib.sha256(measurement_path.read_bytes()).hexdigest()
        if measurement_path.is_file() else None,
        "failure_package_manifest_sha256": None,
    })


def _credential_failure_terminal_fixture(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, timeout_only: bool = False):
    """Run the real launcher through its started-but-no-PASS credential failure path."""
    launch = load_module("launch_t3_rev")
    inputs = _launcher_inputs(launch, tmp_path)
    launch.SUITESPARSE_ROOT = Path(r"C:\SuiteSparse\SuiteSparse-dev")
    inputs["griphfith_root"] = Path(r"C:\q4diag\griphfith-pf-rebuild-355d4c83")
    monkeypatch.setattr(launch, "matlab_processes", lambda: [])
    overlay_validator = launch.require_materialized_runtime_overlay
    _allow_test_matlab_identity(launch, monkeypatch)

    class Process:
        pid = 8642

    monkeypatch.setattr(launch, "Popen", lambda *args, **kwargs: Process())
    real_link = launch.os.link

    def fail_publication(source, target, *args, **kwargs):
        if Path(target).name == "T3_REV_LAUNCH_RECEIPT.json":
            raise OSError("injected credential publication failure")
        return real_link(source, target, *args, **kwargs)

    monkeypatch.setattr(launch.os, "link", fail_publication)
    with pytest.raises(launch.LaunchCredentialError, match="credential"):
        launch.launch_t3_rev(**inputs)
    monkeypatch.setattr(launch, "require_materialized_runtime_overlay", overlay_validator)
    receipts = inputs["run_root"] / "receipts"
    if timeout_only:
        (receipts / "LAUNCH_CREDENTIAL_FAILED.json").unlink()
        with (inputs["run_root"] / "T3_REV.stderr.log").open("ab") as stream:
            stream.write(b"Exact launch credential was not published\n")
    return launch, inputs


@pytest.mark.parametrize(("timeout_only", "expected_phase"), [
    (False, "launch_credential_publication_failure"),
    (True, "bootstrap_credential_timeout"),
])
def test_terminal_validator_authenticates_genuine_no_pass_bootstrap_layout(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timeout_only: bool,
        expected_phase: str) -> None:
    """Started bootstrap evidence authenticates without a contradictory PASS credential."""
    launch, inputs = _credential_failure_terminal_fixture(
        monkeypatch, tmp_path, timeout_only=timeout_only)
    module = load_module("validate_t3_rev_terminal")
    result = module._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
        run_root=inputs["run_root"], launch=launch,
    )
    assert result["classification"] == "FAIL_STARTUP"
    assert result["launch_receipt_sha256"] is None
    assert result["phase_evidence"]["failure_phase"] == expected_phase


def test_no_pass_bootstrap_layout_rejects_stale_live_pass_receipt(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Credential-failure evidence cannot coexist with any live PASS-path bytes."""
    launch, inputs = _credential_failure_terminal_fixture(monkeypatch, tmp_path)
    (inputs["run_root"] / "receipts" / "T3_REV_LAUNCH_RECEIPT.json").write_bytes(
        b'{"status":"PASS"}\n')
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="PASS|credential failure"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_no_pass_bootstrap_layout_rejects_even_empty_stale_output_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Credential failure occurs before any producer output reservation exists."""
    launch, inputs = _credential_failure_terminal_fixture(monkeypatch, tmp_path)
    (inputs["run_root"] / "output").mkdir()
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="writable root|producer evidence"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_no_pass_bootstrap_layout_rejects_unrecognized_publication_error_class(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A reclosed receipt cannot invent an arbitrary credential-publication class."""
    launch, inputs = _credential_failure_terminal_fixture(monkeypatch, tmp_path)
    failure_path = inputs["run_root"] / "receipts" / "LAUNCH_CREDENTIAL_FAILED.json"
    failure = strict_json(failure_path)
    failure["error_type"] = "ArbitraryError"
    failure_path.write_bytes(launch.json_payload(failure))
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="LAUNCH_CREDENTIAL_FAILED"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_terminal_validator_distinguishes_final_busy_without_popen(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A final process-race receipt is not recast as bootstrap credential failure."""
    launch = load_module("launch_t3_rev")
    inputs = _launcher_inputs(launch, tmp_path)
    launch.SUITESPARSE_ROOT = Path(r"C:\SuiteSparse\SuiteSparse-dev")
    inputs["griphfith_root"] = Path(r"C:\q4diag\griphfith-pf-rebuild-355d4c83")
    observations = iter([[], [{"pid": 77, "name": "MATLAB", "command_line": "matlab -batch"}]])
    monkeypatch.setattr(launch, "matlab_processes", lambda: next(observations))
    monkeypatch.setattr(launch, "Popen", lambda *args, **kwargs: pytest.fail("Popen called"))
    overlay_validator = launch.require_materialized_runtime_overlay
    _allow_test_matlab_identity(launch, monkeypatch)
    with pytest.raises(launch.BusyExperimentError, match="BUSY_NO_LAUNCH"):
        launch.launch_t3_rev(**inputs)
    monkeypatch.setattr(launch, "require_materialized_runtime_overlay", overlay_validator)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="BUSY_NO_LAUNCH|no-process"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


@pytest.mark.parametrize(("phase", "classification"), [
    ("runtime_qualification_before_producer", "FAIL_RUNTIME"),
    ("producer_after_pass_runtime_measurement", "FAIL_RUNTIME"),
])
def test_terminal_validator_authenticates_phase_specific_startup_and_runtime_failures(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, phase: str,
        classification: str) -> None:
    """Genuine FAIL qualification and post-PASS producer failures stay distinct."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_phase_failure(inputs, phase)
    lock = strict_json(inputs["run_root"] / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    roots_exist = [Path(value).is_dir() for value in lock["writable_roots"].values()]
    assert all(roots_exist) is (phase == "producer_after_pass_runtime_measurement")
    module = load_module("validate_t3_rev_terminal")
    result = module._validate_terminal(
        inputs["run_root"] / "output",
        sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
        "toy_road_p0_repeatability_20260803",
        extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
        run_root=inputs["run_root"], launch=launch,
    )
    assert result["classification"] == classification
    assert result["phase_evidence"]["failure_phase"] == phase


@pytest.mark.parametrize("phase", [
    "runtime_qualification_before_producer",
])
def test_preproducer_failure_rejects_even_empty_stale_writable_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, phase: str) -> None:
    """Before producer entry, an empty output reservation is still stale producer state."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_phase_failure(inputs, phase)
    (inputs["run_root"] / "output").mkdir()
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="writable root|producer roots"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_post_authorization_runtime_failure_rejects_synthetic_fail_measurement(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A producer failure after authorization remains bound to a genuine PASS measurement."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_phase_failure(inputs, "producer_after_pass_runtime_measurement")
    measurement_path = inputs["run_root"] / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    measurement = strict_json(measurement_path)
    measurement["status"] = "FAIL"
    measurement["producer_entrypoint_authorized"] = False
    _write_canonical_json(measurement_path, measurement)
    terminal_path = inputs["run_root"] / "receipts" / "T3_REV_TERMINAL_FAILURE.json"
    terminal = strict_json(terminal_path)
    terminal["runtime_measurement_sha256"] = hashlib.sha256(measurement_path.read_bytes()).hexdigest()
    _write_canonical_json(terminal_path, terminal)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="PASS|measurement|runtime failure"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


@pytest.mark.parametrize("phase", [
    "runtime_qualification_before_producer",
    "producer_after_pass_runtime_measurement",
])
def test_phase_failure_rejects_producer_artifacts_outside_its_exact_closure(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, phase: str) -> None:
    """No phase may inherit or smuggle a shard outside its declared lifecycle."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_phase_failure(inputs, phase)
    shard = inputs["run_root"] / "output" / "substeps" / "cycle_0001.mat"
    shard.parent.mkdir(parents=True)
    shard.write_bytes(b"not authorized in this phase")
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="artifacts|closure|writable root"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_runtime_qualification_failure_rejects_false_mismatch_claim(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A genuine FAIL measurement must identify its actual first path mismatch."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    _prepare_phase_failure(inputs, "runtime_qualification_before_producer")
    measurement_path = inputs["run_root"] / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    measurement = strict_json(measurement_path)
    measurement["first_mismatch_index"] = 2
    _write_canonical_json(measurement_path, measurement)
    terminal_path = inputs["run_root"] / "receipts" / "T3_REV_TERMINAL_FAILURE.json"
    terminal = strict_json(terminal_path)
    terminal["runtime_measurement_sha256"] = hashlib.sha256(
        measurement_path.read_bytes()).hexdigest()
    _write_canonical_json(terminal_path, terminal)
    module = load_module("validate_t3_rev_terminal")
    with pytest.raises(module.TerminalValidationError, match="measurement semantics"):
        module._validate_terminal(
            inputs["run_root"] / "output",
            sealed_base_root=inputs["repo_root"] / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=inputs["extension_root"], seal_path=inputs["seal_path"],
            run_root=inputs["run_root"], launch=launch,
        )


def test_public_analyzer_rejects_caller_selected_protocols(tmp_path: Path) -> None:
    """Protocol authority is derived from published/sealed identities, never a caller path."""
    module = load_module("analyze_t3_rev")
    with pytest.raises(TypeError, match="unexpected keyword"):
        module.analyze_t3_rev(
            tmp_path / "t3", tmp_path / "rev", tmp_path / "analysis",
            seal_path=tmp_path / "seal.json", t3_protocol_path=tmp_path / "attacker.py",
        )


def test_analyzer_requires_published_t3_adjudication_hash_chain(tmp_path: Path) -> None:
    """A merely authenticated lookalike receipt cannot replace the published T3 chain."""
    module = load_module("analyze_t3_rev")
    authentication = strict_json(
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
        "T3_AUTHENTICATED_TERMINAL.json"
    )
    authentication["package_snapshot_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="published adjudication hashes"):
        module._require_published_t3_chain(ROOT, tmp_path, authentication)


def test_authenticated_analysis_snapshot_rejects_post_auth_byte_substitution(tmp_path: Path) -> None:
    """Every byte selected for reduction must still match its authentication receipt."""
    module = load_module("analyze_t3_rev")
    package = tmp_path / "package"
    package.mkdir()
    terminal = package / "TERMINAL_RESULT.json"
    terminal.write_bytes(b"original")
    authentication = {
        "files": [{"path": "TERMINAL_RESULT.json",
                   "sha256": hashlib.sha256(b"original").hexdigest()}]
    }

    class Protocol:
        @staticmethod
        def recheck_authenticated_package(receipt: object) -> None:
            assert receipt is authentication

    terminal.write_bytes(b"substituted")
    with pytest.raises(ValueError, match="changed"):
        module._snapshot_authenticated_inputs(
            Protocol(), authentication, package, tmp_path / "snapshot",
            ("TERMINAL_RESULT.json",),
        )


def _run_authenticated_analyzer_fixture(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, t3_terminal: int = 71,
        rev_terminal: int = 80, rev_right_censored: bool = False,
) -> tuple[object, dict[str, object], Path]:
    """Run the real hash-qualified analyzer over compact authenticated packages."""
    launch, _, inputs = _launched_terminal_fixture(monkeypatch, tmp_path)
    rev_root = inputs["run_root"] / "output"
    shutil.rmtree(rev_root)
    rev_lock = strict_json(
        inputs["run_root"] / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json")
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    rev_digest = next(
        item["sha256"] for item in manifest["shadow_files"]
        if item["path"] == "toy_road_protocol.py"
    )
    rev_protocol = launch.load_protocol(
        inputs["extension_root"] / "toy_road_protocol.py",
        "test_analyzer_rev_protocol", rev_digest,
    )
    _build_authenticated_terminal_package(
        rev_protocol, rev_root, terminal_cycle=rev_terminal,
        right_censored=rev_right_censored,
        offsets={} if rev_right_censored else {20: 2e-12},
        execution_lock=rev_lock, include_mesh=True,
        **_rev_completed_identity_kwargs(inputs),
    )
    base_protocol_path = BASE / "toy_road_protocol.py"
    base_digest = hashlib.sha256(base_protocol_path.read_bytes()).hexdigest()
    base_protocol = launch.load_protocol(
        base_protocol_path, "test_analyzer_base_protocol", base_digest,
    )
    t3_root = tmp_path / "t3"
    _build_authenticated_terminal_package(
        base_protocol, t3_root, terminal_cycle=t3_terminal, right_censored=False,
        case_id="T3_loading_history", include_mesh=True,
        component_identities=_rev_completed_identity_kwargs(inputs)["component_identities"],
    )
    module = load_module("analyze_t3_rev")
    destination = tmp_path / "analysis"
    summary = module._analyze_t3_rev(
        t3_root, rev_root, destination, seal_path=inputs["seal_path"],
        required_t3_manifest_sha256=hashlib.sha256(
            (t3_root / "TERMINAL_MANIFEST.json").read_bytes()).hexdigest(),
        launch_authority=launch, repository_root=inputs["repo_root"],
    )
    return module, summary, destination


def test_analyzer_end_to_end_emits_complete_authenticated_mechanism_observables(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Transitions, process geometry, overlap and energy use authenticated shard values."""
    _, summary, destination = _run_authenticated_analyzer_fixture(
        monkeypatch, tmp_path)
    assert summary["order_effect_classification"] == \
        "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    assert summary["status"] == "PASS_OFFLINE_ANALYSIS"
    assert summary["required_observables_complete"] is True
    assert summary["required_observable_coverage"] == {
        "block_transitions": "AVAILABLE",
        "energy_components": "AVAILABLE",
        "own_event_boundaries": "AVAILABLE",
        "process_zone_crack_overlap": "AVAILABLE",
        "same_cycle_fields": "AVAILABLE",
    }
    assert summary["auxiliary_observable_coverage"] == {
        "tot_en": "UNAVAILABLE_NOT_CAPTURED_IN_AUTHENTICATED_SHARDS"
    }
    expected_outputs = {
        "block_transition_differences.csv",
        "process_zone_crack_overlap.csv",
        "energy_component_differences.csv",
        "auxiliary_tot_en.csv",
    }
    assert expected_outputs.issubset(path.name for path in destination.iterdir())
    own_rows = list(csv.DictReader(
        (destination / "own_event_differences.csv").open(
            encoding="utf-8", newline="")))
    assert {row["comparison"] for row in own_rows} == {
        "own_event_first_hit", "own_event_confirmed",
    }
    assert all(row["left_cycle"] and row["right_cycle"] for row in own_rows)
    assert all(
        "left_area_weighted_integral" in row and "right_area_weighted_integral" in row
        for row in own_rows
    )
    transition_rows = list(csv.DictReader(
        (destination / "block_transition_differences.csv").open(
            encoding="utf-8", newline="")))
    t3_history = next(row for row in transition_rows
                      if row["comparison"] == "within_case_transition"
                      and row["case_id"] == "T3_loading_history"
                      and row["field"] == "history"
                      and row["start_cycle"] == "30")
    assert float(t3_history["right_minus_left_area_weighted_mean"]) == pytest.approx(1e-3)
    cross_history = next(row for row in transition_rows
                         if row["comparison"] == "cross_case_difference_of_transitions"
                         and row["field"] == "history"
                         and row["start_cycle"] == "30")
    assert float(cross_history["max_abs"]) == pytest.approx(0.0)
    process_rows = list(csv.DictReader(
        (destination / "process_zone_crack_overlap.csv").open(
            encoding="utf-8", newline="")))
    c30 = next(row for row in process_rows
               if row["comparison"] == "same_cycle" and row["cycle"] == "30")
    assert float(c30["left_support_area"]) == pytest.approx(1.0)
    assert float(c30["right_support_area"]) == pytest.approx(1.0)
    assert float(c30["left_centroid_x"]) == pytest.approx(0.5)
    assert float(c30["right_rms_width_x"]) == pytest.approx(0.0)
    assert math.isnan(float(c30["left_crack_tip_x"]))
    assert c30["history_signal_definition"] == \
        "(right-left)_comparison-(right-left)_c30"
    assert c30["history_baseline_cycle"] == "30"
    assert float(c30["spatial_overlap_area"]) == pytest.approx(0.0)
    own_first = next(row for row in process_rows
                     if row["comparison"] == "own_event_first_hit")
    assert float(own_first["spatial_overlap_area"]) == pytest.approx(1.0)
    energy_rows = list(csv.DictReader(
        (destination / "energy_component_differences.csv").open(
            encoding="utf-8", newline="")))
    raw_c30 = next(row for row in energy_rows
                   if row["comparison"] == "same_cycle"
                   and row["cycle"] == "30" and row["field"] == "raw_driver")
    assert float(raw_c30["left_area_weighted_integral"]) == pytest.approx(4.0)
    assert float(raw_c30["right_area_weighted_integral"]) == pytest.approx(4.0)
    assert {row["field"] for row in energy_rows} == {
        "raw_driver", "raw_cyclemax_driver", "active_driver",
    }
    raw_transition = next(row for row in energy_rows
                          if row["comparison"] == "within_case_transition"
                          and row["case_id"] == "T3_loading_history"
                          and row["field"] == "raw_driver"
                          and row["start_cycle"] == "30")
    assert float(raw_transition["right_minus_left_area_weighted_integral"]) == \
        pytest.approx(0.0)
    tot_en_rows = list(csv.DictReader(
        (destination / "auxiliary_tot_en.csv").open(encoding="utf-8", newline="")))
    assert {row["field"] for row in tot_en_rows} == {"tot_en"}
    assert {row["availability"] for row in tot_en_rows} == {
        "UNAVAILABLE_NOT_CAPTURED_IN_AUTHENTICATED_SHARDS"
    }
    assert {row["role"] for row in tot_en_rows} == {
        "AUXILIARY_ONLY_EXCLUDED_FROM_CLASSIFICATION"
    }


def test_analyzer_end_to_end_refuses_pass_when_required_transition_is_unavailable(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An authenticated trajectory ending at c60 cannot silently satisfy the c60->c61 gate."""
    _, summary, destination = _run_authenticated_analyzer_fixture(
        monkeypatch, tmp_path, t3_terminal=60)
    assert summary["status"] == "INCOMPLETE_OFFLINE_ANALYSIS"
    assert summary["order_effect_classification"] == "UNAVAILABLE"
    assert summary["required_observables_complete"] is False
    assert summary["required_observable_coverage"]["block_transitions"] == "UNAVAILABLE"
    transition_rows = list(csv.DictReader(
        (destination / "block_transition_differences.csv").open(
            encoding="utf-8", newline="")))
    missing = next(row for row in transition_rows
                   if row["comparison"] == "within_case_transition"
                   and row["case_id"] == "T3_loading_history"
                   and row["field"] == "history"
                   and row["start_cycle"] == "60")
    assert missing["availability"] == "UNAVAILABLE"
    process_rows = list(csv.DictReader(
        (destination / "process_zone_crack_overlap.csv").open(
            encoding="utf-8", newline="")))
    assert next(row for row in process_rows
                if row["comparison"] == "same_cycle" and row["cycle"] == "61")[
                    "availability"] == "UNAVAILABLE"


def test_analyzer_end_to_end_marks_own_events_not_applicable_for_right_censoring(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A genuine c150 censor is distinct from missing authenticated own-event evidence."""
    _, summary, destination = _run_authenticated_analyzer_fixture(
        monkeypatch, tmp_path, rev_terminal=150, rev_right_censored=True)
    assert summary["status"] == "PASS_OFFLINE_ANALYSIS"
    assert summary["required_observables_complete"] is True
    assert summary["required_observable_coverage"]["own_event_boundaries"] == \
        "NOT_APPLICABLE_RIGHT_CENSORED"
    assert summary["order_effect_classification"] == \
        "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    event_rows = list(csv.DictReader(
        (destination / "own_event_differences.csv").open(
            encoding="utf-8", newline="")))
    assert {row["availability"] for row in event_rows} == {
        "NOT_APPLICABLE_RIGHT_CENSORED"
    }
    assert all("left_area_weighted_integral" in row for row in event_rows)
    process_rows = list(csv.DictReader(
        (destination / "process_zone_crack_overlap.csv").open(
            encoding="utf-8", newline="")))
    unavailable_event = next(row for row in process_rows
                             if row["comparison"] == "own_event_first_hit")
    assert unavailable_event["availability"] == "NOT_APPLICABLE_RIGHT_CENSORED"
    assert "left_support_area" in unavailable_event
