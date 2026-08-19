from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.toy_road_t3_mechanism_20260819.evidence import (
    EXPECTED_CASE,
    EXPECTED_MANIFEST,
    sha256_file,
)


@dataclass(frozen=True)
class FileRecord:
    source: Path
    relative_path: str
    size: int
    sha256: str


def _is_link_or_reparse(path: Path) -> bool:
    info = os.lstat(path)
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def validate_source_tree(root: Path) -> list[FileRecord]:
    root = Path(root)
    if not root.is_dir() or _is_link_or_reparse(root):
        raise ValueError(f"source root is not a regular directory: {root}")
    records: list[FileRecord] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = Path(entry.path)
            if _is_link_or_reparse(path):
                raise ValueError(f"source contains link/reparse point: {path}")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                relative = path.relative_to(root).as_posix()
                records.append(
                    FileRecord(
                        source=path,
                        relative_path=relative,
                        size=path.stat().st_size,
                        sha256=sha256_file(path),
                    )
                )
            else:
                raise ValueError(f"source contains non-regular entry: {path}")
    return sorted(records, key=lambda record: record.relative_path)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def mirror_verified(
    source_output: Path,
    evidence_files: Iterable[Path],
    destination: Path,
    *,
    copier: Callable[[Path, Path], object] = shutil.copyfile,
) -> dict[str, object]:
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    output_records = validate_source_tree(Path(source_output))
    evidence_records: list[FileRecord] = []
    seen_names: set[str] = set()
    for source in sorted((Path(path) for path in evidence_files), key=lambda path: path.name):
        if not source.is_file() or _is_link_or_reparse(source):
            raise ValueError(f"external evidence is not a regular file: {source}")
        if source.name in seen_names:
            raise ValueError(f"duplicate external evidence name: {source.name}")
        seen_names.add(source.name)
        evidence_records.append(
            FileRecord(source, source.name, source.stat().st_size, sha256_file(source))
        )

    payload = [
        (record, Path("output") / Path(record.relative_path)) for record in output_records
    ] + [
        (record, Path("external_evidence") / record.relative_path)
        for record in evidence_records
    ]
    destination.mkdir(parents=True, exist_ok=False)
    verified: list[dict[str, object]] = []
    for record, relative in payload:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copier(record.source, target)
        if not target.is_file() or target.stat().st_size != record.size:
            raise ValueError(f"copied payload size mismatch: {relative.as_posix()}")
        if sha256_file(target) != record.sha256:
            raise ValueError(f"copied payload SHA-256 mismatch: {relative.as_posix()}")
        verified.append(
            {
                "path": relative.as_posix(),
                "size": record.size,
                "sha256": record.sha256,
            }
        )

    locator = {
        "schema_version": "toy_road_t3_onedrive_package_v1",
        "status": "LOCAL_MIRROR_VERIFIED",
        "case_id": EXPECTED_CASE,
        "terminal_manifest_sha256": EXPECTED_MANIFEST,
        "payload_file_count": len(verified),
        "payload_total_bytes": sum(int(record["size"]) for record in verified),
        "upload_state": "LOCAL_MIRROR_VERIFIED",
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    (destination / "ONEDRIVE_PACKAGE.json").write_bytes(_canonical_bytes(locator) + b"\n")
    (destination / "SHA256SUMS.txt").write_text(
        "".join(f"{record['sha256']}  {record['path']}\n" for record in verified),
        encoding="ascii",
        newline="\n",
    )
    return locator


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and verify an immutable T3 OneDrive mirror.")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--external-evidence", required=True, type=Path, nargs="+")
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    result = mirror_verified(args.output_root, args.external_evidence, args.destination)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
