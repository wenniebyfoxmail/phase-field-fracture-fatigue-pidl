#!/usr/bin/env python3
"""Create the FEM inverse-alpha_T grid-search manifest.

This does not run GRIPHFiTH.  It writes a small CSV/JSON manifest that the FEM
producer can use to run the fair baseline:

    alpha_T guess -> FEM forward -> compare reverseBC observations -> loss

The point is to keep the FEM inverse route explicit: FEM can solve the inverse
problem, but each alpha_T candidate requires a new forward simulation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_GRID = (0.25, 0.35, 0.50, 0.70, 1.00)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--umax", type=float, default=0.12)
    p.add_argument("--grid", type=float, nargs="*", default=list(DEFAULT_GRID))
    p.add_argument("--out-dir", default="inverse_alphaT_fem_grid",
                   help="Output directory under SENS_tensile unless absolute.")
    p.add_argument("--fem-root",
                   default="/Users/wenxiaofang/phase-field-fracture-with-pidl/GRIPHFiTH")
    p.add_argument("--input-template",
                   default="Scripts/fatigue_fracture/INPUT_SENT_PIDL_12.m")
    p.add_argument("--setting", default="standardFEM")
    args = p.parse_args()

    here = Path(__file__).resolve().parent
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = here / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, alpha_t in enumerate(args.grid, start=1):
        tag = f"u{int(round(args.umax * 100)):02d}_{args.setting}_aT{alpha_t:g}"
        rows.append({
            "case_id": idx,
            "tag": tag,
            "umax": args.umax,
            "alpha_T": alpha_t,
            "setting": args.setting,
            "fem_root": args.fem_root,
            "input_template": args.input_template,
            "expected_observations": "N_f,a(N),reaction_Fy,d_elem,alpha_bar_elem,f_alpha_elem",
            "notes": "copy reverseBC INPUT, set alpha_T, run full FEM forward, export same cycle fields",
        })

    csv_path = out_dir / "fem_inverse_alphaT_grid.csv"
    json_path = out_dir / "fem_inverse_alphaT_grid.json"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"Wrote {len(rows)} FEM inverse candidates")
    print(f"  CSV : {csv_path}")
    print(f"  JSON: {json_path}")
    print("Producer action: run one FEM forward per alpha_T candidate; no NN outer loop is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
