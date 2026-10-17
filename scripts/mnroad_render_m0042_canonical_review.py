#!/usr/bin/env python3
"""Render a human-review figure for the M0042 redraw-union result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ORIGIN_PX = 99.0
PIXELS_PER_FOOT = 20.1


def landscape_point(point: list[float], source_width: int) -> tuple[float, float]:
    return point[1], source_width - point[0]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = args.packet.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    record = json.loads((packet / "records" / "M0042.geojson").read_text())
    canonical_payload = json.loads(
        (packet / "phase2_work" / "canonical_observation_state.json").read_text()
    )
    components = sorted(
        (row for row in canonical_payload["records"] if row["task_id"] == "M0042"),
        key=lambda row: row["canonical_id"],
    )
    if len(components) != 2:
        raise RuntimeError(f"expected two M0042 components, got {len(components)}")

    source = Image.open(packet / "images" / "2019-03-22_p02.jpg").convert("RGB")
    source_width, _ = source.size
    displayed = source.transpose(Image.Transpose.ROTATE_90)
    colours = ["#0072B2", "#CC79A7"]
    segment_to_component = {
        segment_id: index
        for index, component in enumerate(components)
        for segment_id in component["source_segment_ids"]
    }

    raw_overlay = displayed.copy()
    raw_draw = ImageDraw.Draw(raw_overlay)
    for feature in record["features"]:
        segment_id = feature["properties"]["segment_id"]
        component_index = segment_to_component[segment_id]
        points = [landscape_point(point, source_width) for point in feature["geometry"]["coordinates"]]
        raw_draw.line(points, fill=colours[component_index], width=4, joint="curve")

    canonical_overlay = displayed.copy()
    canonical_draw = ImageDraw.Draw(canonical_overlay)
    for index, component in enumerate(components):
        y = component["lateral_mean_px"]
        for left_ft, right_ft in component["axial_intervals_ft"]:
            left_px = ORIGIN_PX + PIXELS_PER_FOOT * left_ft
            right_px = ORIGIN_PX + PIXELS_PER_FOOT * right_ft
            canonical_draw.line([(left_px, y), (right_px, y)], fill=colours[index], width=10)

    crop_box = (55, 390, 1165, 650)
    panel_width, panel_height = 1332, 312
    raw_panel = raw_overlay.crop(crop_box).resize((panel_width, panel_height), Image.Resampling.LANCZOS)
    canonical_panel = canonical_overlay.crop(crop_box).resize((panel_width, panel_height), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (1480, 1010), "white")
    draw = ImageDraw.Draw(canvas)
    title_font, section_font = font(27, True), font(21, True)
    label_font, small_font = font(17), font(15)
    total = sum(row["canonical_axial_length_ft"] for row in components)

    draw.text((74, 30), "M0042 canonical redraw review", fill="#111827", font=title_font)
    draw.text(
        (74, 68),
        f"2019-03-22 · station 50–100 ft · 19 raw segments → 2 candidate components · total {total:.1f} ft",
        fill="#374151", font=label_font,
    )
    draw.text((74, 118), "A. Original owner annotations — all 19 segments preserved", fill="#111827", font=section_font)
    canvas.paste(raw_panel, (74, 154))
    draw.rectangle((74, 154, 74 + panel_width, 154 + panel_height), outline="#6B7280", width=2)
    for index, component in enumerate(components):
        x = 76 + index * 650
        draw.line((x, 488, x + 46, 488), fill=colours[index], width=6)
        draw.text(
            (x + 58, 478),
            f"{component['canonical_id']} sources: {component['source_segment_count']} segments",
            fill="#111827", font=small_font,
        )

    draw.text((74, 530), "B. Candidate canonical axial occupancy — fixed-rule union", fill="#111827", font=section_font)
    canvas.paste(canonical_panel, (74, 566))
    draw.rectangle((74, 566, 74 + panel_width, 566 + panel_height), outline="#6B7280", width=2)
    for index, component in enumerate(components):
        x = 76 + index * 650
        draw.line((x, 898, x + 46, 898), fill=colours[index], width=8)
        draw.text(
            (x + 58, 887),
            f"{component['canonical_id']}: {component['canonical_axial_length_ft']:.1f} ft",
            fill="#111827", font=label_font,
        )
    draw.text(
        (74, 944),
        "Review aid only: 6 px lateral / 0.5 ft longitudinal-gap rule. This grouping does not prove physical crack identity.",
        fill="#7C2D12", font=small_font,
    )
    figure_path = output / "m0042_canonical_review.png"
    canvas.save(figure_path, dpi=(200, 200))

    readme = output / "README_analysis.md"
    readme.write_text(
        "# Analysis: M0042 canonical redraw review\n\n"
        "## Scientific question\n\n"
        "Do the 19 owner-drawn M0042 centreline segments support the proposed fixed-rule collapse into two same-date axial components?\n\n"
        "## Evidence identity\n\n"
        "- Observation: M0042, 2019-03-22, station 50-100 ft.\n"
        "- Source map: `images/2019-03-22_p02.jpg`.\n"
        "- Raw annotation: `records/M0042.geojson` (19 segments; preserved).\n"
        "- Candidate state: `phase2_work/canonical_observation_state.json`.\n"
        "- Analysis script: `upload code/scripts/mnroad_render_m0042_canonical_review.py`.\n"
        "- Rule: same-page/date interval union; lateral tolerance 6 px; longitudinal gap 0.5 ft.\n\n"
        "## Reading order\n\n"
        "1. Inspect panel A for the original 19 segment positions and proposed component colours.\n"
        "2. Inspect panel B for the corresponding axial occupancy intervals.\n"
        "3. Check especially the boundary near 32 ft, where the two components are separated.\n\n"
        "## Figure guide\n\n"
        "### m0042_canonical_review.png\n\n"
        "- Panel A preserves every source segment and colours it by candidate component.\n"
        "- Panel B shows the union intervals, not a replacement hand-drawn crack.\n"
        f"- Candidate lengths: {components[0]['canonical_axial_length_ft']:.1f} ft and {components[1]['canonical_axial_length_ft']:.1f} ft; total {total:.1f} ft.\n\n"
        "## Cross-figure interpretation\n\n"
        "The proposed result removes same-locus redraw double counting while preserving small observed gaps. It does not erase or rewrite the raw annotation.\n\n"
        "## Gate result\n\n"
        "- Validity gate: pending owner visual review.\n"
        "- Verdict: candidate only; phase 2 is currently invalidated because M0061 has been reopened.\n\n"
        "## Allowed conclusion\n\n"
        "Under the stated fixed rule, the M0042 raw annotations form two candidate axial groups totalling 46.4 ft.\n\n"
        "## Blocked conclusion\n\n"
        "This figure cannot establish that the two groups are distinct physical cracks or that either persists across dates.\n\n"
        "## Storyline impact and next action\n\n"
        "The owner should accept or reject the grouping, especially the split near 32 ft, before the canonical state is reused.\n",
        encoding="utf-8",
    )
    print(figure_path)
    print(readme)


if __name__ == "__main__":
    main()
