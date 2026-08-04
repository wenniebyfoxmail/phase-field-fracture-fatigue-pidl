#!/usr/bin/env python3
"""Fail when a research figure lacks a usable same-stem Markdown explanation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FIGURE_SUFFIXES = {".png", ".pdf", ".svg", ".jpg", ".jpeg"}
REQUIRED_PHRASES = ("how to read", "data provenance", "limitation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("figure_directory", type=Path)
    args = parser.parse_args()
    root = args.figure_directory.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a figure directory: {root}")

    figures = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in FIGURE_SUFFIXES
    )
    errors: list[str] = []
    checked_notes: set[Path] = set()
    for figure in figures:
        note = figure.with_suffix(".md")
        if not note.is_file():
            errors.append(f"missing sidecar: {figure} -> {note.name}")
            continue
        if note in checked_notes:
            continue
        checked_notes.add(note)
        text = note.read_text(encoding="utf-8").strip()
        lowered = text.lower()
        if len(text) < 400:
            errors.append(f"sidecar too short (<400 chars): {note}")
        for phrase in REQUIRED_PHRASES:
            if phrase not in lowered:
                errors.append(f"sidecar missing phrase '{phrase}': {note}")

    result = {
        "status": "pass" if not errors else "fail",
        "figure_directory": str(root),
        "figure_files": len(figures),
        "unique_sidecars": len(checked_notes),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
