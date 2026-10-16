"""Read MD01 step/image identifiers only; never decode response-column values.

No network, image access, workbook import, formula evaluation or workbook edits.
Run with the bundled Python runtime. Output is a metadata receipt, not a result.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXPECTED_HASH = "74720c570524a43dc6d87a689efc52435de6a99ec1b088a2ca4f45d7e26ebf91"
# Fixed, manually reviewed whitelist: no C:F responses or H:I other cameras.
WHITELIST = {
    "xl/worksheets/sheet1.xml": {"A", "B"},
    "xl/worksheets/sheet2.xml": {"A", "B", "G"},
}
HEADER_CELLS = {
    "xl/worksheets/sheet1.xml": {f"{col}1" for col in "ABCDEFGHI"},
    "xl/worksheets/sheet2.xml": {
        f"{col}{row}" for row in (3, 4) for col in "ABCDEFGHI"
    },
}


def selected_cells(archive, member, permitted):
    """Select cell references before inspecting their scalar content."""
    cells = {}
    for _, cell in ET.iterparse(archive.open(member), events=("end",)):
        if cell.tag != NS + "c":
            continue
        ref = cell.get("r")
        if permitted(ref):
            if cell.find(NS + "f") is not None:
                raise ValueError(f"Formula in authorized metadata cell: {ref}")
            cells[ref] = (cell.get("t"), cell.findtext(NS + "v"))
        cell.clear()
    return cells


def run(workbook, listing):
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    if digest != EXPECTED_HASH:
        raise ValueError("Source identity changed; review schema before extracting")
    with zipfile.ZipFile(workbook) as archive:
        headers = {
            member: selected_cells(archive, member, lambda ref, refs=refs: ref in refs)
            for member, refs in HEADER_CELLS.items()
        }
        metadata = {}
        for member, columns in WHITELIST.items():
            first_data_row = 2 if member.endswith("sheet1.xml") else 5
            metadata[member] = selected_cells(
                archive, member,
                lambda ref: int(re.search(r"\d+$", ref).group()) >= first_data_row
                and re.match(r"[A-Z]+", ref).group() in columns,
            )
        requested_strings = {
            int(value) for group in [*headers.values(), *metadata.values()]
            for kind, value in group.values() if kind == "s" and value is not None
        }
        strings = {}
        index = 0
        for _, item in ET.iterparse(archive.open("xl/sharedStrings.xml"), events=("end",)):
            if item.tag == NS + "si":
                if index in requested_strings:
                    strings[index] = "".join(t.text or "" for t in item.iter(NS + "t"))
                index += 1
                item.clear()

    def decode(cell):
        kind, value = cell
        return strings[int(value)] if kind == "s" and value is not None else value

    decoded_headers = {
        member: {ref: decode(cell) for ref, cell in cells.items()}
        for member, cells in headers.items()
    }
    h1 = decoded_headers["xl/worksheets/sheet1.xml"]
    if (h1.get("A1"), h1.get("B1")) != ("Sampling", "Loadstep"):
        raise ValueError("Whitelisted-column headings changed")
    h = decoded_headers["xl/worksheets/sheet2.xml"]
    if (h.get("A4"), h.get("B4"), h.get("G4")) != (
        "Sampling", "Step", "Fixed camera image - side A"
    ):
        raise ValueError("Whitelisted-column headings changed")
    rows = {}
    for ref, cell in metadata["xl/worksheets/sheet2.xml"].items():
        col, row = re.fullmatch(r"([A-Z]+)(\d+)", ref).groups()
        rows.setdefault(int(row), {})[col] = decode(cell)
    files = json.loads(listing.read_text())
    filenames = Counter(entry["filename"].upper() for entry in files)
    mapping = []
    for row, cells in sorted(rows.items()):
        if all(value is None for value in cells.values()):
            continue
        raw = cells.get("G")
        # Only a literal numeric image ID or complete basename can join.
        if raw is not None and re.fullmatch(r"\d+(?:\.0+)?", raw):
            name = f"IMG_{int(float(raw)):04d}.JPG"
        elif raw is not None and re.fullmatch(r"IMG_\d+\.JPG", raw.upper()):
            name = raw.upper()
        else:
            name = None
        mapping.append({
            "excel_row": row, "sampling": cells.get("A"),
            "step": cells.get("B"), "fixed_image_cell": f"G{row}",
            "fixed_image_id_raw": raw, "filename": name,
            "matches_in_fixed_folder": filenames.get(name, 0),
        })
    matched_names = [r["filename"] for r in mapping if r["matches_in_fixed_folder"] == 1]
    labtest_metadata = {}
    for ref, cell in metadata["xl/worksheets/sheet1.xml"].items():
        col, row = re.fullmatch(r"([A-Z]+)(\d+)", ref).groups()
        value = decode(cell)
        if value is not None:
            labtest_metadata.setdefault(int(row), {})[col] = value
    return {
        "source_sha256": digest,
        "scope": "Headers, Labtest 2 A/B, Data acquisition A/B/G only; no response values decoded",
        "headers": decoded_headers,
        "fixed_directory": {
            "file_count": len(files),
            "duplicate_filenames": [n for n, count in filenames.items() if count > 1],
            "files": [{"id": f["id"], "filename": f["filename"]} for f in files],
        },
        "mapping": mapping,
        "labtest_sampling_loadstep": [
            {"excel_row": row, "sampling": cells.get("A"), "loadstep": cells.get("B")}
            for row, cells in sorted(labtest_metadata.items())
        ],
        "join_summary": {
            "metadata_rows": len(mapping),
            "uniquely_matched_rows": len(matched_names),
            "unique_matched_filenames": len(set(matched_names)),
            "files_with_explicit_step": sum(
                r["step"] is not None and r["matches_in_fixed_folder"] == 1
                for r in mapping
            ),
            "image_rows_without_step": [
                r["excel_row"] for r in mapping
                if r["step"] is None and r["matches_in_fixed_folder"] == 1
            ],
            "step_rows_without_image": [
                r["excel_row"] for r in mapping
                if r["step"] is not None and r["fixed_image_id_raw"] is None
            ],
            "fixed_files_without_mapping": sorted(set(filenames) - set(matched_names)),
            "reused_image_names": [n for n, count in Counter(matched_names).items() if count > 1],
            "rows_per_step": dict(Counter(r["step"] for r in mapping)),
        },
        "not_read": ["Labtest 2 C:I data values", "Data acquisition C:F data values",
                     "Data acquisition H:I data values", "image contents", "embedded objects"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("listing", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    receipt = run(args.workbook, args.listing)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt["join_summary"], ensure_ascii=False, indent=2))
    print("first_metadata_rows", json.dumps(receipt["mapping"][:9], ensure_ascii=False))
