#!/usr/bin/env python3
"""Acquire the official full-page LTPP distress-map PDFs as a source receipt.

This is deliberately not a registration implementation.  It fetches the
per-survey PDF advertised by the official InfoPave Manual Distress Survey
Viewer, records the API response and SHA-256 receipts, and rasterises one
*uncropped* source page per PDF for human source review.  It never extracts
controls, fits a transform, or reads crack annotations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path


API_URL = "https://infopave.fhwa.dot.gov/Media/GetDistressPDF"
DATES = (
    ("19910610", "06/10/1991"),
    ("19951024", "10/24/1995"),
    ("19970228", "02/28/1997"),
    ("19980407", "04/07/1998"),
    ("20010913", "09/13/2001"),
    ("20030514", "05/14/2003"),
    ("20071106", "11/06/2007"),
    ("20120417", "04/17/2012"),
)


@dataclass(frozen=True)
class PdfEntry:
    date_id: str
    survey_date: str
    distress_image_id: int
    image_file_name: str
    image_url: str
    bytes: int
    sha256: str


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_pdf_metadata(section_id: str, survey_date: str) -> list[dict[str, object]]:
    payload = json.dumps(
        {"LDW_SECTION_ID": section_id, "SURVEY_TYPE": "MDS", "SURVEY_DATE": survey_date}
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise ValueError(f"expected one PDF metadata row for {survey_date}, got {data!r}")
    item = data[0]
    if item.get("IMAGE_FILE_TYPE") != ".pdf" or not str(item.get("IMAGE_URL", "")).startswith("https://"):
        raise ValueError(f"InfoPave response is not a HTTPS PDF for {survey_date}: {item!r}")
    return data


def download_pdf(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "LTPP-source-receipt/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    if not destination.read_bytes().startswith(b"%PDF-"):
        raise ValueError(f"downloaded asset is not a PDF: {destination}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_uncropped_page(pdf: Path, visual_path: Path, page_number: int) -> None:
    prefix = visual_path.with_suffix("")
    command = [
        "pdftoppm",
        "-png",
        "-r",
        "160",
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        str(pdf),
        str(prefix),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    generated_paths = sorted(prefix.parent.glob(f"{prefix.name}-*.png"))
    if len(generated_paths) != 1:
        raise RuntimeError(
            f"pdftoppm must create exactly one rendered page for {pdf}; got {generated_paths}"
        )
    generated = generated_paths[0]
    generated.rename(visual_path)


def write_manifest(output_root: Path) -> None:
    lines = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        lines.append(f"{sha256_path(path)}  {path.relative_to(output_root)}")
    (output_root / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def acquire(output_root: Path, section_id: str, render_page: int) -> list[PdfEntry]:
    if output_root.exists():
        raise FileExistsError(f"output root must be new: {output_root}")
    (output_root / "pdfs").mkdir(parents=True)
    (output_root / "visuals").mkdir()
    responses: dict[str, list[dict[str, object]]] = {}
    entries: list[PdfEntry] = []

    for date_id, survey_date in DATES:
        response = get_pdf_metadata(section_id, survey_date)
        responses[date_id] = response
        metadata = response[0]
        destination = output_root / "pdfs" / f"{date_id}_{metadata['IMAGE_FILE_NAME']}"
        download_pdf(str(metadata["IMAGE_URL"]), destination)
        entry = PdfEntry(
            date_id=date_id,
            survey_date=survey_date,
            distress_image_id=int(metadata["DISTRESS_IMAGE_ID"]),
            image_file_name=str(metadata["IMAGE_FILE_NAME"]),
            image_url=str(metadata["IMAGE_URL"]),
            bytes=destination.stat().st_size,
            sha256=sha256_path(destination),
        )
        entries.append(entry)
        render_uncropped_page(
            destination,
            output_root / "visuals" / f"{date_id}_full_source_page_{render_page}.png",
            render_page,
        )

    write_json(output_root / "infopave_pdf_api_responses.json", responses)
    write_json(
        output_root / "source_receipt.json",
        {
            "status": "SOURCE_AVAILABILITY_ONLY__NO_REGISTRATION",
            "section_id": section_id,
            "api_url": API_URL,
            "survey_type": "MDS",
            "render_page": render_page,
            "rendering": "uncropped display-only source-page rasterisation at 160 dpi",
            "prohibited_operations": [
                "control-point extraction",
                "crop selection for registration",
                "transform fitting",
                "registration residual evaluation",
                "crack annotation use",
            ],
            "pdfs": [asdict(entry) for entry in entries],
            "script_sha256": sha256_path(Path(__file__).resolve()),
        },
    )
    write_manifest(output_root)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--section-id", default="2056")
    parser.add_argument("--render-page", type=int, default=4)
    args = parser.parse_args()
    entries = acquire(args.output_root, args.section_id, args.render_page)
    print(json.dumps({"output_root": str(args.output_root), "pdf_count": len(entries)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
