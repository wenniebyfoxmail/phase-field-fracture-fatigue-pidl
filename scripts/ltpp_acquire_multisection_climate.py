#!/usr/bin/env python3
"""Acquire and freeze official monthly climate responses for qualified LTPP sections."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path


BASE = "https://infopave.fhwa.dot.gov"
PREVIEW_ENDPOINT = "/Data/GetPreviewData"
FRONTEND_CONTRACTS = (
    "/Scripts/Data/previewSectionTimeLine.js?version=20251224",
    "/Scripts/PreviewData/PreviewData.js",
)
FIELDS = {
    "temp": "CLIMATE_TEMP",
    "precip": "CLIMATE_PRECIP",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ltpp-geoforecast-climate-freeze/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def preview_payload(section_id: int, prefix: str, event_type: str, year: int) -> dict:
    table_name = f"div_{prefix}Record_{year}_1"
    return {
        "sidx": "",
        "sord": "asc",
        "page": "1",
        "rows": "20",
        "totalRecords": 0,
        "selectedFilter": f"{table_name}|{section_id},{event_type},{year}",
        "columnDate": "",
        "schemaName": "",
        "tableName": table_name,
        "fields": 'TO_CHAR(EVENT_DATE, "MONTH"),VALUE',
        "sqlExportQuery": "",
        "moduleName": "section_timeline",
    }


def post_preview(payload: dict, timeout: float) -> bytes:
    request = urllib.request.Request(
        BASE + PREVIEW_ENDPOINT,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "ltpp-geoforecast-climate-freeze/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def post_preview_with_retry(payload: dict, timeout: float, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            body = post_preview(payload, timeout)
            decoded = json.loads(body)
            if decoded.get("Message") == "success":
                return body
            raise ValueError(str(decoded))
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"Preview request failed after {attempts} attempts: {last_error}")


def validate_monthly(body: bytes, section: str, field: str, year: int) -> dict:
    payload = json.loads(body)
    if payload.get("Message") != "success" or int(payload.get("records", 0)) != 12:
        raise ValueError(f"Incomplete response for {section} {field} {year}: {payload}")
    rows = payload.get("rows") or []
    if len(rows) != 12 or {int(row["i"]) for row in rows} != set(range(1, 13)):
        raise ValueError(f"Invalid month coverage for {section} {field} {year}")
    for row in rows:
        float(row["cell"][1])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    parser.add_argument("--lookback-years", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    gate_path = args.gate.resolve()
    output = args.output.resolve()
    if args.resume:
        output.mkdir(parents=True, exist_ok=True)
        if (output / "climate_raw_manifest.json").exists():
            raise ValueError("Refusing to resume a package that already has a final manifest")
    else:
        output.mkdir(parents=True, exist_ok=False)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    contract_root = output / "official_frontend_contract"
    contract_root.mkdir(exist_ok=args.resume)
    contracts = []
    for index, relative in enumerate(FRONTEND_CONTRACTS, start=1):
        path = contract_root / f"{index:02d}_{relative.split('/')[-1].split('?')[0]}"
        if not path.exists():
            body = fetch(BASE + relative, args.timeout_seconds)
            path.write_bytes(body)
        contracts.append(
            {"url": BASE + relative, "path": str(path.relative_to(output)), "sha256": sha256(path)}
        )

    sections = []
    request_count = 0
    network_request_count = 0
    for candidate in gate["candidates"]:
        if not candidate.get("passes_minimum_geometry_climate_gate"):
            continue
        section = candidate["section"]
        dates = [date.fromisoformat(value) for value in candidate["climate_complete_prefix_dates"]]
        if len(dates) < 2:
            raise ValueError(f"Section has fewer than two qualified surveys: {section}")
        section_root = output / section
        section_root.mkdir(exist_ok=args.resume)
        files = []
        if args.lookback_years < 0:
            raise ValueError("lookback-years must be non-negative")
        year_start = dates[0].year - args.lookback_years
        for year in range(year_start, dates[-1].year + 1):
            for prefix, event_type in FIELDS.items():
                request_payload = preview_payload(candidate["ldw_section_id"], prefix, event_type, year)
                response_path = section_root / f"{prefix}_{year}.json"
                request_path = section_root / f"{prefix}_{year}.request.json"
                if response_path.exists() or request_path.exists():
                    if not (response_path.exists() and request_path.exists()):
                        raise ValueError(f"Incomplete resumed pair: {section} {prefix} {year}")
                    validate_monthly(response_path.read_bytes(), section, prefix, year)
                    if json.loads(request_path.read_text(encoding="utf-8")) != request_payload:
                        raise ValueError(f"Request drift in resumed pair: {request_path}")
                else:
                    body = post_preview_with_retry(request_payload, args.timeout_seconds)
                    validate_monthly(body, section, prefix, year)
                    response_path.write_bytes(body)
                    request_path.write_text(
                        json.dumps(request_payload, indent=2) + "\n", encoding="utf-8"
                    )
                    network_request_count += 1
                files.append(
                    {
                        "field": prefix,
                        "event_type": event_type,
                        "year": year,
                        "response_path": str(response_path.relative_to(output)),
                        "response_sha256": sha256(response_path),
                        "request_path": str(request_path.relative_to(output)),
                        "request_sha256": sha256(request_path),
                    }
                )
                request_count += 1
                if args.delay_seconds:
                    time.sleep(args.delay_seconds)
        sections.append(
            {
                "section": section,
                "ldw_section_id": candidate["ldw_section_id"],
                "construction_number": candidate["construction_number"],
                "survey_dates": [value.isoformat() for value in dates],
                "year_start": year_start,
                "year_end": dates[-1].year,
                "files": files,
            }
        )

    manifest = {
        "status": "PASS_OFFICIAL_MONTHLY_CLIMATE_FROZEN",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_base": BASE,
        "official_preview_endpoint": BASE + PREVIEW_ENDPOINT,
        "gate": str(gate_path),
        "gate_sha256": sha256(gate_path),
        "frontend_contracts": contracts,
        "section_count": len(sections),
        "request_count": request_count,
        "network_request_count_this_invocation": network_request_count,
        "lookback_years": args.lookback_years,
        "fields": FIELDS,
        "sections": sections,
        "claim_boundary": "Official monthly temperature and precipitation responses; no pavement moisture or continuous traffic is inferred.",
    }
    manifest_path = output / "climate_raw_manifest.json"
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
                "requests": request_count,
                "manifest_sha256": sha256(manifest_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
