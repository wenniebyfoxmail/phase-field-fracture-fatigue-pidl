#!/usr/bin/env python3
"""Audit a remote ZIP by HTTP range requests and extract only small evidence files."""

from __future__ import annotations

import argparse
import binascii
import csv
import hashlib
import json
import re
import struct
import subprocess
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


EOCD = b"PK\x05\x06"
CD = b"PK\x01\x02"
LOCAL = b"PK\x03\x04"


def get_range(url: str, start: int, end: int) -> bytes:
    result = subprocess.run(
        ["curl", "-sS", "-L", "--fail", "-r", f"{start}-{end}", url],
        check=True,
        capture_output=True,
    )
    data = result.stdout
    expected = end - start + 1
    if len(data) != expected:
        raise RuntimeError(f"range length {len(data)} != {expected}")
    return data


def remote_size(url: str) -> tuple[int, dict[str, str]]:
    result = subprocess.run(
        ["curl", "-sS", "-L", "--fail", "-r", "0-0", "-D", "-", "-o", "/dev/null", url],
        check=True,
        capture_output=True,
        text=True,
    )
    header_text = result.stdout
    matches = re.findall(r"(?im)^content-range:\s*bytes\s+0-0/(\d+)\s*$", header_text)
    if not matches:
        raise RuntimeError("missing Content-Range total")
    size = int(matches[-1])
    selected = {}
    for key in ("ETag", "Last-Modified", "Accept-Ranges"):
        values = re.findall(rf"(?im)^{re.escape(key)}:\s*(.+?)\s*$", header_text)
        if values:
            selected[key] = values[-1]
    return size, selected


def parse_entries(blob: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    pos = 0
    fmt = "<4s6H3L5H2L"
    while pos + 46 <= len(blob):
        values = struct.unpack_from(fmt, blob, pos)
        if values[0] != CD:
            raise RuntimeError(f"central-directory signature mismatch at {pos}")
        flag = values[3]
        name_len, extra_len, comment_len = values[10], values[11], values[12]
        raw_name = blob[pos + 46 : pos + 46 + name_len]
        encoding = "utf-8" if flag & 0x800 else "cp437"
        name = raw_name.decode(encoding)
        rows.append(
            {
                "path": name,
                "compression_method": values[4],
                "crc32": f"{values[7]:08x}",
                "compressed_bytes": values[8],
                "uncompressed_bytes": values[9],
                "local_header_offset": values[16],
                "is_directory": name.endswith("/"),
            }
        )
        pos += 46 + name_len + extra_len + comment_len
    if pos != len(blob):
        raise RuntimeError(f"central-directory parse ended at {pos}/{len(blob)}")
    return rows


def extract_entry(
    url: str, row: dict[str, object], output_root: Path
) -> dict[str, object]:
    offset = int(row["local_header_offset"])
    header = get_range(url, offset, offset + 29)
    values = struct.unpack("<4s5H3L2H", header)
    if values[0] != LOCAL:
        raise RuntimeError(f"local-header signature mismatch for {row['path']}")
    name_len, extra_len = values[9], values[10]
    data_start = offset + 30 + name_len + extra_len
    compressed_size = int(row["compressed_bytes"])
    payload = (
        get_range(url, data_start, data_start + compressed_size - 1)
        if compressed_size
        else b""
    )
    method = int(row["compression_method"])
    if method == 0:
        data = payload
    elif method == 8:
        data = zlib.decompress(payload, -zlib.MAX_WBITS)
    else:
        raise RuntimeError(f"unsupported compression method {method} for {row['path']}")
    if len(data) != int(row["uncompressed_bytes"]):
        raise RuntimeError(f"uncompressed size mismatch for {row['path']}")
    crc = f"{binascii.crc32(data) & 0xFFFFFFFF:08x}"
    if crc != row["crc32"]:
        raise RuntimeError(f"CRC mismatch for {row['path']}")
    relative = PurePosixPath(str(row["path"]))
    parts = relative.parts[1:] if len(relative.parts) > 1 else relative.parts
    target = output_root.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "path": str(row["path"]),
        "saved_as": str(target.relative_to(output_root)),
        "bytes": len(data),
        "crc32": crc,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    size, headers = remote_size(args.url)
    tail_size = min(size, 131072)
    tail_start = size - tail_size
    tail = get_range(args.url, tail_start, size - 1)
    pos = tail.rfind(EOCD)
    if pos < 0:
        raise RuntimeError("ZIP EOCD not found")
    _, disk, cd_disk, disk_entries, total_entries, cd_size, cd_offset, comment_len = (
        struct.unpack_from("<4s4H2LH", tail, pos)
    )
    if disk or cd_disk or disk_entries != total_entries or comment_len:
        raise RuntimeError("multi-disk or commented ZIP is outside this audit")
    central = get_range(args.url, cd_offset, cd_offset + cd_size - 1)
    entries = parse_entries(central)
    if len(entries) != total_entries:
        raise RuntimeError(f"entry count {len(entries)} != {total_entries}")

    selected_extensions = {".txt", ".xlsx", ".pdf"}
    selected = [
        row
        for row in entries
        if not row["is_directory"]
        and PurePosixPath(str(row["path"])).suffix.lower() in selected_extensions
    ]
    extraction_root = args.output / "extracted_small_files"
    extracted = [extract_entry(args.url, row, extraction_root) for row in selected]

    receipt = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": args.url,
        "remote_size_bytes": size,
        "response_headers": headers,
        "zip_entry_count": len(entries),
        "central_directory_offset": cd_offset,
        "central_directory_bytes": cd_size,
        "selected_extensions": sorted(selected_extensions),
        "extracted_file_count": len(extracted),
        "entries": entries,
        "extracted": extracted,
    }
    (args.output / "remote_zip_manifest.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (args.output / "remote_zip_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)
    print(json.dumps({key: receipt[key] for key in ("remote_size_bytes", "zip_entry_count", "extracted_file_count")}, indent=2))


if __name__ == "__main__":
    main()
