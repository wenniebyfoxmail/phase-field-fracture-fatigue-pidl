import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aa2024_empirical_sequence_audit.py"
SPEC = importlib.util.spec_from_file_location("aa2024_empirical", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


SCHEMA = (
    "# ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; "
    "epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n"
)


def _header(stage: int, *, cycles: float | None = None,
            cracklength: float | None = None, drop: str | None = None,
            schema: str = SCHEMA, header_stage: int | None = None) -> str:
    values = {
        "current_stage_index": stage if header_stage is None else header_stage,
        "current_stage_relative_date": float(stage),
        "reference_stage_index": 1,
        "force": 100.0 + stage,
        "displacement": -1.0,
        "cycles": float(stage if cycles is None else cycles),
        "time": float(stage),
        "cracklength": float(stage if cracklength is None else cracklength),
    }
    lines = ["# stage data:\n"]
    for key, value in values.items():
        if key == drop:
            continue
        if key in {"force", "displacement", "cycles", "time", "cracklength"}:
            lines.append(f"# {key} : value_element : {value}\n")
        else:
            lines.append(f"# {key} : {value}\n")
    lines.append(schema)
    lines.append("1; 0; 0; 0; 0; 0; 0; 0; 0; 0; 0\n")
    return "".join(lines)


def _fixture(tmp_path: Path, stages=(1, 2, 3), *, missing_connection=None,
             header_kwargs=None):
    archive = tmp_path / "fixture.zip"
    header_kwargs = header_kwargs or {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for stage in stages:
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage, **header_kwargs.get(stage, {})),
            )
            if stage != missing_connection:
                zf.writestr(
                    "global_3d_dic/Connections/"
                    f"global_3d_dic_results_1_{stage}_connections.txt",
                    "Type; Element #; Node 1; Node 2; Node 3\n",
                )
    return archive, archive.stat().st_size, hashlib.md5(archive.read_bytes()).hexdigest()


def _audit(archive: Path, size: int, digest: str):
    return MODULE.audit(archive, expected_size=size, expected_md5=digest)


def test_actual_count_is_observed_not_compared_with_797(tmp_path):
    archive, size, digest = _fixture(tmp_path)
    result = _audit(archive, size, digest)
    assert result["official_manifest_count_used"] is False
    assert result["sequence_checks"]["global_nodemap_count"] == 3
    assert result["decision"] == "QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE"


def test_stage_sets_must_pair_exactly(tmp_path):
    archive, size, digest = _fixture(tmp_path, missing_connection=2)
    result = _audit(archive, size, digest)
    assert result["decision"] == "BLOCKED_EMPIRICAL_SEQUENCE"
    assert result["stop_reason_codes"] == ["GLOBAL_STAGE_PAIRING_INVALID"]


def test_required_header_field_cannot_be_missing(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={2: {"drop": "cycles"}}
    )
    result = _audit(archive, size, digest)
    assert "REQUIRED_HEADER_FIELD_INVALID" in result["stop_reason_codes"]


def test_filename_and_header_stage_must_match(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={2: {"header_stage": 99}}
    )
    result = _audit(archive, size, digest)
    assert "STAGE_IDENTITY_INVALID" in result["stop_reason_codes"]


def test_chronology_must_be_nondecreasing(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={2: {"cycles": 5}, 3: {"cycles": 4}}
    )
    result = _audit(archive, size, digest)
    assert "CHRONOLOGY_INVALID" in result["stop_reason_codes"]


def test_state_must_vary(tmp_path):
    kwargs = {stage: {"cycles": 1, "cracklength": 2} for stage in (1, 2, 3)}
    archive, size, digest = _fixture(tmp_path, header_kwargs=kwargs)
    result = _audit(archive, size, digest)
    assert "STATE_VARIATION_INSUFFICIENT" in result["stop_reason_codes"]


def test_schema_must_be_stable_and_mechanically_complete(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={2: {"schema": "# ID; x_undef [mm]; u [mm]\n"}}
    )
    result = _audit(archive, size, digest)
    assert "NODEMAP_SCHEMA_INVALID" in result["stop_reason_codes"]


def test_identity_failure_stops_before_zip_open(tmp_path, monkeypatch):
    archive, size, digest = _fixture(tmp_path)
    monkeypatch.setattr(MODULE.zipfile, "ZipFile", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("ZIP opened after identity failure")
    ))
    result = MODULE.audit(archive, expected_size=size + 1, expected_md5=digest)
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_output_is_json_and_atomic(tmp_path):
    target = tmp_path / "out" / "result.json"
    payload = {"finite": 1.0}
    MODULE._atomic_write(target, payload)
    assert json.loads(target.read_text()) == payload
    try:
        MODULE._atomic_write(target, payload)
    except MODULE.AuditError:
        pass
    else:
        raise AssertionError("existing output was overwritten")


def test_output_must_be_strictly_inside_run_root(tmp_path):
    archive, _size, _digest = _fixture(tmp_path)
    root = tmp_path / "run"
    root.mkdir()
    target = root / "data_audit.json"
    assert MODULE._validated_output_path(target, archive, root) == target.resolve()
    for invalid in (root, tmp_path / "outside.json", archive):
        try:
            MODULE._validated_output_path(invalid, archive, root)
        except MODULE.AuditError:
            pass
        else:
            raise AssertionError(f"unsafe output accepted: {invalid}")
