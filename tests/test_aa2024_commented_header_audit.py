import hashlib
import importlib.util
import io
import json
import lzma
import stat
import struct
import sys
import zipfile
import zlib
from decimal import Decimal
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aa2024_commented_header_audit.py"
SPEC = importlib.util.spec_from_file_location("aa2024_commented", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


SCHEMA = (
    "ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; "
    "epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n"
)


def _header(stage: int, *, cycles: float | None = None,
            cracklength: float | None = None, drop: str | None = None,
            schema: str = SCHEMA, header_stage: int | str | None = None,
            relative_date: float | str | None = None,
            pre_schema_comment: str = "") -> str:
    values = {
        "current_stage_index": stage if header_stage is None else header_stage,
        "current_stage_relative_date": (
            float(stage) if relative_date is None else relative_date
        ),
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
    if pre_schema_comment:
        lines.append(pre_schema_comment)
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
        tmp_path, header_kwargs={2: {"schema": "ID; x_undef [mm]; u [mm]\n"}}
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


def test_connection_directories_cannot_satisfy_pairing(tmp_path):
    archive = tmp_path / "directories.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage),
            )
            zf.writestr(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt/",
                b"",
            )
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert result["sequence_checks"]["global_connection_count"] == 0
    assert "GLOBAL_STAGE_PAIRING_INVALID" in result["stop_reason_codes"]


def test_unix_directory_metadata_without_slash_cannot_satisfy_pairing(tmp_path):
    archive = tmp_path / "mode-directories.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage),
            )
            info = zipfile.ZipInfo(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt"
            )
            info.create_system = 3
            info.external_attr = (stat.S_IFDIR | 0o755) << 16
            zf.writestr(info, b"")
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert result["sequence_checks"]["global_connection_count"] == 0
    assert "GLOBAL_STAGE_PAIRING_INVALID" in result["stop_reason_codes"]


def test_dos_directory_metadata_without_slash_cannot_satisfy_pairing(tmp_path):
    archive = tmp_path / "dos-directories.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage),
            )
            info = zipfile.ZipInfo(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt"
            )
            info.create_system = 0
            info.external_attr = 0x10
            zf.writestr(info, b"")
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert result["sequence_checks"]["global_connection_count"] == 0
    assert "GLOBAL_STAGE_PAIRING_INVALID" in result["stop_reason_codes"]


def test_actual_noncomment_schema_controls_decision(tmp_path):
    misleading = "# ID; x_undef; y_undef; z_undef; u; v; w; epsx; epsy; epsxy; epseqv\n"
    archive, size, digest = _fixture(
        tmp_path,
        header_kwargs={
            2: {"pre_schema_comment": misleading, "schema": "ID; u\n"},
        },
    )
    result = _audit(archive, size, digest)
    assert "NODEMAP_HEADER_INVALID" in result["stop_reason_codes"]
    assert result["sequence_checks"]["stable_required_nodemap_schema"] is False


def test_real_commented_schema_form_qualifies_synthetic_sequence(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={s: {"schema": "# " + SCHEMA} for s in (1, 2, 3)}
    )
    result = _audit(archive, size, digest)
    assert result["decision"] == "QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE"
    assert set(result["component_states"].values()) == {"passed"}


def test_commented_schema_stops_after_first_numeric_byte():
    payload = _header(1, schema="# " + SCHEMA).encode()
    handle = io.BytesIO(payload)
    class Archive:
        def open(self, *_):
            class Context:
                def __enter__(self): return handle
                def __exit__(self, *_): return False
            return Context()
    fields, schema = MODULE._read_header(Archive(), None)
    assert fields["current_stage_index"] == 1
    assert schema == MODULE.REQUIRED_COLUMN_TOKENS
    assert handle.tell() == payload.index(b"\n1;") + 2


def test_multiple_commented_schemas_fail_before_later_member(tmp_path, monkeypatch):
    archive, size, digest = _fixture(tmp_path, header_kwargs={
        1: {"pre_schema_comment": "# " + SCHEMA, "schema": "# " + SCHEMA}
    })
    original = zipfile.ZipFile.open
    opened = []
    def traced(self, member, *args, **kwargs):
        name = member.filename if hasattr(member, "filename") else member
        opened.append(name)
        assert name.endswith("results_1_1.txt")
        return original(self, member, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "open", traced)
    result = _audit(archive, size, digest)
    assert len(opened) == 1
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_incomplete_commented_schema_cannot_qualify(tmp_path):
    archive, size, digest = _fixture(tmp_path, header_kwargs={
        1: {"schema": "# ID; u\n"}
    })
    result = _audit(archive, size, digest)
    assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
    assert result["component_states"]["discovery_and_pairing"] == "passed"
    assert result["component_states"]["header_parsing"] == "inconclusive"
    assert result["component_states"]["state_variation"] == "not_assessed"


def test_matching_explicit_header_after_comment_is_checked(tmp_path):
    archive, size, digest = _fixture(tmp_path, header_kwargs={
        1: {"pre_schema_comment": "# " + SCHEMA}
    })
    assert _audit(archive, size, digest)["decision"] == "QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE"


def test_numeric_row_is_rejected_at_first_byte():
    handle = io.BytesIO(b"1; 0; 0; 0; 0; 0\n")
    try:
        MODULE._read_bounded_line(handle, 0)
    except MODULE.AuditError:
        pass
    else:
        raise AssertionError("numerical row was accepted as a header")
    assert handle.tell() == 1


def test_numeric_row_after_ascii_whitespace_stops_at_numeric_prefix():
    prefix = b" \t\v\f\r"
    handle = io.BytesIO(prefix + b"1; 0; 0; 0; 0; 0\n")
    try:
        MODULE._read_bounded_line(handle, 0)
    except MODULE.AuditError:
        pass
    else:
        raise AssertionError("whitespace-prefixed numerical row was accepted")
    assert handle.tell() == len(prefix) + 1


def test_nonascii_leading_prefix_fails_before_complete_row_is_read():
    handle = io.BytesIO("\u00a01; 0; 0\n".encode("utf-8"))
    try:
        MODULE._read_bounded_line(handle, 0)
    except MODULE.AuditError:
        pass
    else:
        raise AssertionError("non-ASCII leading prefix was accepted")
    assert handle.tell() == 1


def test_whitespace_prefixed_numeric_rows_are_full_audit_parser_failures(tmp_path):
    for index, prefix in enumerate((b"\x0b", b"\x0c", "\u00a0".encode("utf-8"))):
        archive = tmp_path / f"whitespace-prefix-{index}.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for stage in (1, 2):
                header = _header(stage).encode("utf-8").replace(
                    SCHEMA.encode("utf-8"),
                    prefix + b"1; 0; 0; 0; 0; 0; 0; 0; 0; 0; 0\n",
                )
                zf.writestr(
                    f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                    header,
                )
                zf.writestr(
                    "global_3d_dic/Connections/"
                    f"global_3d_dic_results_1_{stage}_connections.txt",
                    "connection header only\n",
                )
        result = _audit(
            archive, archive.stat().st_size,
            hashlib.md5(archive.read_bytes()).hexdigest(),
        )
        assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
        assert result["allowed_conclusion"] == "qualification_not_established"
        assert result["sequence_checks"]["nodemap_body_rows_read"] == 0


def test_header_cap_is_enforced_without_overread(tmp_path):
    overlong = "#" + ("x" * MODULE.HEADER_BYTE_CAP) + "\n"
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={1: {"pre_schema_comment": overlong}}
    )
    result = _audit(archive, size, digest)
    assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_first_stage_failure_prevents_later_header_access(tmp_path, monkeypatch):
    archive, size, digest = _fixture(tmp_path)
    original = MODULE._read_header
    opened = []

    def guarded(zip_file, info):
        opened.append(info.filename)
        if "_2.txt" in info.filename:
            raise MODULE.AuditError("synthetic stage-2 failure")
        if "_3.txt" in info.filename:
            raise AssertionError("stage 3 opened after stage-2 failure")
        return original(zip_file, info)

    monkeypatch.setattr(MODULE, "_read_header", guarded)
    result = _audit(archive, size, digest)
    assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
    assert not any("_3.txt" in name for name in opened)


def test_decimal_stage_identity_is_exact(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={1: {"header_stage": "1.0000000000000001"}}
    )
    result = _audit(archive, size, digest)
    assert "STAGE_IDENTITY_INVALID" in result["stop_reason_codes"]


def test_decimal_chronology_is_exact(tmp_path):
    archive, size, digest = _fixture(
        tmp_path,
        header_kwargs={
            1: {"relative_date": "1.0000000000000001"},
            2: {"relative_date": "1.0000000000000000"},
        },
    )
    result = _audit(archive, size, digest)
    assert "CHRONOLOGY_INVALID" in result["stop_reason_codes"]


def test_malformed_value_element_is_controlled_and_inconclusive(tmp_path):
    bad_header = _header(1).replace(
        "# force : value_element : 101.0", "# force : value_element"
    )
    archive = tmp_path / "malformed-field.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                bad_header if stage == 1 else _header(stage),
            )
            zf.writestr(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt",
                "connection header only\n",
            )
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_huge_stage_identifier_is_controlled_and_inconclusive(tmp_path):
    huge = "9" * 5000
    archive = tmp_path / "huge-stage.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{huge}.txt",
            _header(1),
        )
        zf.writestr(
            "global_3d_dic/Connections/"
            f"global_3d_dic_results_1_{huge}_connections.txt",
            "connection header only\n",
        )
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert "STAGE_ID_PARSE_INVALID" in result["stop_reason_codes"]
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_member_decode_and_decompression_failures_are_controlled(
    tmp_path, monkeypatch
):
    archive, size, digest = _fixture(tmp_path)
    for failure in (
        UnicodeDecodeError("utf-8", b"x", 0, 1, "bad local name"),
        zlib.error("bad deflate stream"),
        lzma.LZMAError("bad lzma stream"),
    ):
        monkeypatch.setattr(
            MODULE, "_read_header",
            lambda *_args, failure=failure: (_ for _ in ()).throw(failure),
        )
        result = _audit(archive, size, digest)
        assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
        assert result["allowed_conclusion"] == "qualification_not_established"


def test_actual_corrupt_lzma_prefix_is_controlled_and_inconclusive(tmp_path):
    archive = tmp_path / "corrupt-lzma.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_LZMA) as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage),
            )
            zf.writestr(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt",
                "connection header only\n",
            )
    with zipfile.ZipFile(archive, "r") as zf:
        first = next(info for info in zf.infolist() if "Nodemaps" in info.filename)
        header_offset = first.header_offset
    payload = bytearray(archive.read_bytes())
    filename_len, extra_len = struct.unpack_from("<HH", payload, header_offset + 26)
    compressed_offset = header_offset + 30 + filename_len + extra_len
    payload[compressed_offset + 4] = 0xFF
    archive.write_bytes(payload)

    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert result["stop_reason_codes"] == ["NODEMAP_HEADER_INVALID"]
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_stage_id_parse_failure_prevents_all_header_access(tmp_path, monkeypatch):
    huge = "9" * 5000
    archive = tmp_path / "mixed-huge-stage.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stage in (1, 2):
            zf.writestr(
                f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt",
                _header(stage),
            )
            zf.writestr(
                "global_3d_dic/Connections/"
                f"global_3d_dic_results_1_{stage}_connections.txt",
                "connection header only\n",
            )
        zf.writestr(
            f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{huge}.txt",
            _header(3),
        )
        zf.writestr(
            "global_3d_dic/Connections/"
            f"global_3d_dic_results_1_{huge}_connections.txt",
            "connection header only\n",
        )

    monkeypatch.setattr(
        MODULE, "_read_header",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("header read after stage-ID parse failure")
        ),
    )
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    assert "STAGE_ID_PARSE_INVALID" in result["stop_reason_codes"]
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_empty_archive_never_reports_positive_whole_sequence_coverage(tmp_path):
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w"):
        pass
    result = _audit(
        archive, archive.stat().st_size,
        hashlib.md5(archive.read_bytes()).hexdigest(),
    )
    checks = result["sequence_checks"]
    assert checks["all_headers_parsed"] is False
    assert checks["required_fields_complete"] is False
    assert checks["stage_identity_matches"] is False
    assert checks["chronology_nondecreasing"] is False
    assert checks["stable_required_nodemap_schema"] is False


def test_partial_header_coverage_never_reports_stable_schema(tmp_path):
    archive, size, digest = _fixture(
        tmp_path, header_kwargs={2: {"drop": "cycles"}}
    )
    result = _audit(archive, size, digest)
    checks = result["sequence_checks"]
    assert checks["all_headers_parsed"] is False
    assert checks["stable_required_nodemap_schema"] is False
    assert result["allowed_conclusion"] == "qualification_not_established"


def test_decimal_parser_preserves_exact_values():
    assert MODULE._parse_numeric("1.0000000000000001") == Decimal(
        "1.0000000000000001"
    )
