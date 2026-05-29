#!/usr/bin/env python3
"""Build a tiered manifest for Taobo PIDL archives.

The goal is not to rank every old run against FEM directly.  It is to make the
alignment caveats explicit before a run enters a FEM/PIDL comparison table.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT = "/mnt/data2/drtao/projects"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "_analysis_fem_mechanism_20260528"
DEFAULT_DOC = Path(__file__).resolve().parent.parent / "docs" / "taobo_tiered_comparison_plan_2026-05-29.md"


REMOTE_SCRIPT = r"""
from pathlib import Path
import json, re
root = Path({root!r})
records = []
seen = set()
if root.exists():
    for ab in root.glob("**/best_models/alpha_bar_vs_cycle.npy"):
        archive = ab.parent.parent
        best = archive / "best_models"
        if str(archive) in seen:
            continue
        seen.add(str(archive))
        trained = sorted(best.glob("trained_1NN_*.pt"))
        checkpoints = sorted(best.glob("checkpoint_step_*.pt"))
        settings = archive / "model_settings.txt"
        trained_ids = []
        for p in trained:
            m = re.search(r"trained_1NN_(\d+)\.pt$", p.name)
            if m:
                trained_ids.append(int(m.group(1)))
        checkpoint_ids = []
        for p in checkpoints:
            m = re.search(r"checkpoint_step_(\d+)\.pt$", p.name)
            if m:
                checkpoint_ids.append(int(m.group(1)))
        records.append({{
            "record_type": "archive",
            "remote_path": str(archive),
            "project": archive.relative_to(root).parts[0] if archive.is_relative_to(root) else "",
            "name": archive.name,
            "has_settings": settings.exists(),
            "has_alpha_bar": ab.exists(),
            "has_kt": (best / "Kt_vs_cycle.npy").exists(),
            "has_xtip": (best / "x_tip_vs_cycle.npy").exists(),
            "trained_count": len(trained),
            "checkpoint_count": len(checkpoints),
            "max_trained_index": max(trained_ids, default=-1),
            "max_checkpoint_index": max(checkpoint_ids, default=-1),
        }})
    for log in root.glob("**/run_logs/**/*.log"):
        lname = log.name.lower()
        if any(k in lname for k in ("tip", "patch", "branch", "wr010", "femmesh", "tolir", "explicit", "hardirr", "adapthist")):
            records.append({{
                "record_type": "log",
                "remote_path": str(log),
                "project": log.relative_to(root).parts[0] if log.is_relative_to(root) else "",
                "name": log.name,
                "has_settings": False,
                "has_alpha_bar": False,
                "has_kt": False,
                "has_xtip": False,
                "trained_count": 0,
                "checkpoint_count": 0,
                "max_trained_index": -1,
                "max_checkpoint_index": -1,
            }})
print(json.dumps(records))
"""


@dataclass
class Classified:
    record_type: str
    tier: str
    family: str
    status: str
    comparison_use: str
    required_action: str
    remote_path: str
    project: str
    name: str
    umax: str
    n_value: str
    seed: str
    max_trained_index: int
    max_checkpoint_index: int
    has_settings: bool
    has_alpha_bar: bool
    has_kt: bool
    has_xtip: bool


def rx(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text)
    return m.group(1) if m else default


def family_from_name(name: str, path: str) -> str:
    low = f"{path} {name}".lower()
    if "femmesh" in low or "femmesh" in low.replace("_", ""):
        return "FEM-mesh / soft-hist0 alignment"
    if "tolir" in low:
        return "irreversibility tolerance"
    if "explicitcycle" in low or "explicit_cycle" in low:
        return "explicit cycle/substep timing"
    if "reversebc_softhist0_forward" in low:
        return "soft-hist0 forward / tol-ir"
    if "branch_restart" in low or re.search(r"br_c\d+", low):
        return "branch restart"
    if "patch_strength" in low or low.startswith("ps_") or "_ps_" in low:
        return "patch strength"
    if "tiplocal" in low or "tip_local" in low:
        return "tip-local patch"
    if "wr010" in low or "wr0.10" in low:
        return "wider local patch"
    if "sidecars2" in low or "sidecars1" in low or "tipfol" in low:
        return "sidecar / tip-follow sampling"
    if "adapthist" in low:
        return "adaptive lambda_hist"
    if "hardirr" in low:
        return "hard irreversibility"
    if "fourier" in low:
        return "Fourier representation"
    if "siren" in low:
        return "SIREN representation"
    if "williams" in low:
        return "Williams enrichment"
    if "exactbc" in low:
        return "exact boundary condition"
    if "enriched" in low:
        return "enriched ansatz"
    if "psihack" in low:
        return "psi/history hack"
    if "oracle" in low:
        return "oracle zone"
    if "sym" in low or "strac" in low:
        return "symmetry / side-traction"
    if "baseline" in low:
        return "baseline"
    return "other"


def classify(record: dict) -> Classified:
    name = record["name"]
    path = record["remote_path"]
    low = f"{path} {name}".lower()
    umax = rx(r"Umax([0-9.]+)", name)
    n_value = rx(r"_N(?:cyc)?([0-9]+)", name)
    seed = rx(r"Seed_([0-9]+)", name)
    family = family_from_name(name, path)
    record_type = record["record_type"]
    full_u012 = umax in {"0.12", "0.120"} or "umax0.12" in low
    enough_cycles = int(record.get("max_trained_index", -1)) >= 68 or int(record.get("trained_count", 0)) >= 69

    if record_type == "log":
        if any(k in low for k in ("tip", "patch", "branch", "wr010")):
            tier = "Tier 1 - mechanism diagnostic"
            comparison_use = "method evidence / locate matching archive"
            action = "parse log and map to archive before field rescore"
        else:
            tier = "Tier 3 - bookkeeping"
            comparison_use = "run provenance only"
            action = "no field comparison unless matching archive is found"
        status = "log-only"
    elif "femmesh_softhist0" in low or "reversebc_softhist0_forward" in low:
        tier = "Tier 0 - strict benchmark"
        comparison_use = "absolute FEM-vs-PIDL comparison"
        action = "rescore with FEM c -> PIDL j=c-1 on common probes"
        status = "complete" if enough_cycles else "partial"
    elif "pidl-align-soft-hist0-20260529" in low and any(k in low for k in ("tolir", "explicitcycle")):
        tier = "Tier 1 - controlled alignment diagnostic"
        comparison_use = "one-factor timing/tolerance evidence; setting audit required before absolute FEM claims"
        action = "rescore with j0 protocol and verify initial crack, mesh, and history timing before promoting"
        status = "complete" if enough_cycles else "partial"
    elif (
        full_u012
        and any(k in low for k in ("sidecar", "tiplocal", "tip_local", "adapthist", "hardirr", "branch", "patch", "wr010"))
    ):
        tier = "Tier 1 - mechanism diagnostic"
        comparison_use = "mechanism ranking under old settings"
        action = "rescore with j0 protocol, then rerun winners under Tier 0 settings"
        status = "complete" if enough_cycles else "partial"
    elif full_u012:
        tier = "Tier 2 - legacy architecture evidence"
        comparison_use = "idea mining only"
        action = "rescore if loader compatible; do not make absolute FEM claims"
        status = "complete" if enough_cycles else "partial"
    else:
        tier = "Tier 3 - out of current benchmark"
        comparison_use = "not comparable to u=0.12 soft-hist0 FEM"
        action = "exclude unless doing Umax/multiseed sensitivity"
        status = "complete" if enough_cycles else "partial"

    if "fourier" in low and record_type == "archive":
        action += "; may need historical Fourier checkpoint compatibility loader"
    if not record.get("has_settings", False) and record_type == "archive":
        action += "; audit settings from name/log because model_settings.txt is missing"

    return Classified(
        record_type=record_type,
        tier=tier,
        family=family,
        status=status,
        comparison_use=comparison_use,
        required_action=action,
        remote_path=path,
        project=record["project"],
        name=name,
        umax=umax,
        n_value=n_value,
        seed=seed,
        max_trained_index=int(record.get("max_trained_index", -1)),
        max_checkpoint_index=int(record.get("max_checkpoint_index", -1)),
        has_settings=bool(record.get("has_settings", False)),
        has_alpha_bar=bool(record.get("has_alpha_bar", False)),
        has_kt=bool(record.get("has_kt", False)),
        has_xtip=bool(record.get("has_xtip", False)),
    )


def fetch_records(host: str, root: str) -> list[dict]:
    code = REMOTE_SCRIPT.format(root=root)
    proc = subprocess.run(
        ["ssh", host, "python3", "-"],
        input=code,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(proc.stdout)


def write_csv(rows: list[Classified], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(Classified.__dataclass_fields__)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_doc(rows: list[Classified], out_doc: Path, out_csv: Path) -> None:
    counts: dict[str, int] = {}
    family_counts: dict[tuple[str, str], int] = {}
    for row in rows:
        counts[row.tier] = counts.get(row.tier, 0) + 1
        family_counts[(row.tier, row.family)] = family_counts.get((row.tier, row.family), 0) + 1

    priority = [
        row for row in rows
        if row.record_type == "archive"
        and row.tier in {
            "Tier 0 - strict benchmark",
            "Tier 1 - controlled alignment diagnostic",
            "Tier 1 - mechanism diagnostic",
        }
        and row.umax == "0.12"
    ]
    priority.sort(key=lambda r: (
        0 if r.tier.startswith("Tier 0") else 1,
        0 if r.status == "complete" else 1,
        r.family,
        -r.max_trained_index,
    ))
    priority = priority[:18]

    lines = [
        "# Taobo Tiered PIDL Comparison Plan",
        "",
        "Date: 2026-05-29",
        "",
        "## Purpose",
        "",
        "This manifest prevents old Taobo runs from being compared as if they all",
        "shared the current soft-hist0 FEM/PIDL protocol.  Each run gets a tier",
        "before it enters a scoreboard.",
        "",
        "## Tier Rule",
        "",
        "- Tier 0: strict benchmark.  Use for absolute FEM-vs-PIDL comparison.",
        "- Tier 1: mechanism diagnostic.  Use for ranking ideas; rerun winners under Tier 0.",
        "- Tier 2: legacy architecture evidence.  Use for idea mining only.",
        "- Tier 3: out of current benchmark.  Exclude unless doing a different sensitivity.",
        "",
        "## Inventory Counts",
        "",
    ]
    for tier in sorted(counts):
        lines.append(f"- {tier}: {counts[tier]}")
    lines += [
        "",
        "## Family Counts",
        "",
    ]
    for (tier, family), count in sorted(family_counts.items()):
        lines.append(f"- {tier} / {family}: {count}")
    lines += [
        "",
        "## First Rescore Queue",
        "",
        "| Tier | Family | Status | Max saved index | Action | Remote path |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in priority:
        lines.append(
            f"| {row.tier} | {row.family} | {row.status} | {row.max_trained_index} | "
            f"{row.required_action} | `{row.remote_path}` |"
        )
    lines += [
        "",
        "## Comparison Protocol",
        "",
        "1. Score Tier 0 first with `FEM c -> PIDL j=c-1`, common probes, and",
        "   separate absolute versus incremental `E_d`.",
        "2. Score Tier 1 with the same posthoc metrics, but label the output as",
        "   mechanism ranking under old settings.",
        "3. Promote only Tier 1 winners into new strict soft-hist0/FEM-mesh reruns.",
        "4. Keep Tier 2 as evidence for what is worth rebuilding, not as final",
        "   FEM/PIDL evidence.",
        "",
        "Primary gates: c20/c40/c69 `damage`, `alpha_bar`, active `psi_plus`,",
        "p99/p999, near-tip integrals, process-zone width, and `Delta E_d` from c1.",
        "",
        "## Generated Manifest",
        "",
        f"CSV: `{out_csv.relative_to(out_doc.parent.parent)}`",
        "",
        "## Immediate Rescore Result",
        "",
        "The strict FEM-mesh soft-hist0 benchmark and the Taobo `tol_ir=0.001`",
        "forward archive have now both been rescored with the current `FEM c -> PIDL",
        "j=c-1` protocol.  The `reverseBC_softHist0_forward_tolir0.001` archive and",
        "the controlled `tolir0.001_baseline` archive are checkpoint-identical for the",
        "sampled states, so they should not be counted as two independent methods.",
        "",
        "| Method | Cycle | damage tip2 | alpha_bar tip2 | alpha_bar p99 | active psi tip2 | active psi p99 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        "| FEM-mesh softHist0 | 1 | 1.008 | 0.985 | 0.421 | 1.013 | 1.053 |",
        "| FEM-mesh softHist0 | 20 | 0.996 | 0.946 | 0.928 | 1.150 | 1.018 |",
        "| FEM-mesh softHist0 | 40 | 1.002 | 0.792 | 0.430 | 0.245 | 0.994 |",
        "| FEM-mesh softHist0 | 69 | 1.012 | 0.466 | 0.191 | 0.029 | 1.374 |",
        "| softHist0/tol_ir=0.001 | 1 | 1.028 | 1.011 | 0.511 | 1.038 | 1.129 |",
        "| softHist0/tol_ir=0.001 | 20 | 1.118 | 1.057 | 1.026 | 1.692 | 1.009 |",
        "| softHist0/tol_ir=0.001 | 40 | 1.272 | 0.883 | 0.476 | 0.188 | 0.967 |",
        "| softHist0/tol_ir=0.001 | 69 | 1.464 | 0.516 | 0.216 | 0.033 | 1.312 |",
        "",
        "Reading: the tolerance change does not close the late-cycle mechanism gap.",
        "It increases near-tip damage relative to FEM, but the late near-tip fatigue",
        "history and active degraded driver are still far below FEM.  Therefore",
        "`tol_ir=0.001` is not a field-mechanism fix by itself.",
        "",
    ]
    out_doc.parent.mkdir(parents=True, exist_ok=True)
    out_doc.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="gpu-taobo")
    parser.add_argument("--remote-root", default=DEFAULT_ROOT)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_DIR / "taobo_tier_manifest_20260529.csv")
    parser.add_argument("--out-doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()

    records = fetch_records(args.host, args.remote_root)
    rows = [classify(record) for record in records]
    rows.sort(key=lambda r: (r.tier, r.family, r.project, r.name, r.remote_path))
    write_csv(rows, args.out_csv)
    write_doc(rows, args.out_doc, args.out_csv)
    print(f"records: {len(rows)}")
    print(f"wrote {args.out_csv}")
    print(f"wrote {args.out_doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
