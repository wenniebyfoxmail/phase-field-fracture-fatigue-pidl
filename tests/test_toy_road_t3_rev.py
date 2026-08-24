from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
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
        destination: Path | None = None) -> dict[str, object]:
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
        ROOT / "analysis/toy_road_t3_mechanism_20260819/evidence/"
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
