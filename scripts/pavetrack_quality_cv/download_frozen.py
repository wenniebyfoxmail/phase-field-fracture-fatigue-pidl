#!/usr/bin/env python3
"""Extract selected ZIP members with a small number of verified HTTP ranges."""

from __future__ import annotations

import argparse
import binascii
import io
import json
from pathlib import Path
import struct
import time
import zipfile
import zlib

import requests


def get_range(url: str, start: int, end: int, attempts: int = 10) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                headers={"Range": f"bytes={start}-{end}"},
                timeout=600,
            )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 0.0
                except ValueError:
                    delay = 0.0
                delay = max(delay, min(300.0, 30.0 * (2**attempt)))
                raise RuntimeError(f"rate_limited retry_after_s={delay:g}")
            response.raise_for_status()
            if response.status_code != 206:
                raise RuntimeError(f"server ignored range request: {response.status_code}")
            expected = end - start + 1
            if len(response.content) != expected:
                raise RuntimeError(
                    f"short range response: {len(response.content)} != {expected}"
                )
            return response.content
        except Exception as exc:
            last_error = exc
            if "rate_limited retry_after_s=" in str(exc):
                delay = float(str(exc).rsplit("=", 1)[-1])
            else:
                delay = min(60.0, 2**attempt)
            print(
                f"range retry {attempt + 1}/{attempts} bytes={start}-{end} "
                f"delay={delay:g}s error={exc}",
                flush=True,
            )
            time.sleep(delay)
    assert last_error is not None
    raise last_error


class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url: str, size: int, chunk_size: int = 2 * 1024 * 1024):
        self.url = url
        self.size = size
        self.chunk_size = chunk_size
        self.position = 0
        self.cache: dict[int, bytes] = {}

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            target = offset
        elif whence == io.SEEK_CUR:
            target = self.position + offset
        elif whence == io.SEEK_END:
            target = self.size + offset
        else:
            raise ValueError(f"unsupported whence {whence}")
        if not 0 <= target <= self.size:
            raise ValueError(f"seek outside remote object: {target}")
        self.position = target
        return target

    def _chunk(self, index: int) -> bytes:
        if index not in self.cache:
            start = index * self.chunk_size
            end = min(self.size - 1, start + self.chunk_size - 1)
            self.cache[index] = get_range(self.url, start, end)
        return self.cache[index]

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        chunks = []
        remaining = size
        while remaining:
            index = self.position // self.chunk_size
            offset = self.position % self.chunk_size
            block = self._chunk(index)
            take = min(remaining, len(block) - offset)
            chunks.append(block[offset : offset + take])
            self.position += take
            remaining -= take
        return b"".join(chunks)


def safe_name(name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe ZIP member {name!r}")
    return path


def verify_payload(info: zipfile.ZipInfo, payload: bytes) -> None:
    if len(payload) != info.file_size:
        raise RuntimeError(f"size mismatch for {info.filename}")
    if (binascii.crc32(payload) & 0xFFFFFFFF) != info.CRC:
        raise RuntimeError(f"CRC mismatch for {info.filename}")


def decode_member(info: zipfile.ZipInfo, block: bytes, block_start: int) -> bytes:
    offset = info.header_offset - block_start
    header = block[offset : offset + 30]
    if len(header) != 30:
        raise RuntimeError(f"short local header for {info.filename}")
    fields = struct.unpack("<4s5H3I2H", header)
    if fields[0] != b"PK\x03\x04":
        raise RuntimeError(f"bad local header for {info.filename}")
    filename_length, extra_length = fields[-2:]
    data_start = offset + 30 + filename_length + extra_length
    compressed = block[data_start : data_start + info.compress_size]
    if len(compressed) != info.compress_size:
        raise RuntimeError(f"short compressed payload for {info.filename}")
    if info.compress_type == zipfile.ZIP_STORED:
        payload = compressed
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        payload = zlib.decompress(compressed, -15)
    else:
        raise RuntimeError(
            f"unsupported ZIP compression {info.compress_type} for {info.filename}"
        )
    verify_payload(info, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--locations", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--max-range-mib", type=int, default=32)
    parser.add_argument("--max-gap-mib", type=int, default=2)
    parser.add_argument("--delay-s", type=float, default=1.0)
    args = parser.parse_args()

    wanted = {str(x) for x in args.locations}
    reader = HTTPRangeReader(args.url, args.size)
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(reader) as archive:
        infos = list(archive.infolist())
        archive_members = len(infos)
        start_dir = archive.start_dir

    ordered = sorted((info for info in infos if not info.is_dir()), key=lambda x: x.header_offset)
    next_offset = {
        info.header_offset: (
            ordered[index + 1].header_offset if index + 1 < len(ordered) else start_dir
        )
        for index, info in enumerate(ordered)
    }

    selected: list[tuple[zipfile.ZipInfo, str, Path, int]] = []
    for info in ordered:
        if not info.filename.lower().endswith(".jpg"):
            continue
        parts = safe_name(info.filename).parts
        matched = next((part for part in parts[:-1] if part in wanted), None)
        if matched is None:
            continue
        target = args.output / matched / Path(info.filename).name
        selected.append((info, matched, target, next_offset[info.header_offset] - 1))

    completed: list[dict[str, object]] = []
    pending: list[tuple[zipfile.ZipInfo, str, Path, int]] = []
    for info, matched, target, member_end in selected:
        if target.exists() and target.stat().st_size == info.file_size:
            payload = target.read_bytes()
            verify_payload(info, payload)
            completed.append(
                {
                    "location": matched,
                    "member": info.filename,
                    "target": str(target),
                    "bytes": info.file_size,
                    "crc": info.CRC,
                    "status": "already_complete_crc_verified",
                }
            )
        else:
            pending.append((info, matched, target, member_end))

    max_range = args.max_range_mib * 1024 * 1024
    max_gap = args.max_gap_mib * 1024 * 1024
    groups: list[list[tuple[zipfile.ZipInfo, str, Path, int]]] = []
    for item in pending:
        if not groups:
            groups.append([item])
            continue
        candidate_start = groups[-1][0][0].header_offset
        previous_end = groups[-1][-1][3]
        candidate_end = item[3]
        gap = item[0].header_offset - previous_end - 1
        if candidate_end - candidate_start + 1 <= max_range and gap <= max_gap:
            groups[-1].append(item)
        else:
            groups.append([item])

    print(
        json.dumps(
            {
                "selected": len(selected),
                "already_complete_crc_verified": len(completed),
                "pending": len(pending),
                "range_groups": len(groups),
            },
            indent=2,
        ),
        flush=True,
    )

    failed: list[dict[str, object]] = []
    for group_index, group in enumerate(groups, start=1):
        start = group[0][0].header_offset
        end = group[-1][3]
        try:
            block = get_range(args.url, start, end)
            for info, matched, target, _member_end in group:
                payload = decode_member(info, block, start)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + ".part")
                temporary.write_bytes(payload)
                temporary.replace(target)
                completed.append(
                    {
                        "location": matched,
                        "member": info.filename,
                        "target": str(target),
                        "bytes": info.file_size,
                        "crc": info.CRC,
                        "status": "downloaded_crc_verified",
                    }
                )
            print(
                f"range {group_index}/{len(groups)} files={len(group)} "
                f"bytes={end - start + 1}",
                flush=True,
            )
        except Exception as error:
            for info, matched, target, _member_end in group:
                failed.append(
                    {
                        "location": matched,
                        "member": info.filename,
                        "target": str(target),
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
            print(
                f"failed range {group_index}/{len(groups)} files={len(group)} error={error}",
                flush=True,
            )
        time.sleep(args.delay_s)

    completed.sort(key=lambda item: (str(item["location"]), str(item["member"])))
    payload = {
        "url": args.url,
        "remote_size": args.size,
        "requested_locations": sorted(wanted),
        "archive_members": archive_members,
        "selected_files": len(selected),
        "extracted_files": len(completed),
        "extracted_bytes": sum(int(item["bytes"]) for item in completed),
        "failed_files": len(failed),
        "failures": failed,
        "files": completed,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key not in {"files", "failures"}},
            indent=2,
        ),
        flush=True,
    )
    if failed:
        raise RuntimeError(f"{len(failed)} files failed")
    if len(completed) != len(selected):
        raise RuntimeError("completion count mismatch")


if __name__ == "__main__":
    main()
