#!/usr/bin/env python3
"""Freeze section-scoped LTPP FWD/backcal tables from public InfoPave."""

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
    "MON_DEFL_MASTER",
    "MON_DEFL_LOC_INFO",
    "MON_DEFL_DROP_DATA",
    "MON_DEFL_DEV_CONFIG",
    "MON_DEFL_DEV_SENSORS",
    "MON_DEFL_TEMP_DEPTHS",
    "MON_DEFL_TEMP_VALUES",
    "BAKCAL_BASIN",
    "BAKCAL_MODULUS_BASIN_MASTER",
    "BAKCAL_BEST_FIT_BASIN_MASTER",
    "BAKCAL_MODULUS_BASIN_LAYER",
    "BAKCAL_BEST_FIT_BASIN_LAYER",
    "BAKCAL_MODULUS_SECTION_LAYER",
    "BAKCAL_BEST_FIT_SECTION_LAYER",
    "BAKCAL_STRUCTURE_LAYERS",
    "BAKCAL_BEST_FIT_LAYERS",
    "BAKCAL_LAYER_LINK",
    "BAKCAL_PASS",
    "BAKCAL_MODULUS_SECTION_MASTER",
    "BAKCAL_BEST_FIT_SECTION_MASTER",
)


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
        self.filter_model = self._section_filter_model(self.page_html, "2056")

    def _get(self, path: str) -> bytes:
        request = urllib.request.Request(
            BASE + path,
            headers={"User-Agent": "LTPP-06-1253-acquisition/1.0"},
        )
        with self.opener.open(request, timeout=60) as response:
            return response.read()

    def _token(self) -> str:
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
                "Authorization": self._token(),
                "Content-Type": "application/json; charset=utf-8",
                "Referer": BASE + TABLE_EXPORT,
                "User-Agent": "LTPP-06-1253-acquisition/1.0",
                "X-Requested-With": "XMLHttpRequest",
            },
            method="POST",
        )
        with self.opener.open(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("isSuccess") is False:
            raise RuntimeError(f"InfoPave rejected request: {result.get('Message')}")
        return result

    @staticmethod
    def _section_filter_model(page_html: str, section_id: str) -> list[dict]:
        needle = "sltModel.getAttributeData("
        call = page_html.rindex(needle) + len(needle)
        start = page_html.index("[", call)
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index in range(start, len(page_html)):
            char = page_html[index]
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
        model = json.loads(page_html[start:end])
        for entry in model:
            entry["ISATTRIBUTESELECTED"] = False
            entry["whereClause"] = ""
            entry["andWhereClause"] = ""
        section = next(x for x in model if x["ATTRIBUTE_CODE"] == "SECTION")
        section["ISATTRIBUTESELECTED"] = True
        section["whereClause"] = f"in (%27{section_id}%27)"
        return model

    def dictionary(self, table: str) -> dict:
        return self.post_json(DICTIONARY, {"tableName": table})

    def page(
        self,
        table: str,
        schema: str,
        fields: list[str],
        sort_fields: list[str],
        page_number: int,
        page_size: int,
    ) -> tuple[dict, dict]:
        payload = {
            "sidx": ",".join(sort_fields),
            "sord": "asc",
            "page": str(page_number),
            "rows": str(page_size),
            "selectedFilter": json.dumps(self.filter_model, separators=(",", ":")),
            "schemaName": schema,
            "tableName": table,
            "fields": ",".join(fields),
            "sqlExportQuery": "",
            "totalRecords": "0",
            "moduleName": "tableexport",
        }
        return payload, self.post_json(PREVIEW, payload)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_table(
    client: InfoPaveClient, table: str, root: Path, page_size: int
) -> dict:
    dictionary = client.dictionary(table)
    (root / f"{table}.dictionary.json").write_text(
        json.dumps(dictionary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    entries = dictionary.get("tableDictionary") or []
    if not entries:
        return {"table": table, "status": "dictionary_absent", "row_count": 0}
    fields = [entry["FIELD_NAME"] for entry in entries]
    keys = [entry["FIELD_NAME"] for entry in entries if entry.get("FIELD_KEY") == "PK"]
    schema = client.schema_by_table.get(table) or entries[0].get("SCHEMA_NAME")
    if not schema:
        raise RuntimeError(f"No schema found for {table}")

    request_payload, first = client.page(
        table, schema, fields, (keys or fields[:1])[:1], 1, page_size
    )
    (root / f"{table}.request.json").write_text(
        json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pages = int(first.get("total") or 0)
    expected = int(first.get("records") or 0)
    raw_pages = [first]
    rows = list(first.get("rows") or [])
    for number in range(2, pages + 1):
        _, response = client.page(
            table, schema, fields, (keys or fields[:1])[:1], number, page_size
        )
        raw_pages.append(response)
        rows.extend(response.get("rows") or [])

    (root / f"{table}.raw_pages.json").write_text(
        json.dumps(raw_pages, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cells = [tuple(row.get("cell") or []) for row in rows]
    unique_cells = list(dict.fromkeys(cells))
    if any(len(cell) != len(fields) for cell in unique_cells):
        raise RuntimeError(f"{table}: response width does not match dictionary fields")
    state_index = fields.index("STATE_CODE") if "STATE_CODE" in fields else None
    shrp_index = fields.index("SHRP_ID") if "SHRP_ID" in fields else None
    wrong_section = 0
    if state_index is not None and shrp_index is not None:
        wrong_section = sum(
            str(cell[state_index]).zfill(2) != "06" or str(cell[shrp_index]) != "1253"
            for cell in unique_cells
        )
    if wrong_section:
        raise RuntimeError(f"{table}: {wrong_section} rows escaped section filter")
    if expected != len(unique_cells):
        raise RuntimeError(
            f"{table}: server records={expected}, unique downloaded={len(unique_cells)}"
        )

    with (root / f"{table}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(unique_cells)
    return {
        "table": table,
        "status": "frozen",
        "schema": schema,
        "field_count": len(fields),
        "primary_key": keys,
        "row_count": len(unique_cells),
        "server_record_count": expected,
        "page_count": pages,
        "wrong_section_rows": wrong_section,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    client = InfoPaveClient()
    summaries = [
        acquire_table(client, table, args.output, args.page_size) for table in TABLES
    ]
    summary = {
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": BASE + TABLE_EXPORT,
        "source_release": "SDR 39",
        "section": "06-1253",
        "ldw_section_id": 2056,
        "method": "public Table Export preview endpoint with official structured section filter",
        "scope": "raw table acquisition only; no Ferrite or PIDL authorization",
        "tables": summaries,
    }
    (args.output / "acquisition_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in args.output.iterdir() if path.is_file())
    (args.output / "raw_files.sha256").write_text(
        "".join(f"{file_sha256(path)}  {path.name}\n" for path in files),
        encoding="ascii",
    )


if __name__ == "__main__":
    main()
