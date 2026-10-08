import importlib.util
import json
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aa2024_value_blind_audit.py"
SPEC = importlib.util.spec_from_file_location("aa2024_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_key_aliases_cover_required_channels():
    assert MODULE._canonical_key("Cycles") == "cycles"
    assert MODULE._canonical_key("Force") == "force"
    assert MODULE._canonical_key("Actuator displacement") == "displacement"
    assert MODULE._canonical_key("DCPD potential") == "potential"
    assert MODULE._canonical_key("Crack length") == "cracklength"
    assert MODULE._canonical_key("Back face strain 1") == "dms_1"
    assert MODULE._canonical_key("Back face strain 2") == "dms_2"


def test_header_reader_stops_before_field_values(tmp_path):
    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "root/global_3d_dic/Nodemaps/n.txt",
            "# Cycles: 1200\n# Force: 15\n# Crack length: 12.5\n"
            "# Back face strain 1: 1.0\n# Back face strain 2: 2.0\n"
            "0;999;888\n1;777;666\n",
        )
    with zipfile.ZipFile(archive_path) as archive:
        values = MODULE._read_header(archive, archive.infolist()[0])
    assert values["cycles"] == 1200
    assert values["cracklength"] == 12.5
    assert 999 not in values.values()


def test_horizon_support_uses_distinct_cycle_origins():
    support = MODULE._horizon_support([0, 1000, 2000, 3000], [1000])
    assert support == [{
        "horizon_cycles": 1000,
        "tolerance_cycles": 100.0,
        "eligible_distinct_origins": 3,
        "eligible_origin_target_pairs": 3,
    }]


def test_official_metadata_audit_does_not_emit_description_or_outcomes():
    payload = {
        "id": MODULE.EXPECTED_RECORD_ID,
        "conceptrecid": MODULE.EXPECTED_CONCEPT_ID,
        "metadata": {
            "doi": "10.5281/zenodo.11945905",
            "license": {"id": "cc-by-4.0"},
            "description": (
                "797 files; direct current potential drop; "
                "every 0.5 mm of crack extension; secret crack values 1,2,3"
            ),
        },
        "files": [{
            "key": MODULE.EXPECTED_ARCHIVE_NAME,
            "size": MODULE.EXPECTED_SIZE,
            "checksum": f"md5:{MODULE.EXPECTED_MD5}",
        }],
    }
    audited = MODULE._official_metadata_audit(payload)
    rendered = json.dumps(audited)
    assert audited["dcpd_declared_by_record"] is True
    assert "secret crack values" not in rendered


def test_member_path_guard():
    assert MODULE._safe_member("root/global_3d_dic/Nodemaps/a.txt")
    assert not MODULE._safe_member("../escape.txt")
    assert not MODULE._safe_member("/absolute.txt")
    assert not MODULE._safe_member("windows\\escape.txt")
