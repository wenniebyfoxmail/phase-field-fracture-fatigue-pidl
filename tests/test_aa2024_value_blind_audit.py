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


def _header(cycle, crack="987.654", *, force=True):
    lines = [f"# Cycles: {cycle}"]
    if force:
        lines.append("# Force: 15 N")
    lines.extend([
        "# Displacement: 1.25 mm",
        "# Potential: 2.5 V",
        f"# Crack length: {crack} mm",
        "# Back face strain 1: 0.1",
        "# Back face strain 2: 0.2",
        "0;999999.125;888888.25",
    ])
    return "\n".join(lines) + "\n"


def _build_fixture(
    tmp_path: Path,
    *,
    count=45,
    missing_force=False,
    reset_cycle=False,
    omit_mapping=None,
    orphan_mapping=False,
    unsafe_member=False,
    duplicate_timestep=False,
):
    archive_path = tmp_path / "fixture.zip"
    mapping_rows = ["filename,cycles"]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("root/higher_level_metadata_dictionary.json", '{"material":"text"}')
        archive.writestr("root/timestep_level_metadata_dictionary.json", '{"cycles":"count"}')
        for index in range(count):
            cycle = index * 1000
            if reset_cycle and index == count // 2:
                cycle = 0
            timestep = index if not (duplicate_timestep and index == count - 1) else index - 1
            global_stem = (
                f"global_alt_{timestep}"
                if duplicate_timestep and index == count - 1
                else f"global_{timestep}"
            )
            connection_stem = (
                f"connect_alt_{timestep}"
                if duplicate_timestep and index == count - 1
                else f"connect_{timestep}"
            )
            archive.writestr(
                f"root/global_3d_dic/Nodemaps/{global_stem}.txt",
                _header(cycle, force=not (missing_force and index == 0)),
            )
            archive.writestr(
                f"root/global_3d_dic/Connections/{connection_stem}.txt",
                "id;a;b\n0;1;2\n",
            )
            local_name = f"local_{index}.txt"
            archive.writestr(
                f"root/local_2d_dic/80/Nodemaps/{local_name}", _header(cycle)
            )
            if omit_mapping != index:
                mapping_rows.append(f"{local_name},{cycle}")
        if orphan_mapping:
            mapping_rows.append("orphan.txt,1000")
        archive.writestr(
            "root/local_2d_microscopic_coordinates_by_nodemaps.csv",
            "\n".join(mapping_rows) + "\n",
        )
        if unsafe_member:
            archive.writestr("../escape.txt", "not read")

    digest = hashlib.md5(archive_path.read_bytes()).hexdigest()
    lock = MODULE.IdentityLock(
        record_id=7,
        concept_id="6",
        doi="10.test/fixture",
        archive_name=archive_path.name,
        archive_size=archive_path.stat().st_size,
        archive_md5=digest,
        expected_global_nodemaps=count,
        expected_global_connections=count,
    )
    metadata = {
        "id": 7,
        "conceptrecid": "6",
        "metadata": {
            "doi": "10.test/fixture",
            "license": {"id": "cc-by-4.0"},
            "description": (
                "797 nodemaps; direct current potential drop; "
                "every 0.5 mm of crack extension"
            ),
        },
        "files": [{
            "key": archive_path.name,
            "size": archive_path.stat().st_size,
            "checksum": f"md5:{digest}",
        }],
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata_path, archive_path, lock


def _audit(tmp_path, **kwargs):
    metadata, archive, lock = _build_fixture(tmp_path, **kwargs)
    return MODULE.audit(metadata, archive, (1000,), lock)


def test_fully_qualified_fixture_and_complete_header_counts(tmp_path):
    result = _audit(tmp_path)
    assert result["decision"] == "QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN"
    assert result["strict_checks"]["required_headers_complete"] is True
    assert all(
        value == 0
        for value in result["header_schema_and_missingness"]
        ["required_field_missing_counts"].values()
    )


@pytest.mark.parametrize(
    "kwargs,failed_gate",
    [
        ({"missing_force": True}, "required_headers_complete"),
        ({"reset_cycle": True}, "monotone_cycle_counter_by_timestep"),
        ({"omit_mapping": 0}, "local_mapping_file_join_complete"),
        ({"orphan_mapping": True}, "local_mapping_file_join_complete"),
        ({"duplicate_timestep": True}, "timestep_and_connection_identity"),
    ],
)
def test_mandatory_capability_gate_failures(tmp_path, kwargs, failed_gate):
    result = _audit(tmp_path, **kwargs)
    assert result["decision"] == "BLOCKED_DATASET_CAPABILITY"
    assert result["strict_checks"][failed_gate] is False


def test_insufficient_evaluation_resolution_is_separate_decision(tmp_path):
    result = _audit(tmp_path, count=10)
    assert result["decision"] == "BLOCKED_EVALUATION_RESOLUTION"


def test_strict_numeric_and_alias_parsing():
    assert MODULE._canonical_key("Cycles") == "cycles"
    assert MODULE._canonical_key("Cycles_missing") is None
    assert MODULE._canonical_key("Force uncertainty") is None
    assert MODULE._strict_number("1000 cycles") == 1000
    assert MODULE._strict_number("1,000") is None
    assert MODULE._strict_number("12,5") is None
    assert MODULE._strict_number("missing code -1") is None
    assert MODULE._strict_number(None) is None


def test_header_reader_rejects_duplicates_and_never_reads_field_values(tmp_path):
    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("n.txt", _header(1200))
        archive.writestr("duplicate.txt", "# Cycles: 1\n# Cycles: 2\n0;1\n")
    with zipfile.ZipFile(archive_path) as archive:
        values = MODULE._read_header(archive, archive.getinfo("n.txt"))
        assert values["cycles"] == 1200
        assert 999999.125 not in values.values()
        with pytest.raises(MODULE.AuditFormatError):
            MODULE._read_header(archive, archive.getinfo("duplicate.txt"))


def test_unsafe_manifest_stops_before_header_read(tmp_path, monkeypatch):
    metadata, archive, lock = _build_fixture(tmp_path, unsafe_member=True)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("member read occurred before manifest stop")

    monkeypatch.setattr(MODULE, "_read_header", forbidden)
    result = MODULE.audit(metadata, archive, (1000,), lock)
    assert result["decision"] == "BLOCKED_ARCHIVE_MANIFEST"


def test_complete_output_is_redacted(tmp_path):
    result = _audit(tmp_path)
    rendered = json.dumps(result)
    assert "987.654" not in rendered
    assert "999999.125" not in rendered
    assert "local_0.txt" not in rendered
    assert '"filename"' not in rendered


def test_output_collision_and_atomic_write(tmp_path):
    metadata, archive, _lock = _build_fixture(tmp_path)
    allowed = tmp_path / "audit"
    allowed.mkdir()
    with pytest.raises(MODULE.AuditFormatError):
        MODULE._validated_output_path(archive, allowed, (metadata, archive))
    target = allowed / "data_audit.json"
    validated = MODULE._validated_output_path(target, allowed, (metadata, archive))
    MODULE._atomic_json_write(validated, {"decision": "TEST"})
    assert json.loads(target.read_text())["decision"] == "TEST"
    assert not any(path.name.startswith(".data_audit.json.") for path in allowed.iterdir())


def test_horizon_support_reports_partitioned_unique_targets():
    support = MODULE._horizon_support([index * 1000 for index in range(45)], [1000])[0]
    assert support["meets_minimum_information"] is True
    assert support["sealed"]["maximum_target_reuse"] == 1
    assert support["exact_cycle_pair_count"] > 0
