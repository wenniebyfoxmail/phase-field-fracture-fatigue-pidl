from __future__ import annotations

import json
import importlib.util
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import sys
import threading

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
    manifest_path = extension / "EXTENSION_SOURCE_MANIFEST.json"
    manifest = strict_json(manifest_path)
    cases = strict_json(extension / "CASE_PHYSICS_CONTRACTS.json")
    case_table = cases["cases"]
    assert isinstance(case_table, dict)
    case = case_table["T3_rev_loading_order"]
    assert isinstance(case, dict)

    seal_builder = load_module("build_t3_rev_seal")
    seal = {
        "schema_version": "toy_road_t3_rev_seal_v1",
        "status": "PASS",
        "case_id": "T3_rev_loading_order",
        "authorization_capability": "exactly_one_T3_rev_loading_order_execution",
        "resume_allowed": False,
        "follow_on_authorized": False,
        "extension_identity": {
            "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
            "repository_commit": commit,
            "base_source_commit": manifest["base_source_commit"],
            "base_source_manifest_sha256": manifest["base_source_manifest_sha256"],
            "extension_source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "extension_contract_sha256": hashlib.sha256(
                (ANALYSIS / "T3_REV_CONTRACT.json").read_bytes()
            ).hexdigest(),
            "source_diff_inventory_sha256": hashlib.sha256(
                (extension / "SOURCE_DIFF_INVENTORY.json").read_bytes()
            ).hexdigest(),
            "extension_family_contract_sha256": hashlib.sha256(
                (extension / "FAMILY_CONTRACT.json").read_bytes()
            ).hexdigest(),
            "verification": {
                "status": "PASS",
                "numerical_algorithm_changed": False,
                "allowed_shadow_files": list(builder.ALLOWED_SHADOW_FILES),
            },
        },
        "predecessor_evidence": {},
        "physics_closure": {},
        "runtime_identity": seal_builder.EXPECTED_EXECUTION,
    }
    seal_path = tmp_path / "T3_REV_SEAL.json"
    seal_path.write_text(json.dumps(seal, sort_keys=True, separators=(",", ":")), encoding="utf-8")
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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert module.seal_consumption_marker(inputs["seal_path"]).is_file()
    receipt = strict_json(inputs["run_root"] / "receipts" / "PREPARED_NO_LAUNCH.json")
    assert receipt["status"] == "PREPARED_NO_LAUNCH"
    assert receipt["resume_allowed"] is False


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

    def simultaneous_consume(seal_path, run_root):
        claims.wait(timeout=10)
        return real_consume(seal_path, run_root)

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
    marker = strict_json(module.seal_consumption_marker(inputs["seal_path"]))
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
    assert invalidated.exists() is (failure == "popen")
    assert strict_json(inputs["run_root"] / "receipts" / "PREPARED_NO_LAUNCH.json")["status"] == "PREPARED_NO_LAUNCH"


def test_extension_mutation_between_preflight_and_final_check_has_no_pass_receipt(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = load_module("launch_t3_rev")
    inputs = _launcher_inputs(module, tmp_path)
    _allow_test_matlab_identity(module, monkeypatch)
    manifest = strict_json(inputs["extension_root"] / "EXTENSION_SOURCE_MANIFEST.json")
    shadow = inputs["extension_root"] / manifest["shadow_files"][0]["path"]
    checks = 0

    def mutate_on_final_busy_check():
        nonlocal checks
        checks += 1
        if checks == 2:
            shadow.write_bytes(shadow.read_bytes() + b"\n% raced mutation\n")
        return []

    monkeypatch.setattr(module, "matlab_processes", mutate_on_final_busy_check)
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
    seal = tmp_path / "T3_REV_SEAL.json"
    seal.write_text("{}", encoding="utf-8")
    roots = [tmp_path / "first", tmp_path / "second"]

    def claim(root: Path) -> tuple[str, object]:
        try:
            return ("claimed", module.consume_seal(seal, root))
        except module.LaunchError as error:
            return ("blocked", str(error))

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(claim, roots))
    assert [state for state, _ in outcomes].count("claimed") == 1
    assert [state for state, _ in outcomes].count("blocked") == 1
    marker = module.seal_consumption_marker(seal)
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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists(), name


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
    assert not module.seal_consumption_marker(inputs["seal_path"]).exists()


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
