import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aa2024_value_blind_audit.py"
SPEC = importlib.util.spec_from_file_location("aa2024_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _fixture(tmp_path: Path, *, count: int = 3,
             mapping_name: str = "local_2d_microscopic_coordinates_by_nodemaps.csv",
             unsafe_name: str | None = None, collision: bool = False,
             metadata_sentinel: str = ""):
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("root/higher_level_metadata_dictionary.json", "{}")
        zf.writestr("root/timestep_level_metadata_dictionary.json", "{}")
        zf.writestr(f"root/{mapping_name}", "not inspected")
        for index in range(count):
            zf.writestr(f"root/global_3d_dic/Nodemaps/n_{index}.txt", "secret")
            zf.writestr(f"root/global_3d_dic/Connections/c_{index}.txt", "secret")
        if unsafe_name:
            zf.writestr(unsafe_name, "secret")
        if collision:
            zf.writestr("root/dup.txt", "one")
            zf.writestr("root/./dup.txt", "two")

    digest = hashlib.md5(archive.read_bytes()).hexdigest()
    lock = MODULE.IdentityLock(
        record_id=7, concept_id="6", doi="10.test/fixture",
        archive_name=archive.name, archive_size=archive.stat().st_size,
        archive_md5=digest, expected_global_nodemaps=count,
        expected_global_connections=count,
    )
    metadata = {
        "id": 7, "conceptrecid": "6",
        "metadata": {
            "doi": "10.test/fixture",
            "license": {"id": "cc-by-4.0", "title": metadata_sentinel},
            "description": f"797 global files {metadata_sentinel}",
        },
        "files": [{"key": archive.name, "size": archive.stat().st_size,
                   "checksum": f"md5:{digest}"}],
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata_path, archive, lock


def test_qualified_manifest_is_v3_and_only_allows_header_audit(tmp_path):
    metadata, archive, lock = _fixture(tmp_path)
    result = MODULE.audit(metadata, archive, lock)
    assert result["protocol_revision"] == "v3"
    assert result["decision"] == "QUALIFIED_FOR_HEADER_AUDIT"
    assert result["stop_reason_codes"] == []
    assert result["allowed_conclusion"] == "header_audit_may_be_designed"


def test_global_count_mismatch_blocks(tmp_path):
    metadata, archive, lock = _fixture(tmp_path, count=2)
    lock = MODULE.IdentityLock(**{**lock.__dict__, "expected_global_nodemaps": 3})
    result = MODULE.audit(metadata, archive, lock)
    assert result["decision"] == "BLOCKED_DATASET_CAPABILITY"
    assert result["stop_reason_codes"] == ["GLOBAL_NODEMAP_COUNT_MISMATCH"]


def test_mapping_basename_mismatch_blocks(tmp_path):
    metadata, archive, lock = _fixture(
        tmp_path, mapping_name="local_2d_microscopic_coordinates_coordinates_by_nodemaps.csv")
    result = MODULE.audit(metadata, archive, lock)
    assert "MAPPING_FILE_IDENTITY_MISMATCH" in result["stop_reason_codes"]


@pytest.mark.parametrize("kwargs", [{"unsafe_name": "../escape.txt"}, {"collision": True}])
def test_unsafe_or_ambiguous_paths_block(tmp_path, kwargs):
    metadata, archive, lock = _fixture(tmp_path, **kwargs)
    result = MODULE.audit(metadata, archive, lock)
    assert "UNSAFE_OR_AMBIGUOUS_MEMBER_PATH" in result["stop_reason_codes"]


def test_malformed_zip_has_fixed_reason_and_complete_schema(tmp_path):
    archive = tmp_path / "fixture.zip"
    archive.write_bytes(b"not a zip")
    digest = hashlib.md5(archive.read_bytes()).hexdigest()
    lock = MODULE.IdentityLock(record_id=7, concept_id="6", doi="10.test/fixture",
        archive_name=archive.name, archive_size=archive.stat().st_size,
        archive_md5=digest, expected_global_nodemaps=0, expected_global_connections=0)
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"id": 7, "conceptrecid": "6",
        "metadata": {"doi": "10.test/fixture", "license": {"id": "cc-by-4.0"},
                     "description": "797"},
        "files": [{"key": archive.name, "size": archive.stat().st_size,
                   "checksum": f"md5:{digest}"}]}), encoding="utf-8")
    result = MODULE.audit(metadata, archive, lock)
    assert result["stop_reason_codes"] == ["ZIP_CENTRAL_DIRECTORY_INVALID"]
    assert set(result) == {"schema_version", "experiment_id", "protocol_revision",
        "value_blinded", "scope", "official_metadata_checks", "local_archive_checks",
        "manifest_counts", "decision", "stop_reason_codes", "allowed_conclusion",
        "blocked_conclusions"}


def test_identity_failure_stops_before_zip_open(tmp_path, monkeypatch):
    metadata, archive, lock = _fixture(tmp_path)
    damaged = bytearray(archive.read_bytes())
    damaged[0] ^= 1
    archive.write_bytes(damaged)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("central directory opened after identity failure")
    monkeypatch.setattr(MODULE.zipfile, "ZipFile", forbidden)
    result = MODULE.audit(metadata, archive, lock)
    assert result["stop_reason_codes"] == ["ARCHIVE_IDENTITY_MISMATCH"]


def test_member_content_is_never_opened(tmp_path, monkeypatch):
    metadata, archive, lock = _fixture(tmp_path)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("archive member content was read")
    monkeypatch.setattr(zipfile.ZipFile, "open", forbidden)
    assert MODULE.audit(metadata, archive, lock)["decision"] == "QUALIFIED_FOR_HEADER_AUDIT"


def test_external_metadata_strings_never_reach_output(tmp_path):
    sentinel = "MALICIOUS_EXTERNAL_SENTINEL"
    metadata, archive, lock = _fixture(tmp_path, metadata_sentinel=sentinel)
    rendered = json.dumps(MODULE.audit(metadata, archive, lock))
    assert sentinel not in rendered
    assert "secret" not in rendered
    assert "n_0.txt" not in rendered


def test_output_path_guards_and_atomic_write(tmp_path):
    metadata, archive, lock = _fixture(tmp_path)
    allowed, raw = tmp_path / "audit", tmp_path / "raw"
    allowed.mkdir(); raw.mkdir()
    with pytest.raises(MODULE.AuditError):
        MODULE._validated_output_path(archive, (metadata, archive), allowed, raw)
    with pytest.raises(MODULE.AuditError):
        MODULE._validated_output_path(raw / "result.json", (metadata, archive), raw, raw)
    target = allowed / "data_audit.json"
    validated = MODULE._validated_output_path(target, (metadata, archive), allowed, raw)
    MODULE._atomic_write(validated, MODULE.audit(metadata, archive, lock))
    assert json.loads(target.read_text())["protocol_revision"] == "v3"
    assert not list(allowed.glob(".data_audit.json.*"))


def test_malformed_metadata_is_redacted_and_schema_complete(tmp_path):
    metadata, archive, lock = _fixture(tmp_path)
    metadata.write_text("{bad", encoding="utf-8")
    result = MODULE.audit(metadata, archive, lock)
    assert result["stop_reason_codes"] == ["OFFICIAL_METADATA_INVALID"]
    assert result["decision"] == "BLOCKED_DATASET_CAPABILITY"


def test_official_metadata_failure_stops_before_zip_open(tmp_path, monkeypatch):
    metadata, archive, lock = _fixture(tmp_path)
    payload = json.loads(metadata.read_text())
    payload["metadata"]["license"]["id"] = "wrong"
    metadata.write_text(json.dumps(payload), encoding="utf-8")
    def forbidden(*_args, **_kwargs):
        raise AssertionError("central directory opened after metadata failure")
    monkeypatch.setattr(MODULE.zipfile, "ZipFile", forbidden)
    assert MODULE.audit(metadata, archive, lock)["stop_reason_codes"] == [
        "OFFICIAL_METADATA_INVALID"
    ]


@pytest.mark.parametrize(
    "missing_name,reason",
    [
        ("higher_level_metadata_dictionary.json", "METADATA_DICTIONARY_IDENTITY_MISMATCH"),
        ("timestep_level_metadata_dictionary.json", "METADATA_DICTIONARY_IDENTITY_MISMATCH"),
        ("connection", "GLOBAL_CONNECTION_COUNT_MISMATCH"),
    ],
)
def test_missing_required_manifest_assets_block(tmp_path, missing_name, reason):
    metadata, archive, lock = _fixture(tmp_path)
    replacement = tmp_path / "rebuilt.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(replacement, "w") as target:
        for info in source.infolist():
            if missing_name == "connection" and "/Connections/c_0.txt" in info.filename:
                continue
            if info.filename.endswith(missing_name):
                continue
            target.writestr(info, source.read(info))
    replacement.replace(archive)
    digest = hashlib.md5(archive.read_bytes()).hexdigest()
    lock = MODULE.IdentityLock(**{**lock.__dict__, "archive_size": archive.stat().st_size,
                                  "archive_md5": digest})
    payload = json.loads(metadata.read_text())
    payload["files"][0].update({"size": archive.stat().st_size, "checksum": f"md5:{digest}"})
    metadata.write_text(json.dumps(payload), encoding="utf-8")
    assert reason in MODULE.audit(metadata, archive, lock)["stop_reason_codes"]
