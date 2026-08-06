#!/usr/bin/env python3
"""Freeze the exact InfoPave tables used by the six-section enriched-input gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.cookiejar
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE = "https://infopave.fhwa.dot.gov"
TABLE_EXPORT = "/Data/TableExport/"
TOKEN = "/Home/LoadPartialView"
DICTIONARY = "/Data/GetTableDictionaryInformation"
PREVIEW = "/Data/GetPreviewData"
TABLES = (
    "TRF_TREND",
    "SECTION_LAYER_STRUCTURE",
    "MON_DEFL_MASTER",
    "MON_DEFL_LOC_INFO",
    "MON_DEFL_DROP_DATA",
    "MON_DEFL_DEV_CONFIG",
    "MON_DEFL_DEV_SENSORS",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class InfoPaveClient:
    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
        self.page_html = self._get(TABLE_EXPORT).decode("utf-8")
        self.schema_by_table = dict(
            re.findall(
                r'tablename="([A-Z0-9_]+)"\s+schemaname="([A-Z0-9_]+)',
                self.page_html,
            )
        )

    def _get(self, path: str) -> bytes:
        request = urllib.request.Request(
            BASE + path,
            headers={"User-Agent": "ltpp-enriched-input-freeze/1.0"},
        )
        with self.opener.open(request, timeout=60) as response:
            return response.read()

    def token(self) -> str:
        markup = self._get(TOKEN).decode("utf-8")
        match = re.search(r'id="appToken"[^>]*value="([^"]+)"', markup)
        if not match:
            raise RuntimeError("InfoPave application token was not found")
        return match.group(1)

    def post_json(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": self.token(),
                "Content-Type": "application/json; charset=utf-8",
                "Referer": BASE + TABLE_EXPORT,
                "User-Agent": "ltpp-enriched-input-freeze/1.0",
                "X-Requested-With": "XMLHttpRequest",
            },
            method="POST",
        )
        with self.opener.open(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("isSuccess") is False:
            raise RuntimeError(f"InfoPave rejected request: {result.get('Message')}")
        return result

    def section_filter(self, ldw_section_id: int) -> list[dict]:
        needle = "sltModel.getAttributeData("
        call = self.page_html.rindex(needle) + len(needle)
        start = self.page_html.index("[", call)
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index in range(start, len(self.page_html)):
            char = self.page_html[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise RuntimeError("Could not parse InfoPave section-filter model")
        model = json.loads(self.page_html[start:end])
        for entry in model:
            entry["ISATTRIBUTESELECTED"] = False
            entry["whereClause"] = ""
            entry["andWhereClause"] = ""
        section = next(x for x in model if x["ATTRIBUTE_CODE"] == "SECTION")
        section["ISATTRIBUTESELECTED"] = True
        section["whereClause"] = f"in (%27{ldw_section_id}%27)"
        return model

    def page(
        self,
        table: str,
        schema: str,
        fields: list[str],
        sort_fields: list[str],
        page_number: int,
        page_size: int,
        selected_filter: list[dict],
    ) -> tuple[dict, dict]:
        payload = {
            "sidx": ",".join(sort_fields),
            "sord": "asc",
            "page": str(page_number),
            "rows": str(page_size),
            "selectedFilter": json.dumps(selected_filter, separators=(",", ":")),
            "schemaName": schema,
            "tableName": table,
            "fields": ",".join(fields),
            "sqlExportQuery": "",
            "totalRecords": "0",
            "moduleName": "tableexport",
        }
        return payload, self.post_json(PREVIEW, payload)


def acquire_table(
    client: InfoPaveClient,
    section: str,
    ldw_section_id: int,
    table: str,
    root: Path,
    page_size: int,
) -> dict:
    dictionary = client.post_json(DICTIONARY, {"tableName": table})
    dictionary_path = root / f"{table}.dictionary.json"
    dictionary_path.write_text(
        json.dumps(dictionary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    entries = dictionary.get("tableDictionary") or []
    if not entries:
        raise RuntimeError(f"Required table has no dictionary: {table}")
    fields = [entry["FIELD_NAME"] for entry in entries]
    keys = [entry["FIELD_NAME"] for entry in entries if entry.get("FIELD_KEY") == "PK"]
    schema = client.schema_by_table.get(table) or entries[0].get("SCHEMA_NAME")
    if not schema:
        raise RuntimeError(f"No schema found for {table}")
    selected_filter = client.section_filter(ldw_section_id)
    request_payload, first = client.page(
        table,
        schema,
        fields,
        (keys or fields[:1])[:1],
        1,
        page_size,
        selected_filter,
    )
    request_path = root / f"{table}.request.json"
    request_path.write_text(
        json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    page_count = int(first.get("total") or 0)
    expected = int(first.get("records") or 0)
    raw_pages = [first]
    rows = list(first.get("rows") or [])
    for page_number in range(2, page_count + 1):
        _, response = client.page(
            table,
            schema,
            fields,
            (keys or fields[:1])[:1],
            page_number,
            page_size,
            selected_filter,
        )
        raw_pages.append(response)
        rows.extend(response.get("rows") or [])
    raw_pages_path = root / f"{table}.raw_pages.json"
    raw_pages_path.write_text(
        json.dumps(raw_pages, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cells = [tuple(row.get("cell") or []) for row in rows]
    unique_cells = list(dict.fromkeys(cells))
    if any(len(cell) != len(fields) for cell in unique_cells):
        raise RuntimeError(f"{section} {table}: response width does not match dictionary")
    if expected != len(unique_cells):
        raise RuntimeError(
            f"{section} {table}: server records={expected}, downloaded={len(unique_cells)}"
        )
    if "STATE_CODE" in fields and "SHRP_ID" in fields:
        state_index = fields.index("STATE_CODE")
        shrp_index = fields.index("SHRP_ID")
        expected_state, expected_shrp = section.split("-", 1)
        escaped = [
            cell
            for cell in unique_cells
            if str(cell[state_index]).zfill(2) != expected_state
            or str(cell[shrp_index]) != expected_shrp
        ]
        if escaped:
            raise RuntimeError(f"{section} {table}: {len(escaped)} rows escaped filter")
    csv_path = root / f"{table}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(unique_cells)
    return {
        "table": table,
        "schema": schema,
        "field_count": len(fields),
        "primary_key": keys,
        "row_count": len(unique_cells),
        "server_record_count": expected,
        "page_count": page_count,
        "csv": str(csv_path.relative_to(root.parent)),
        "csv_sha256": sha256(csv_path),
        "dictionary_sha256": sha256(dictionary_path),
        "request_sha256": sha256(request_path),
        "raw_pages_sha256": sha256(raw_pages_path),
        "field_units": {
            entry["FIELD_NAME"]: {
                "stored_unit": entry.get("UNITS"),
                "converted_unit": entry.get("CONVERTED_UNIT"),
                "conversion_factor": entry.get("CONVERSION_FACTOR"),
            }
            for entry in entries
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    gate_path = args.gate.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    sections = [
        {"section": row["section"], "ldw_section_id": row["ldw_section_id"]}
        for row in gate["candidates"]
        if row.get("passes_minimum_geometry_climate_gate")
    ]
    if len(sections) != 6:
        raise ValueError(f"Expected six qualified sections, found {len(sections)}")
    client = InfoPaveClient()
    section_receipts = []
    for section_row in sections:
        section = section_row["section"]
        ldw_section_id = int(section_row["ldw_section_id"])
        section_root = output / section
        section_root.mkdir()
        tables = [
            acquire_table(
                client,
                section,
                ldw_section_id,
                table,
                section_root,
                args.page_size,
            )
            for table in TABLES
        ]
        section_receipts.append(
            {"section": section, "ldw_section_id": ldw_section_id, "tables": tables}
        )
    manifest = {
        "status": "PASS_OFFICIAL_ENRICHED_TABLES_FROZEN",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_source": BASE + TABLE_EXPORT,
        "source_release": "SDR 39",
        "method": "public Table Export preview endpoint with official structured section filter",
        "gate": str(gate_path),
        "gate_sha256": sha256(gate_path),
        "section_count": len(sections),
        "required_tables": list(TABLES),
        "sections": section_receipts,
        "claim_boundary": "Raw source-time inputs only; no endpoint fitting or outcome inspection.",
    }
    manifest_path = output / "raw_data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    hashed = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "raw_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output)}\n" for path in hashed),
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "sections": len(sections),
                "tables_per_section": len(TABLES),
                "manifest_sha256": sha256(manifest_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
