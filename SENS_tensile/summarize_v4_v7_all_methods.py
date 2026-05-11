#!/usr/bin/env python3
"""summarize_v4_v7_all_methods.py — collate V4 (symmetry) + V7 (BC residual) across all PIDL methods.

Reads `validation_report.json` from every archive under SENS_tensile/, augments with
hand-curated entries for methods whose validation lives elsewhere (Windows outbox,
Taobo remote run, Phase C smoke), and writes:
  - a CSV table (one row per method)
  - a console-pretty summary

Methods covered (12 + recent strac/A1 family):
  baseline, Williams, Fourier, Enriched-v1, spAlphaT, Oracle, Sym y² (hard),
  Sym soft (penalty), A1 mirror α, Strac alone, A1+Strac combo
"""
from __future__ import annotations
import json
import re
import csv
from pathlib import Path

HERE = Path(__file__).parent
OUT_CSV = HERE / "validation_v4_v7_all_methods.csv"


def label(arc: str) -> str:
    if "spAlphaT" in arc:
        m = re.search(r"b[0-9.]+", arc)
        return f"spAlphaT-{m.group()}"
    if "williams" in arc:
        return "Williams"
    if "fourier" in arc:
        return "Fourier"
    if "enriched_ansatz" in arc:
        m = re.search(r"v\d", arc)
        return f"Enriched-{m.group()}" if m else "Enriched"
    if "oracle_zone" in arc:
        m = re.search(r"Umax([\d.]+)", arc)
        return f"Oracle u={m.group(1)}"
    if "psiHack" in arc:
        return "E2 hack"
    if "narrow" in arc:
        return "Golahmar+narrow"
    if "alpha1_corridor" in arc:
        return "α-1 mesh"
    if "symY2" in arc:
        return "Sym y² (hard)"
    if "symSoft" in arc and "strac" in arc:
        return "A1+Strac combo"
    if "symSoft" in arc:
        return "Sym soft (penalty)"
    if "mirror_alpha" in arc:
        return "A1 mirror α"
    if "fatigue_off" in arc:
        return "MONO (no fatigue)"
    m = re.search(r"Umax([\d.]+)", arc)
    u = m.group(1) if m else "?"
    if "_mono" in arc:
        return f"baseline mono u={u}"
    return f"baseline u={u}"


def parse_archive(p: Path):
    arc = p.parent.parent.name
    try:
        d = json.load(open(p))
    except Exception:
        return None
    v4 = next((t for t in d if t.get("test") == "V4_symmetry"), None)
    v7 = (next((t for t in d if t.get("test") == "V7_bc_residual_side"), None)
          or next((t for t in d if t.get("test") == "V7_bc_residual"), None))
    return {
        "method": label(arc),
        "archive": arc,
        "V4_status": (v4 or {}).get("status", "—"),
        "V4_rms_alpha": (v4 or {}).get("rms_alpha_skew"),
        "V4_max_alpha": (v4 or {}).get("max_alpha_skew"),
        "V7_status": (v7 or {}).get("status", "—"),
        "V7_rel_sxx": (v7 or {}).get("rel_residual_sxx"),
        "V7_rel_sxy": (v7 or {}).get("rel_residual_sxy"),
        "V7_sxx_L": (v7 or {}).get("max_sxx_left_abs"),
        "V7_sxx_R": (v7 or {}).get("max_sxx_right_abs"),
    }


def main():
    rows = []
    for p in sorted((HERE).glob("hl_*/best_models/validation_report.json")):
        r = parse_archive(p)
        if r and (r["V4_rms_alpha"] is not None or r["V7_rel_sxx"] is not None):
            rows.append(r)

    # Dedupe by label (keep first occurrence — most relevant)
    seen = {}
    for r in rows:
        if r["method"] not in seen:
            seen[r["method"]] = r
    rows = list(seen.values())

    # Hand-curated entries for methods whose validation lives outside Mac
    # (Windows outbox, Taobo remote run, Phase C smoke).
    # Numbers come from: docs/handovers/windows_pidl_outbox.md commit 7387eec,
    # Taobo validate_strac_seed1.json (run 2026-05-10), and earlier handover notes.
    extra = [
        {
            "method": "Sym soft (penalty)",
            "archive": "Queue E seed1 N=300 u=0.12 (Taobo)",
            "V4_status": "FAIL", "V4_rms_alpha": 0.02188, "V4_max_alpha": 0.14825,
            "V7_status": "WARN", "V7_rel_sxx": 0.27605, "V7_rel_sxy": 0.18308,
            "V7_sxx_L": 8353.04, "V7_sxx_R": 21833.20,
        },
        {
            "method": "A1 mirror α (smoke)",
            "archive": "Windows Phase B (Req 6) seeds 1/2/3 N=5",
            # cycle 4 sxx_L_max ~280 (raw), σ_yy_bulk_max ~0.4 → rel ~70000%
            "V4_status": "PASS (mirror=exact)", "V4_rms_alpha": 0.0,
            "V4_max_alpha": 0.0,
            "V7_status": "FAIL", "V7_rel_sxx": 700.0, "V7_rel_sxy": 1.5,
            "V7_sxx_L": 280.0, "V7_sxx_R": 0.10,
        },
        {
            "method": "Strac alone (this run)",
            "archive": "Taobo seed1 N=300 u=0.12 cycle 87 (run 2026-05-10)",
            "V4_status": "FAIL", "V4_rms_alpha": 0.02092, "V4_max_alpha": 0.12659,
            "V7_status": "FAIL", "V7_rel_sxx": 1.380, "V7_rel_sxy": 1.197,
            "V7_sxx_L": 80998.4, "V7_sxx_R": 18371.7,  # NOTE: different stress unit normalization
        },
        {
            "method": "A1+Strac combo (smoke)",
            "archive": "Windows Phase C (Req 6) seed1 N=5",
            "V4_status": "PASS (mirror=exact)", "V4_rms_alpha": 0.0,
            "V4_max_alpha": 0.0,
            "V7_status": "PASS", "V7_rel_sxx": 0.158, "V7_rel_sxy": 0.124,
            "V7_sxx_L": 0.010, "V7_sxx_R": 0.068,
        },
    ]

    # Add extras at end (overriding any local stale dupes)
    for e in extra:
        for i, r in enumerate(rows):
            if r["method"] == e["method"]:
                rows[i] = e
                break
        else:
            rows.append(e)

    # Sort by V4 RMS (best to worst)
    def rms_key(r):
        return r["V4_rms_alpha"] if r["V4_rms_alpha"] is not None else 99.0
    rows.sort(key=rms_key)

    # Write CSV
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote: {OUT_CSV}")

    # Pretty print
    print()
    print(f"{'method':<26} {'V4 RMS':>8} {'V4 max':>8} {'V7 sxx':>8} {'V7 sxy':>8} {'sxx_L':>10} {'sxx_R':>10}")
    print("-" * 92)
    for r in rows:
        rms = f"{r['V4_rms_alpha']:8.4f}" if r['V4_rms_alpha'] is not None else "    -   "
        mxa = f"{r['V4_max_alpha']:8.4f}" if r['V4_max_alpha'] is not None else "    -   "
        rxx = f"{r['V7_rel_sxx']*100:7.1f}%" if r['V7_rel_sxx'] is not None else "    -   "
        rxy = f"{r['V7_rel_sxy']*100:7.1f}%" if r['V7_rel_sxy'] is not None else "    -   "
        sL = f"{r['V7_sxx_L']:10.2f}" if r['V7_sxx_L'] is not None else "     -    "
        sR = f"{r['V7_sxx_R']:10.2f}" if r['V7_sxx_R'] is not None else "     -    "
        print(f"{r['method']:<26} {rms} {mxa} {rxx} {rxy} {sL} {sR}")


if __name__ == "__main__":
    main()
