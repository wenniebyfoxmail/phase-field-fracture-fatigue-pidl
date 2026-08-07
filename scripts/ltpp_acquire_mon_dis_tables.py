#!/usr/bin/env python3
"""Freeze all section-scoped MON_DIS tables exposed by public InfoPave."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ltpp_acquire_fwd_tables import (
    BASE,
    TABLE_EXPORT,
    InfoPaveClient,
    acquire_table,
    file_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    client = InfoPaveClient()
    tables = sorted(
        table for table in client.schema_by_table if table.startswith("MON_DIS")
    )
    if not tables:
        raise RuntimeError("InfoPave exposed no MON_DIS tables")
    if len(tables) > 60:
        raise RuntimeError(f"Refusing unexpected MON_DIS table count: {len(tables)}")

    summaries = [
        acquire_table(client, table, args.output, args.page_size) for table in tables
    ]
    summary = {
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": BASE + TABLE_EXPORT,
        "source_release": "SDR 39",
        "section": "06-1253",
        "ldw_section_id": 2056,
        "method": "public Table Export preview endpoint with official structured section filter",
        "scope": "raw MON_DIS acquisition for external QC; no label mutation or model authorization",
        "discovered_table_count": len(tables),
        "tables": summaries,
    }
    summary_path = args.output / "acquisition_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in args.output.iterdir() if path.is_file())
    (args.output / "raw_files.sha256").write_text(
        "".join(f"{file_sha256(path)}  {path.name}\n" for path in files),
        encoding="ascii",
    )
    frozen = [row for row in summaries if row["status"] == "frozen"]
    print(
        json.dumps(
            {
                "table_count": len(tables),
                "frozen_table_count": len(frozen),
                "total_rows": sum(row["row_count"] for row in frozen),
                "tables_with_rows": [
                    row["table"] for row in frozen if row["row_count"] > 0
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
