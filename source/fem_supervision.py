"""
fem_supervision.py — MIT-8 (Apr 25 2026)

Loads FEM ψ⁺_raw snapshots and provides per-cycle target tensors aligned
to PIDL element centroids via nearest-neighbor interpolation.

FEM data format (`u<UMAX>_cycle_<NNNN>.mat` from `_pidl_handoff_v2/
psi_snapshots_for_agent/`):
    psi_elem        : (N_FEM_elem, 1) — RAW ψ⁺ per element (undegraded)
    d_elem          : (N_FEM_elem, 1) — damage at element
    alpha_bar_elem  : (N_FEM_elem, 1) — fatigue history
    f_alpha_elem    : (N_FEM_elem, 1) — fatigue degradation factor

Mesh (`mesh_geometry.mat`):
    element_centroids : (N_FEM_elem, 2)
    node_coords       : (N_node, 2)
    connectivity      : (N_FEM_elem, 4) — int32, 1-indexed

Supervision target: FEM ψ⁺_raw at PIDL element centroids, time-interpolated
between available cycles {1, 40, 70, 82} for U_max=0.12.

Usage from runner:
    fem_sup = FEMSupervision(umax=0.12)
    target = fem_sup.psi_target_at_cycle(j, pidl_centroids)  # tensor
    # add λ·MSE(psi_pidl_raw_per_elem, target) to training loss
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch

DEFAULT_FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/"
                       "psi_snapshots_for_agent")

# Cycles where FEM snapshots exist (per U_max)
_AVAILABLE_CYCLES = {
    0.08: [1, 150, 350, 396],
    0.12: [1, 40, 70, 82],
}


class FEMSupervision:
    """Loads FEM ψ⁺_raw snapshots, provides time + space interpolation."""

    def __init__(self, umax: float, fem_dir: Path = DEFAULT_FEM_DIR):
        self.umax = umax
        self.fem_dir = Path(fem_dir)
        if umax not in _AVAILABLE_CYCLES:
            raise ValueError(f"No FEM snapshots for umax={umax}. "
                             f"Available: {list(_AVAILABLE_CYCLES.keys())}")
        self.cycles = _AVAILABLE_CYCLES[umax]
        self._load_mesh()
        self._load_snapshots()

    def _load_mesh(self) -> None:
        mesh = sio.loadmat(str(self.fem_dir / "mesh_geometry.mat"))
        self.fem_centroids = np.asarray(mesh["element_centroids"], dtype=np.float64)
        # shape (N_FEM, 2)

    def _load_snapshots(self) -> None:
        """Load all cycle snapshots into self.psi_raw[c] = array(N_FEM,)."""
        u_tag = f"u{int(round(self.umax * 100)):02d}"
        self.psi_raw: dict[int, np.ndarray] = {}
        self.d_field: dict[int, np.ndarray] = {}
        for c in self.cycles:
            fname = self.fem_dir / f"{u_tag}_cycle_{c:04d}.mat"
            if not fname.is_file():
                raise FileNotFoundError(fname)
            data = sio.loadmat(str(fname))
            self.psi_raw[c] = np.asarray(data["psi_elem"], dtype=np.float64).ravel()
            self.d_field[c] = np.asarray(data["d_elem"], dtype=np.float64).ravel()

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

        Time interpolation: if cycle_idx is between two available FEM cycles,
        linearly interpolate; if before/after available range, clamp to nearest.
        """
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
