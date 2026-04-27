#!/usr/bin/env python3
"""
run_e2_reverse_umax_windows.py — Windows wrapper for Mac's run_e2_reverse_umax.py

Mac's runner uses fem_supervision.DEFAULT_FEM_DIR which is hardcoded to a Mac path
(/Users/wenxiaofang/Downloads/_pidl_handoff_v2/...). On Windows the same FEM dump
lives at the GRIPHFiTH project dir (Windows-FEM produced it locally).

This wrapper monkey-patches DEFAULT_FEM_DIR to the Windows location BEFORE Mac's
runner imports / instantiates FEMSupervision, then defers to Mac's runner via
runpy. No source/ or Mac-runner modifications.

Usage (CLI args identical to Mac's runner):
    python run_e2_reverse_umax_windows.py 0.12
    python run_e2_reverse_umax_windows.py 0.08 --n-cycles 500 --zone-radius 0.02
"""
from __future__ import annotations
import sys
import runpy
from pathlib import Path

WIN_FEM_DIR = Path(
    r"C:\Users\xw436\GRIPHFiTH\Scripts\fatigue_fracture\_pidl_handoff_v2"
    r"\psi_snapshots_for_agent"
)

if not WIN_FEM_DIR.exists():
    raise SystemExit(f"[wrapper] FEM data dir not found: {WIN_FEM_DIR}")

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

import fem_supervision  # noqa: E402

print(f"[wrapper] Patching fem_supervision FEM dir")
print(f"[wrapper]   was: {fem_supervision.DEFAULT_FEM_DIR}")
print(f"[wrapper]   now: {WIN_FEM_DIR}")
fem_supervision.DEFAULT_FEM_DIR = WIN_FEM_DIR
# Function defaults are bound at def-time → patching the module-level
# DEFAULT_FEM_DIR does NOT update FEMSupervision.__init__'s `fem_dir` default.
# Override the constructor's __defaults__ tuple instead:
fem_supervision.FEMSupervision.__init__.__defaults__ = (WIN_FEM_DIR,)

# Rename argv[0] so argparse error messages look natural (not 'wrapper.py')
TARGET = HERE / "run_e2_reverse_umax.py"
sys.argv[0] = str(TARGET)

# Hand off to Mac's runner — runs with current sys.argv (umax + flags forwarded)
runpy.run_path(str(TARGET), run_name="__main__")
