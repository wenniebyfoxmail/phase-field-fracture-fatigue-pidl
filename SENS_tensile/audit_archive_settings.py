#!/usr/bin/env python3
"""
audit_archive_settings.py — Sanity-check PIDL archive setup before paper use.

Catches the three known runner/checkpoint bugs by cross-checking every paper-grade
archive against its name + saved settings + checkpoint state:

  1. CLI-Umax bug (ea4b4ab Apr-25): name says Umax=X but settings.disp_max != X
     because runner forgot to call config.rebuild_disp_cyclic().
  2. savefolder no-op + checkpoint inheritance (6040cbb May-4): an archive whose
     first/earliest x_tip is already deep into the specimen (>0.05) — strong sign
     it resumed from someone else's checkpoint.
  3. Post-fracture resume (427ebe7 May-4): if max(x_tip_history) reaches the right
     boundary BEFORE the run started, the result is a resume artifact.

Also flags `_BUG_actuallyUmax0.12_*` renamed archives, incomplete runs, fallback
false-stops.

Usage:
  python audit_archive_settings.py                # audit current dir (SENS_tensile/)
  python audit_archive_settings.py PATH [PATH ...]
  python audit_archive_settings.py --glob "*Umax0.12*"
  python audit_archive_settings.py --csv audit.csv
  python audit_archive_settings.py --strict       # exit 1 if any WARN/FAIL

Exit code: 0 if all PASS (or all PASS+WARN without --strict), 1 otherwise.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


# ── Constants from model_train.py defaults ──────────────────────────────────
RIGHT_BDY_X_MIN_DEFAULT = 0.48          # fracture trigger threshold for tip
FRESH_START_X_TIP_MAX = 0.05            # fresh runs should start with tip ≈ 0
KNOWN_BAD_TOKENS = ("_BUG_", "_invalid", "_incomplete", "_failed",
                    "_fallback_false_stop")

# Tolerance for float compare on Umax (1e-6 is generous; settings stores str)
UMAX_FLOAT_TOL = 1e-6


# ── Parsers ─────────────────────────────────────────────────────────────────
NAME_RE = re.compile(
    r"^hl_(?P<hl>\d+)_Neurons_(?P<neurons>\d+)_"
    r"activation_(?P<activation>[^_]+)_"
    r"coeff_(?P<coeff>[\d.]+)_"
    r"Seed_(?P<seed>\d+)_"
    r".*?"
    r"_N(?P<n_cycles>\d+)_R(?P<R>[\d.]+)_Umax(?P<umax>[\d.]+)"
    r"(?P<suffix>.*)$"
)


@dataclass
class Finding:
    level: str        # "PASS" | "WARN" | "FAIL"
    code: str
    detail: str


@dataclass
class AuditRow:
    archive: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(f.level == "FAIL" for f in self.findings):
            return "FAIL"
        if any(f.level == "WARN" for f in self.findings):
            return "WARN"
        return "PASS"


def parse_archive_name(name: str) -> dict | None:
    m = NAME_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    d["coeff"] = float(d["coeff"])
    d["seed"] = int(d["seed"])
    d["n_cycles"] = int(d["n_cycles"])
    d["umax"] = float(d["umax"])
    d["suffix"] = d["suffix"].lstrip("_") or "<baseline>"
    return d


def parse_settings(path: Path) -> dict | None:
    if not path.exists():
        return None
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # Some keys appended "(overridden)" — strip that
        key = re.sub(r"\s*\(.*\)\s*$", "", key).strip()
        out[key] = val
    return out


def safe_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def safe_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Audit checks ────────────────────────────────────────────────────────────
def check_known_bad_token(row: AuditRow, name: str) -> None:
    for tok in KNOWN_BAD_TOKENS:
        if tok in name:
            row.findings.append(Finding(
                "FAIL", "known_bad",
                f"name contains {tok!r} (renamed/marked as invalid)"
            ))
            return


def check_name_parses(row: AuditRow, parsed: dict | None) -> bool:
    if parsed is None:
        row.findings.append(Finding(
            "WARN", "name_parse",
            "could not parse archive name — non-standard layout"
        ))
        return False
    return True


def check_settings_match_name(row: AuditRow, parsed: dict, settings: dict | None) -> None:
    if settings is None:
        row.findings.append(Finding(
            "WARN", "missing_settings",
            "model_settings.txt missing (incomplete run, or method runner skipped writing)"
        ))
        return

    # Umax / disp_max guard (catches CLI-Umax bug)
    s_disp_max = safe_float(settings.get("disp_max"))
    if s_disp_max is None:
        row.findings.append(Finding(
            "WARN", "missing_disp_max",
            "model_settings.txt has no disp_max entry"
        ))
    elif abs(s_disp_max - parsed["umax"]) > UMAX_FLOAT_TOL:
        row.findings.append(Finding(
            "FAIL", "umax_mismatch",
            f"name says Umax={parsed['umax']} but settings.disp_max={s_disp_max} "
            f"(CLI-Umax bug fingerprint — likely actually trained at default)"
        ))

    # n_cycles cross-check (looser; runners may N=10 smoke into N=300 archive name)
    s_ncyc = safe_int(settings.get("n_cycles"))
    if s_ncyc is not None and s_ncyc != parsed["n_cycles"]:
        row.findings.append(Finding(
            "WARN", "ncycles_mismatch",
            f"name says N={parsed['n_cycles']} but settings.n_cycles={s_ncyc} "
            f"(common for resumed/extended runs; verify intentional)"
        ))

    # coeff cross-check
    s_coeff = safe_float(settings.get("coeff"))
    if s_coeff is not None and abs(s_coeff - parsed["coeff"]) > 1e-6:
        row.findings.append(Finding(
            "FAIL", "coeff_mismatch",
            f"name says coeff={parsed['coeff']} but settings.coeff={s_coeff}"
        ))


def check_x_tip_trajectory(row: AuditRow, archive: Path) -> None:
    """Catches checkpoint-inheritance and post-fracture resume bugs.

    A clean fresh run starts with x_tip ≈ 0. If the FIRST recorded x_tip is
    already past FRESH_START_X_TIP_MAX, the run resumed from foreign state.
    """
    # Try new filename first (post-Apr-25 runs), fall back to legacy
    candidates = [
        archive / "best_models" / "x_tip_alpha_vs_cycle.npy",
        archive / "best_models" / "x_tip_vs_cycle.npy",
    ]
    npy = next((p for p in candidates if p.exists()), None)
    if npy is None:
        # Not necessarily bad — early/incomplete runs may not have one yet.
        row.findings.append(Finding(
            "WARN", "no_x_tip_history",
            "best_models/x_tip*_vs_cycle.npy missing — cannot verify fresh start"
        ))
        return

    try:
        hist = np.load(npy, allow_pickle=False)
    except Exception as e:
        row.findings.append(Finding(
            "WARN", "x_tip_load_fail",
            f"could not load x_tip history: {e}"
        ))
        return

    if hist.size == 0:
        row.findings.append(Finding(
            "WARN", "x_tip_empty",
            "x_tip history is empty"
        ))
        return

    first = float(hist.flat[0])
    last = float(hist.flat[-1])

    if first > FRESH_START_X_TIP_MAX:
        row.findings.append(Finding(
            "FAIL", "resume_from_foreign",
            f"first x_tip={first:.4f} > {FRESH_START_X_TIP_MAX} "
            f"(strong evidence the run inherited a non-fresh checkpoint)"
        ))

    if first >= RIGHT_BDY_X_MIN_DEFAULT:
        row.findings.append(Finding(
            "FAIL", "resume_post_fracture",
            f"first x_tip={first:.4f} already past right boundary "
            f"({RIGHT_BDY_X_MIN_DEFAULT}) — resume-from-fractured artifact"
        ))


def check_checkpoint_existence(row: AuditRow, archive: Path) -> None:
    ckpts = list((archive / "best_models").glob("checkpoint_step_*.pt")) if (archive / "best_models").exists() else []
    if not ckpts:
        row.findings.append(Finding(
            "WARN", "no_checkpoint",
            "no best_models/checkpoint_step_*.pt — incomplete or pre-checkpoint format"
        ))


# ── Top-level audit ─────────────────────────────────────────────────────────
def audit_archive(archive: Path) -> AuditRow:
    row = AuditRow(archive=str(archive.name))
    name = archive.name

    check_known_bad_token(row, name)
    parsed = parse_archive_name(name)
    if not check_name_parses(row, parsed):
        return row
    settings = parse_settings(archive / "model_settings.txt")
    check_settings_match_name(row, parsed, settings)
    check_x_tip_trajectory(row, archive)
    check_checkpoint_existence(row, archive)
    return row


def discover_archives(roots: list[Path], glob_pat: str | None) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_file():
            continue
        if (root / "model_settings.txt").exists() or (root / "best_models").exists():
            # Treat root itself as an archive
            out.append(root)
            continue
        # Otherwise walk children
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("."):
                continue
            if glob_pat and not child.match(glob_pat):
                continue
            # Heuristic: archive directories start with "hl_"
            if not child.name.startswith("hl_"):
                continue
            out.append(child)
    return out


# ── Reporting ───────────────────────────────────────────────────────────────
COLORS = {
    "PASS": "\033[32m",  # green
    "WARN": "\033[33m",  # yellow
    "FAIL": "\033[31m",  # red
    "RESET": "\033[0m",
}


def fmt(level: str, color: bool) -> str:
    if not color:
        return f"[{level}]"
    return f"{COLORS[level]}[{level}]{COLORS['RESET']}"


def print_report(rows: list[AuditRow], color: bool) -> None:
    pass_n = warn_n = fail_n = 0
    for row in rows:
        st = row.status
        print(f"{fmt(st, color)} {row.archive}")
        for f in row.findings:
            if f.level == "PASS":
                continue
            print(f"    {fmt(f.level, color)} {f.code}: {f.detail}")
        if st == "PASS":
            pass_n += 1
        elif st == "WARN":
            warn_n += 1
        else:
            fail_n += 1

    total = pass_n + warn_n + fail_n
    print()
    print(f"Audited {total} archive(s): "
          f"{fmt('PASS', color)} {pass_n}  "
          f"{fmt('WARN', color)} {warn_n}  "
          f"{fmt('FAIL', color)} {fail_n}")


def write_csv(rows: list[AuditRow], path: Path) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["archive", "status", "level", "code", "detail"])
        for row in rows:
            if not row.findings:
                w.writerow([row.archive, row.status, "PASS", "ok", ""])
                continue
            for f in row.findings:
                w.writerow([row.archive, row.status, f.level, f.code, f.detail])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("paths", nargs="*", type=Path,
                   help="Archive paths or directories containing archives "
                        "(default: current directory)")
    p.add_argument("--glob", type=str, default=None,
                   help="Filter archive names by glob pattern, e.g. '*Umax0.12*'")
    p.add_argument("--csv", type=Path, default=None,
                   help="Also write machine-readable CSV report")
    p.add_argument("--strict", action="store_true",
                   help="Exit code 1 if any WARN or FAIL (default: only FAIL)")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI color in stdout")
    args = p.parse_args()

    roots = args.paths or [Path.cwd()]
    archives = discover_archives(roots, args.glob)
    if not archives:
        print("No archives found.", file=sys.stderr)
        return 1

    rows = [audit_archive(a) for a in archives]
    color = (not args.no_color) and sys.stdout.isatty()
    print_report(rows, color)

    if args.csv:
        write_csv(rows, args.csv)
        print(f"\nCSV written to {args.csv}")

    if args.strict:
        bad = any(r.status != "PASS" for r in rows)
    else:
        bad = any(r.status == "FAIL" for r in rows)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
