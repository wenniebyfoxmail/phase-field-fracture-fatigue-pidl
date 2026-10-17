#!/usr/bin/env python3
"""Render current page-level audits for every failed MnROAD reconciliation date."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


RAW_COLOUR = (0, 114, 178, 255)
CANONICAL_COLOUR = (230, 159, 0, 190)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def landscape_point(
    point: list[float], source_width: int, source_height: int, rotation: int,
) -> tuple[float, float]:
    if rotation == 90:
        return source_height - point[1], point[0]
    return point[1], source_width - point[0]


def target_features(record: dict) -> list[dict]:
    return [
        feature for feature in record["features"]
        if feature["properties"].get("lane") == "Driving"
        and feature["properties"].get("distress_class") == "NWP"
    ]


def render_summary(reconciliation: list[dict], output: Path) -> None:
    dates = [row["survey_date"] for row in reconciliation]
    excel = np.array([row["excel_nwp_ft"] for row in reconciliation], dtype=float)
    canonical = np.array([row["canonical_axial_ft"] for row in reconciliation], dtype=float)
    differences = canonical - excel
    tolerances = np.array([row["tolerance_ft"] for row in reconciliation], dtype=float)
    passed = np.array([row["passes"] for row in reconciliation], dtype=bool)
    positions = np.arange(len(dates))

    plt.rcParams.update({"font.family": "Arial", "font.size": 9})
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10.5, 6.8), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.08},
    )
    width = 0.36
    top.bar(positions - width / 2, excel, width, color="#0072B2", label="Excel Driving-lane NWP")
    top.bar(positions + width / 2, canonical, width, color="#E69F00", label="Canonical map occupancy")
    top.set_ylabel("Longitudinal cracking length (ft)")
    top.grid(axis="y", color="#D1D5DB", linewidth=0.7)
    top.set_axisbelow(True)
    top.legend(frameon=False, loc="upper left")
    top.set_title("MnROAD Cell 22: latest locked annotation reconciliation", loc="left", weight="bold", fontsize=13)

    colors = np.where(passed, "#009E73", "#D55E00")
    bottom.axhline(0, color="#4B5563", linewidth=0.9)
    bottom.vlines(
        positions, -tolerances, tolerances, color="#9CA3AF", alpha=0.25,
        linewidth=10, label="Allowed tolerance",
    )
    bottom.scatter(positions, differences, c=colors, s=42, zorder=3)
    for x, value, ok in zip(positions, differences, passed):
        bottom.annotate(
            f"{value:+.1f}", (x, value), xytext=(0, 7 if value >= 0 else -12),
            textcoords="offset points", ha="center", va="center",
            fontsize=8, color="#047857" if ok else "#9A3412",
        )
    bottom.set_ylabel("Map - Excel (ft)")
    bottom.set_xticks(positions, dates, rotation=28, ha="right")
    bottom.grid(axis="y", color="#E5E7EB", linewidth=0.7)
    bottom.set_axisbelow(True)
    bottom.legend(frameon=False, loc="lower left")
    for axis in (top, bottom):
        axis.spines[["top", "right"]].set_visible(False)
    fig.text(
        0.01, 0.01,
        "Scope: SECTION_ID 22-D-2016, LANE Driving, LONG_NWP_L_L/M/H. "
        "A failed date indicates aggregate disagreement, not a proven missing crack on a specific page.",
        fontsize=8, color="#4B5563",
    )
    fig.subplots_adjust(left=0.09, right=0.99, top=0.93, bottom=0.19, hspace=0.08)
    fig.savefig(output / "mnroad_reconciliation_summary.png", dpi=220, bbox_inches="tight")
    fig.savefig(output / "mnroad_reconciliation_summary.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--analysis-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--annotator", type=Path,
        default=Path(__file__).with_name("mnroad_single_owner_crack_annotator_server.py"),
    )
    parser.add_argument(
        "--candidate-builder", type=Path,
        default=Path(__file__).with_name("mnroad_build_phase2_candidates.py"),
    )
    args = parser.parse_args()
    packet = args.packet.resolve()
    analysis_dir = (args.analysis_dir or (packet / "phase2_work")).resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    annotator = load_module("mnroad_annotator", args.annotator.resolve())
    helper = load_module("mnroad_candidate_helper", args.candidate_builder.resolve())
    report = json.loads((analysis_dir / "phase2_finalization_report.json").read_text())
    reconciliation = report["reconciliation"]
    failed_rows = [row for row in reconciliation if not row["passes"]]
    if not failed_rows:
        raise RuntimeError("latest finalization report contains no failed dates")

    private = json.loads((packet / "private_repeat_key.json").read_text())["tasks"]
    canonical_payload = json.loads((analysis_dir / "canonical_observation_state.json").read_text())
    canonical_by_task: dict[str, list[dict]] = {}
    for row in canonical_payload["records"]:
        canonical_by_task.setdefault(row["task_id"], []).append(row)

    audit_rows: list[dict] = []
    summaries: dict[str, dict] = {}
    for reconciliation_row in failed_rows:
        date = reconciliation_row["survey_date"]
        excel_total = reconciliation_row["excel_nwp_ft"]
        tasks = sorted(
            (row for row in private.values() if row["survey_date"] == date and not row["is_repeat"]),
            key=lambda row: row["page"],
        )
        canonical_total = 0.0
        canvas = Image.new("RGB", (1600, 1960), "white")
        draw = ImageDraw.Draw(canvas)
        title_font, subtitle_font = font(31, True), font(20)
        panel_title_font, note_font, tiny_font = font(17, True), font(15), font(13)

        draw.text((70, 35), f"MnROAD Cell 22 page audit — {date}", fill="#111827", font=title_font)
        draw.text(
            (70, 82),
            "Blue = locked owner centreline; orange = canonical axial union; all panels use 0 ft → 50 ft left-to-right.",
            fill="#374151", font=subtitle_font,
        )
        draw.line((70, 123, 1530, 123), fill="#D1D5DB", width=2)

        origin_px, pixels_per_foot = helper.X_CALIBRATION[date]
        rotation = annotator.landscape_rotation_degrees(date)
        for index, task in enumerate(tasks):
            task_id = task["task_id"]
            record = json.loads((packet / "records" / f"{task_id}.geojson").read_text())
            raw = target_features(record)
            canonical = sorted(canonical_by_task.get(task_id, []), key=lambda row: row["canonical_id"])
            page_length = sum(row["canonical_axial_length_ft"] for row in canonical)
            canonical_total += page_length

            source = Image.open(packet / "images" / task["image"]).convert("RGB")
            source_width, source_height = source.size
            transpose = Image.Transpose.ROTATE_270 if rotation == 90 else Image.Transpose.ROTATE_90
            displayed = source.transpose(transpose).convert("RGBA")
            overlay = Image.new("RGBA", displayed.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            for component in canonical:
                y = component["lateral_mean_px"]
                for left_ft, right_ft in component["axial_intervals_ft"]:
                    left_px = origin_px + pixels_per_foot * left_ft
                    right_px = origin_px + pixels_per_foot * right_ft
                    overlay_draw.line([(left_px, y), (right_px, y)], fill=CANONICAL_COLOUR, width=11)
                intervals = component["axial_intervals_ft"]
                if intervals:
                    midpoint = sum(intervals[0]) / 2
                    x = origin_px + pixels_per_foot * midpoint
                    overlay_draw.text(
                        (x, y - 26), component["canonical_id"].split("-")[-1],
                        fill=(146, 64, 14, 255), font=tiny_font,
                    )
            for feature in raw:
                points = [
                    landscape_point(point, source_width, source_height, rotation)
                    for point in feature["geometry"]["coordinates"]
                ]
                overlay_draw.line(points, fill=RAW_COLOUR, width=4, joint="curve")

            merged = Image.alpha_composite(displayed, overlay)
            crop = merged.crop((45, 345, 1275, 655)).convert("RGB")
            panel = crop.resize((700, 176), Image.Resampling.LANCZOS)
            col, row = index % 2, index // 2
            x0, y0 = 70 + col * 760, 155 + row * 337
            title = (
                f"{task_id} | station {task['page_start_ft']}–{task['page_end_ft']} ft | "
                f"raw {len(raw)} | canonical {page_length:.1f} ft"
            )
            draw.text((x0, y0), title, fill="#111827", font=panel_title_font)
            canvas.paste(panel, (x0, y0 + 31))
            draw.rectangle((x0, y0 + 31, x0 + 700, y0 + 207), outline="#6B7280", width=2)
            if raw:
                component_text = ", ".join(
                    f"{row['canonical_id'].split('-')[-1]}={row['canonical_axial_length_ft']:.1f}ft"
                    for row in canonical
                )
                if len(component_text) > 100:
                    component_text = component_text[:97] + "..."
                draw.text((x0, y0 + 219), component_text, fill="#4B5563", font=tiny_font)
                zero_components = [row for row in canonical if row["canonical_axial_length_ft"] == 0]
                if zero_components:
                    draw.text(
                        (x0, y0 + 244),
                        f"REVIEW: {len(zero_components)} segment(s) lie outside the calibrated 0–50 ft bound and contribute 0.0 ft.",
                        fill="#991B1B", font=tiny_font,
                    )
            else:
                draw.text((x0, y0 + 219), "No Driving-lane NWP annotation on this page.", fill="#6B7280", font=note_font)

            audit_rows.append({
                "survey_date": date,
                "task_id": task_id,
                "station_start_ft": task["page_start_ft"],
                "station_end_ft": task["page_end_ft"],
                "raw_target_segment_count": len(raw),
                "canonical_component_count": len(canonical),
                "canonical_axial_length_ft": page_length,
            })

        difference = canonical_total - excel_total
        footer_y = 1850
        draw.line((70, footer_y - 18, 1530, footer_y - 18), fill="#D1D5DB", width=2)
        draw.text(
            (70, footer_y),
            f"Excel date total: {excel_total:.1f} ft   |   canonical map occupancy: {canonical_total:.1f} ft   |   difference: {difference:+.1f} ft   |   FAIL",
            fill="#991B1B", font=font(20, True),
        )
        draw.text(
            (70, footer_y + 42),
            "Excel provides only a date-level total; it cannot identify a missing page or prove that a visible mark is NWP.",
            fill="#7C2D12", font=note_font,
        )
        figure_path = output / f"mnroad_{date}_failed_total_page_audit.png"
        canvas.save(figure_path, dpi=(200, 200))
        summaries[date] = {
            "excel_total_ft": excel_total,
            "canonical_total_ft": canonical_total,
            "difference_ft": difference,
            "tolerance_ft": reconciliation_row["tolerance_ft"],
            "figure": figure_path.name,
        }

    csv_path = output / "page_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    render_summary(reconciliation, output)

    figure_sections = []
    for date, summary in summaries.items():
        figure_sections.extend([
            f"### {summary['figure']}",
            "",
            f"- Workbook: {summary['excel_total_ft']:.1f} ft.",
            f"- Canonical: {summary['canonical_total_ft']:.1f} ft.",
            f"- Difference: {summary['difference_ft']:+.1f} ft; tolerance ±{summary['tolerance_ft']:.1f} ft.",
            "",
        ])
    failed_dates = ", ".join(summaries)
    readme = output / "README_analysis.md"
    readme.write_text(
        "# Analysis: MnROAD latest locked reconciliation and page audits\n\n"
        "## Scientific question\n\n"
        "Which dates still disagree with the Driving-lane NWP workbook totals after rebuilding from the latest locked annotations, and on which pages do the mapped annotations occur?\n\n"
        "## Evidence identity\n\n"
        "- Section/lane: 22-D-2016, Driving.\n"
        f"- Failed dates in the current finalization report: {failed_dates}.\n"
        "- Map sources: ten primary InfoPave distress-map pages per date; concealed repeats are excluded.\n"
        "- Raw overlays: latest locked owner annotations in `records/M*.geojson`.\n"
        f"- Processed overlays: `{analysis_dir / 'canonical_observation_state.json'}`.\n"
        "- Workbook comparator: date-level `LONG_NWP_L_L + LONG_NWP_L_M + LONG_NWP_L_H` for `LANE=Driving`; it has no page-level allocation.\n"
        "- Canonical method: same-page/date axial interval union using the frozen tolerances; thresholds were not tuned to Excel.\n\n"
        "## Reading order\n\n"
        "1. Read `mnroad_reconciliation_summary.png` for all seven date totals and residuals.\n"
        "2. Open each failed-date page audit and read the page title, raw count, and canonical length.\n"
        "3. Compare blue locked centrelines with orange canonical intervals.\n"
        "4. Treat the footer only as an aggregate discrepancy; do not assign it to a page without independent evidence.\n\n"
        "## Figure guide\n\n"
        "### mnroad_reconciliation_summary.png\n\n"
        "The upper panel compares workbook and canonical totals. The lower panel shows map minus Excel; green points pass and orange points fail the frozen tolerance.\n\n"
        + "\n".join(figure_sections)
        + "## Gate result\n\n"
        f"- Dates passed: {report['passed_dates']}/{report['eligible_dates']}.\n"
        f"- Dates failed: {len(failed_rows)} ({failed_dates}).\n"
        f"- Qualification: `{report['qualification']}`.\n\n"
        "## Allowed conclusion\n\n"
        "The figures locate every currently counted map annotation and reproduce the latest locked date totals.\n\n"
        "## Blocked conclusion\n\n"
        "The figures do not prove that an uncounted visible mark is NWP, that the owner omitted a crack, that Excel is wrong, or which page explains a date-level deficit. Different survey and map-drawing semantics remain possible.\n\n"
        "## Storyline impact and next action\n\n"
        "The current annotation is complete by owner review, but scalar reconciliation remains unresolved. Further correction requires new source evidence such as MnROAD page-level distress records or survey counting rules, not geometry added solely to match Excel.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "summaries": summaries,
        "summary_figure": str(output / "mnroad_reconciliation_summary.png"),
        "csv": str(csv_path),
        "readme": str(readme),
    }, indent=2))


if __name__ == "__main__":
    main()
