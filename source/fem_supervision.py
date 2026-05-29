"""
fem_supervision.py — MIT-8 (Apr 25 2026; Apr 27 full-sweep update)

Loads FEM ψ⁺_raw snapshots and provides per-cycle target tensors aligned
to PIDL element centroids via nearest-neighbor interpolation.

FEM data format. Two layouts are auto-detected inside the FEM dir:

  (a) FLAT (Mac handoff_v2):
        u<NN>_cycle_<NNNN>.mat                 e.g. u12_cycle_0040.mat
        mesh_geometry.mat

  (b) NESTED (Windows full export):
        SENT_PIDL_<NN>_export/psi_fields/cycle_<NNNN>.mat
        mesh_geometry.mat                       (anywhere at top level)

Both produce per-cycle .mat files with key `psi_elem` (N_FEM_elem, 1).

The dir is resolved in this priority order:
    1. ctor arg `fem_dir` (explicit override)
    2. env var `FEM_DATA_DIR` (Windows / cluster override)
    3. DEFAULT_FEM_DIR (Mac local handoff_v2 path)

Available cycles are auto-discovered from filesystem — no hardcoded
cycle list. When a requested cycle exists exactly, no interpolation is
applied (Apr 27 finding: Windows has full per-cycle dump for all 5 Umax,
making time-interp unnecessary on that machine).

Usage from runner:
    fem_sup = FEMSupervision(umax=0.12)
    target = fem_sup.psi_target_at_cycle(j, pidl_centroids)  # tensor
"""
from __future__ import annotations
import os
import re
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch

DEFAULT_FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/"
                       "psi_snapshots_for_agent")


def _resolve_fem_dir(explicit: Path | str | None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("FEM_DATA_DIR")
    if env:
        return Path(env)
    return DEFAULT_FEM_DIR


def _u_tag(umax: float) -> str:
    return f"u{int(round(umax * 100)):02d}"


class FEMSupervision:
    """Loads FEM ψ⁺_raw snapshots, provides time + space interpolation."""

    def __init__(self, umax: float, fem_dir: Path | str | None = None):
        self.umax = umax
        self.fem_dir = _resolve_fem_dir(fem_dir)
        if not self.fem_dir.is_dir():
            raise FileNotFoundError(
                f"FEM data dir not found: {self.fem_dir}. "
                f"Set FEM_DATA_DIR env var or pass fem_dir= to override.")
        self._discover_cycles()
        if not self.cycles:
            raise ValueError(
                f"No FEM snapshots for umax={umax} in {self.fem_dir}. "
                f"Looked for both '{_u_tag(umax)}_cycle_*.mat' (flat) and "
                f"'SENT_PIDL_{int(round(umax*100)):02d}_export/psi_fields/"
                f"cycle_*.mat' (nested).")
        self._load_mesh()
        self._load_snapshots()

    # ------------------------------------------------------------------
    # Layout discovery
    # ------------------------------------------------------------------
    def _discover_cycles(self) -> None:
        """Scan filesystem for cycle dump files; populate self.cycles + self._path_for[c]."""
        u_tag = _u_tag(self.umax)
        u_pct = int(round(self.umax * 100))
        path_for: dict[int, Path] = {}

        # Layout (a) FLAT
        flat_re = re.compile(rf"^{re.escape(u_tag)}_cycle_(\d+)\.mat$")
        for p in self.fem_dir.glob(f"{u_tag}_cycle_*.mat"):
            m = flat_re.match(p.name)
            if m:
                path_for[int(m.group(1))] = p

        # Layout (b) NESTED — only used to fill cycles not already found in flat
        nested_root = self.fem_dir / f"SENT_PIDL_{u_pct:02d}_export" / "psi_fields"
        if nested_root.is_dir():
            nested_re = re.compile(r"^cycle_(\d+)\.mat$")
            for p in nested_root.glob("cycle_*.mat"):
                m = nested_re.match(p.name)
                if m:
                    c = int(m.group(1))
                    path_for.setdefault(c, p)

        self._path_for = path_for
        self.cycles = sorted(path_for.keys())

    def _load_mesh(self) -> None:
        # mesh_geometry.mat may sit at either FEM_DATA_DIR root or alongside the
        # nested export dir. Search both.
        candidates = [
            self.fem_dir / "mesh_geometry.mat",
            self.fem_dir.parent / "mesh_geometry.mat",
        ]
        for c in candidates:
            if c.is_file():
                mesh = sio.loadmat(str(c))
                self.fem_centroids = np.asarray(
                    mesh["element_centroids"], dtype=np.float64)
                return
        raise FileNotFoundError(
            f"mesh_geometry.mat not found near {self.fem_dir}. "
            f"Checked: {[str(c) for c in candidates]}")

    def _load_snapshots(self) -> None:
        """Load all cycle snapshots into self.psi_raw[c] = array(N_FEM,)."""
        self.psi_raw: dict[int, np.ndarray] = {}
        self.d_field: dict[int, np.ndarray] = {}
        for c in self.cycles:
            fname = self._path_for[c]
            data = sio.loadmat(str(fname))
            self.psi_raw[c] = np.asarray(data["psi_elem"], dtype=np.float64).ravel()
            # d_elem is optional in nested-layout files; tolerate absence
            d = data.get("d_elem", data.get("alpha_elem"))
            if d is not None:
                self.d_field[c] = np.asarray(d, dtype=np.float64).ravel()

    def _interpolate_to_pidl(self, fem_field: np.ndarray,
                             pidl_centroids: np.ndarray) -> np.ndarray:
        """Nearest-neighbor: for each PIDL element, find closest FEM element."""
        # pidl_centroids: (N_PIDL, 2), fem_centroids: (N_FEM, 2)
        # For each PIDL row, compute distance to all FEM rows, take argmin.
        # N_PIDL is small (~6000), N_FEM is large (~78000), so brute-force OK.
        from scipy.spatial import cKDTree
        tree = cKDTree(self.fem_centroids)
        _, idx = tree.query(pidl_centroids, k=1)
        return fem_field[idx]   # shape (N_PIDL,)

    def psi_target_at_cycle(self, cycle_idx: int,
                            pidl_centroids: np.ndarray,
                            *, device: torch.device | None = None,
                            dtype: torch.dtype = torch.float32) -> torch.Tensor:
        """Return FEM ψ⁺_raw target at given cycle, on PIDL collocation.

        If the requested cycle_idx exists exactly in the dataset, use it
        directly (no interpolation). Otherwise linearly interpolate between
        the bracketing available cycles. Out-of-range requests clamp to
        nearest end.
        """
        if cycle_idx in self.psi_raw:
            psi = self._interpolate_to_pidl(self.psi_raw[cycle_idx], pidl_centroids)
        else:
            c_lo, c_hi = self._bracket_cycles(cycle_idx)
            psi_lo_pidl = self._interpolate_to_pidl(self.psi_raw[c_lo], pidl_centroids)
            if c_hi == c_lo:
                psi = psi_lo_pidl
            else:
                psi_hi_pidl = self._interpolate_to_pidl(self.psi_raw[c_hi], pidl_centroids)
                t = (cycle_idx - c_lo) / (c_hi - c_lo)
                psi = (1.0 - t) * psi_lo_pidl + t * psi_hi_pidl
        out = torch.from_numpy(psi).to(dtype=dtype)
        if device is not None:
            out = out.to(device)
        return out

    def _bracket_cycles(self, cycle_idx: int) -> tuple[int, int]:
        """Return (c_lo, c_hi) bracketing cycle_idx; equal if exact or out of range."""
        if cycle_idx <= self.cycles[0]:
            return (self.cycles[0], self.cycles[0])
        if cycle_idx >= self.cycles[-1]:
            return (self.cycles[-1], self.cycles[-1])
        for i in range(len(self.cycles) - 1):
            if self.cycles[i] <= cycle_idx <= self.cycles[i + 1]:
                return (self.cycles[i], self.cycles[i + 1])
        return (self.cycles[0], self.cycles[0])

    def supervised_loss(self, psi_pidl_raw_per_elem: torch.Tensor,
                        cycle_idx: int,
                        pidl_centroids: np.ndarray,
                        lambda_sup: float = 1.0,
                        loss_kind: str = "mse_log") -> torch.Tensor:
        """Compute λ·loss(ψ⁺_PIDL_raw, ψ⁺_FEM_raw_interp) at cycle_idx.

        loss_kind:
          'mse_log' — MSE on log10(ψ⁺ + eps), recommended (handles 8 orders of
              magnitude variation in ψ⁺_raw without dominating gradient at tip)
          'mse_lin' — plain MSE (will be dominated by tip element)
          'mse_rel' — MSE on relative error (ψ_p - ψ_f)/(ψ_f + eps), elementwise
        """
        target = self.psi_target_at_cycle(
            cycle_idx, pidl_centroids,
            device=psi_pidl_raw_per_elem.device,
            dtype=psi_pidl_raw_per_elem.dtype)
        eps = 1e-12
        if loss_kind == "mse_log":
            ratio = torch.log10(psi_pidl_raw_per_elem.clamp(min=eps)) \
                  - torch.log10(target.clamp(min=eps))
            loss = (ratio ** 2).mean()
        elif loss_kind == "mse_lin":
            loss = ((psi_pidl_raw_per_elem - target) ** 2).mean()
        elif loss_kind == "mse_rel":
            rel = (psi_pidl_raw_per_elem - target) / (target.abs() + eps)
            loss = (rel ** 2).mean()
        else:
            raise ValueError(f"unknown loss_kind={loss_kind}")
        return lambda_sup * loss
