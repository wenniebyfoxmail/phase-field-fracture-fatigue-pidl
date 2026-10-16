"""Shared exact-code identity checks for S09-E008 export and execution."""
from __future__ import annotations

from pathlib import Path
import subprocess


EXECUTION_FILES = (
    "source/s09_code_identity.py",
    "source/s09_stage0a_capability.py", "source/s09_stage0a_p1_packet.py",
    "source/s09_stage0a_p1_trainer.py", "source/s09_stage0a_transition.py",
    "source/s09_multiobjective_update.py", "source/s09_fem_physics.py",
    "source/s09_q4_quadrature.py", "source/s09_equilibrium_operator.py",
    "source/s09_operator.py", "source/s09_stage0a_packet.py",
    "source/s09_stage0a_p1_freeze.py", "scripts/export_s09_stage0a_p1_packet.py",
    "scripts/resolve_s09_stage0a_p1_config.py", "scripts/run_s09_stage0a_p1.py",
)


def current_commit(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def tracked_execution_files_clean(root: Path) -> bool:
    result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *EXECUTION_FILES],
                            cwd=root)
    return result.returncode == 0


def require_approved_code(root: Path, approved_commit: str) -> None:
    if current_commit(root) != approved_commit:
        raise ValueError("current commit differs from externally approved Code Ready commit")
    if not tracked_execution_files_clean(root):
        raise ValueError("tracked execution files are dirty")
