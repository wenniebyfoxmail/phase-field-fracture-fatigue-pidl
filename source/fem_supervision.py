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

    def alpha_target_at_cycle(self, cycle_idx: int,
                              pidl_centroids: np.ndarray,
                              *, device: torch.device | None = None,
                              dtype: torch.dtype = torch.float32) -> torch.Tensor:
        """Return FEM d_elem (= α phase-field) target at given cycle, on PIDL collocation.

        Mirrors psi_target_at_cycle() but loads from self.d_field instead of self.psi_raw.
        d_elem ∈ [0, 1] is the phase-field damage variable at each FEM element.

        ★ 2026-05-14: enables α-direct supervision per user request. Used when
        supervised_dict.target_kind == 'alpha'.
        """
        if not self.d_field:
            raise RuntimeError(
                "FEM .mat files do not contain d_elem field — alpha supervision unavailable. "
                "Re-export FEM snapshots with d_elem to use this path.")
        if cycle_idx in self.d_field:
            d = self._interpolate_to_pidl(self.d_field[cycle_idx], pidl_centroids)
        else:
            c_lo, c_hi = self._bracket_cycles(cycle_idx)
            if c_lo not in self.d_field or c_hi not in self.d_field:
                # If d_field is sparse, fall back to nearest available
                avail = sorted(self.d_field.keys())
                c_use = min(avail, key=lambda c: abs(c - cycle_idx))
                d = self._interpolate_to_pidl(self.d_field[c_use], pidl_centroids)
            else:
                d_lo_pidl = self._interpolate_to_pidl(self.d_field[c_lo], pidl_centroids)
                if c_hi == c_lo:
                    d = d_lo_pidl
                else:
                    d_hi_pidl = self._interpolate_to_pidl(self.d_field[c_hi], pidl_centroids)
                    t = (cycle_idx - c_lo) / (c_hi - c_lo)
                    d = (1.0 - t) * d_lo_pidl + t * d_hi_pidl
        out = torch.from_numpy(d).to(dtype=dtype)
        if device is not None:
            out = out.to(device)
        return out

    def alpha_supervised_loss(self, alpha_pidl_per_elem: torch.Tensor,
                              cycle_idx: int,
                              pidl_centroids: np.ndarray,
                              lambda_sup: float = 1.0,
                              loss_kind: str = "mse_lin",
                              mask: torch.Tensor | None = None) -> torch.Tensor:
        """Compute λ·MSE(α_PIDL_per_elem, d_elem_FEM_interp).

        ★ 2026-05-14: α-direct supervision (parallel to supervised_loss for ψ⁺).
        α ∈ [0,1] is well-conditioned for linear MSE (no log transform needed).

        Args:
          alpha_pidl_per_elem: (n_elem,) — NN α projected to elements (node-mean over T_conn).
          loss_kind: 'mse_lin' (default for α; no log since well-conditioned)
                     'mse_log' (parallel to ψ⁺ for direct comparison; uses log(α+eps))
          mask: bool tensor (n_elem,) — sparse anchor support.
        """
        target = self.alpha_target_at_cycle(
            cycle_idx, pidl_centroids,
            device=alpha_pidl_per_elem.device,
            dtype=alpha_pidl_per_elem.dtype)
        eps = 1e-12
        if loss_kind == "mse_lin":
            perel = (alpha_pidl_per_elem - target) ** 2
        elif loss_kind == "mse_log":
            perel = (torch.log10(alpha_pidl_per_elem.clamp(min=eps))
                   - torch.log10(target.clamp(min=eps))) ** 2
        elif loss_kind == "mse_rel":
            perel = ((alpha_pidl_per_elem - target) / (target.abs() + eps)) ** 2
        else:
            raise ValueError(f"unknown loss_kind={loss_kind}")

        if mask is None:
            loss = perel.mean()
        else:
            mask_b = mask.to(perel.device).bool()
            n = int(mask_b.sum().item())
            if n == 0:
                loss = perel.new_zeros(())
            else:
                loss = perel[mask_b].mean()
        return lambda_sup * loss

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
                        loss_kind: str = "mse_log",
                        mask: torch.Tensor | None = None) -> torch.Tensor:
        """Compute λ·loss(ψ⁺_PIDL_raw, ψ⁺_FEM_raw_interp) at cycle_idx.

        loss_kind:
          'mse_log' — MSE on log10(ψ⁺ + eps), recommended (handles 8 orders of
              magnitude variation in ψ⁺_raw without dominating gradient at tip)
          'mse_lin' — plain MSE (will be dominated by tip element)
          'mse_rel' — MSE on relative error (ψ_p - ψ_f)/(ψ_f + eps), elementwise

        ★ 2026-05-14: mask parameter for sparse boundary-anchor supervision.
        mask: bool tensor (n_elem,) — True for elements included in MSE.
            None = all elements (historical full-domain MIT-8 behavior).
            Sparse boundary anchor: True only at boundary/crack-path indices.
        """
        target = self.psi_target_at_cycle(
            cycle_idx, pidl_centroids,
            device=psi_pidl_raw_per_elem.device,
            dtype=psi_pidl_raw_per_elem.dtype)
        eps = 1e-12
        if loss_kind == "mse_log":
            perel = (torch.log10(psi_pidl_raw_per_elem.clamp(min=eps))
                   - torch.log10(target.clamp(min=eps))) ** 2
        elif loss_kind == "mse_lin":
            perel = (psi_pidl_raw_per_elem - target) ** 2
        elif loss_kind == "mse_rel":
            perel = ((psi_pidl_raw_per_elem - target) / (target.abs() + eps)) ** 2
        else:
            raise ValueError(f"unknown loss_kind={loss_kind}")

        if mask is None:
            loss = perel.mean()
        else:
            mask_b = mask.to(perel.device).bool()
            n = int(mask_b.sum().item())
            if n == 0:
                loss = perel.new_zeros(())
            else:
                loss = perel[mask_b].mean()
        return lambda_sup * loss


def _load_mat_any(path: Path | str, variable_names: list[str] | None = None) -> dict:
    """Load a MATLAB v7 or v7.3 file into a plain dict of arrays."""
    path = Path(path)
    try:
        return {
            k: v for k, v in sio.loadmat(str(path), variable_names=variable_names).items()
            if not k.startswith("__")
        }
    except NotImplementedError:
        import h5py

        out: dict[str, np.ndarray] = {}
        with h5py.File(path, "r") as h5:
            names = variable_names if variable_names is not None else list(h5.keys())
            for name in names:
                if name in h5 and hasattr(h5[name], "shape"):
                    out[name] = np.asarray(h5[name])
        return out


def _as_elem_by_cycle(arr: np.ndarray, n_elem: int | None = None) -> np.ndarray:
    """Return compact FEM field as (n_elem, n_cycle), regardless of MATLAB/HDF orientation."""
    arr = np.asarray(arr)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    if n_elem is not None:
        if arr.shape[0] == n_elem:
            return arr
        if arr.shape[1] == n_elem:
            return arr.T
    return arr if arr.shape[0] >= arr.shape[1] else arr.T


def _as_xy(arr: np.ndarray) -> np.ndarray:
    """Return coordinate-like arrays as (n, 2)."""
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"expected 2D coordinate array, got shape={arr.shape}")
    if arr.shape[1] == 2:
        return arr
    if arr.shape[0] == 2:
        return arr.T
    raise ValueError(f"cannot interpret coordinate array shape={arr.shape}")


class CyclewiseFEMFieldSupervision:
    """FEM cyclewise field supervision for the strict soft-hist0 handoffs.

    Supported target_kind values:
      alpha      -> FEM d_elem
      alpha_bar  -> FEM alpha_bar_elem
      history    -> alias for alpha_bar
      psi_active -> FEM psi_plus_elem, i.e. g(alpha) * psi_raw
      psi_raw    -> FEM psi_raw_elem if exported, otherwise psi_plus_elem / g(d_elem)
    """

    _FIELD_ALIASES = {
        "alpha": ("d_elem", "alpha_elem"),
        "d": ("d_elem", "alpha_elem"),
        "alpha_bar": ("alpha_bar_elem", "hist_fat_elem"),
        "history": ("alpha_bar_elem", "hist_fat_elem"),
        "hist_fat": ("alpha_bar_elem", "hist_fat_elem"),
        "psi_active": ("psi_active_elem", "psi_plus_elem"),
        "active": ("psi_active_elem", "psi_plus_elem"),
        "psi": ("psi_raw_elem", "psi_elem", "psi_plus_elem"),
        "psi_raw": ("psi_raw_elem", "psi_elem", "psi_plus_elem"),
    }

    def __init__(self, fields_mat: Path | str, mesh_mat: Path | str | None = None):
        self.fields_mat = Path(fields_mat)
        if not self.fields_mat.is_file():
            raise FileNotFoundError(f"FEM fields .mat not found: {self.fields_mat}")
        mesh_path = Path(mesh_mat) if mesh_mat is not None else self.fields_mat.parent / "mesh_geometry.mat"
        self.mesh_mat = mesh_path if mesh_path.is_file() else None

        core_names = [
            "cycles", "d_elem", "alpha_elem", "alpha_bar_elem", "hist_fat_elem",
            "psi_plus_elem", "psi_active_elem", "psi_plus_peak_to_date_elem",
            "psi_raw_elem", "psi_elem", "element_centroids", "node_coords", "connectivity",
        ]
        data = _load_mat_any(self.fields_mat, variable_names=core_names)
        mesh = _load_mat_any(self.mesh_mat) if self.mesh_mat is not None else {}
        data = {**mesh, **data}

        if "cycles" in data:
            self.cycles = [int(round(x)) for x in np.asarray(data["cycles"]).ravel()]
        else:
            first = next(v for k, v in data.items() if k.endswith("_elem"))
            n_cycle = min(np.asarray(first).shape)
            self.cycles = list(range(1, n_cycle + 1))
        self._cycle_to_col = {c: i for i, c in enumerate(self.cycles)}

        if "element_centroids" in data:
            self.fem_centroids = _as_xy(data["element_centroids"])
        elif "node_coords" in data and "connectivity" in data:
            nodes = _as_xy(data["node_coords"])
            conn = np.asarray(data["connectivity"])
            if conn.shape[0] in (3, 4) and conn.shape[1] != conn.shape[0]:
                conn = conn.T
            conn = conn.astype(np.int64)
            if conn.min() == 1:
                conn = conn - 1
            self.fem_centroids = nodes[conn].mean(axis=1)
        else:
            raise ValueError(
                f"No element_centroids or node_coords/connectivity in {self.fields_mat}"
            )

        n_elem = int(self.fem_centroids.shape[0])
        self.fields: dict[str, np.ndarray] = {}
        for key, value in data.items():
            if key.endswith("_elem") or key in ("psi_elem",):
                arr = _as_elem_by_cycle(value, n_elem=n_elem)
                if arr.shape[0] == n_elem:
                    self.fields[key] = np.asarray(arr, dtype=np.float64)

        if "d_elem" in self.fields and "psi_plus_elem" in self.fields and "psi_raw_elem" not in self.fields:
            d = np.clip(self.fields["d_elem"], None, 1.0)
            g = np.maximum((1.0 - d) ** 2, 1e-12)
            self.fields["psi_raw_elem"] = self.fields["psi_plus_elem"] / g

    def available_targets(self) -> list[str]:
        out = []
        for target, names in self._FIELD_ALIASES.items():
            if any(name in self.fields for name in names):
                out.append(target)
        return sorted(set(out))

    def _field_name(self, target_kind: str) -> str:
        target_kind = str(target_kind).lower()
        for name in self._FIELD_ALIASES.get(target_kind, (target_kind,)):
            if name in self.fields:
                return name
        raise RuntimeError(
            f"FEM target {target_kind!r} unavailable in {self.fields_mat}. "
            f"Fields present: {sorted(self.fields)}"
        )

    def _bracket_cycles(self, cycle_idx: int) -> tuple[int, int]:
        if cycle_idx <= self.cycles[0]:
            return self.cycles[0], self.cycles[0]
        if cycle_idx >= self.cycles[-1]:
            return self.cycles[-1], self.cycles[-1]
        for i in range(len(self.cycles) - 1):
            if self.cycles[i] <= cycle_idx <= self.cycles[i + 1]:
                return self.cycles[i], self.cycles[i + 1]
        return self.cycles[0], self.cycles[0]

    def _field_at_cycle(self, field_name: str, cycle_idx: int) -> np.ndarray:
        field = self.fields[field_name]
        if cycle_idx in self._cycle_to_col:
            return field[:, self._cycle_to_col[cycle_idx]]
        c_lo, c_hi = self._bracket_cycles(cycle_idx)
        lo = field[:, self._cycle_to_col[c_lo]]
        if c_hi == c_lo:
            return lo
        hi = field[:, self._cycle_to_col[c_hi]]
        t = (cycle_idx - c_lo) / (c_hi - c_lo)
        return (1.0 - t) * lo + t * hi

    def _interpolate_to_pidl(self, fem_field: np.ndarray,
                             pidl_centroids: np.ndarray) -> np.ndarray:
        from scipy.spatial import cKDTree
        tree = cKDTree(self.fem_centroids)
        _, idx = tree.query(pidl_centroids, k=1)
        return np.asarray(fem_field, dtype=np.float64)[idx]

    def target_at_cycle(self, target_kind: str, cycle_idx: int,
                        pidl_centroids: np.ndarray,
                        *, device: torch.device | None = None,
                        dtype: torch.dtype = torch.float32) -> torch.Tensor:
        field_name = self._field_name(target_kind)
        field = self._field_at_cycle(field_name, cycle_idx)
        target = self._interpolate_to_pidl(field, pidl_centroids)
        out = torch.from_numpy(target).to(dtype=dtype)
        if device is not None:
            out = out.to(device)
        return out

    def field_supervised_loss(self, pred_per_elem: torch.Tensor,
                              target_kind: str,
                              cycle_idx: int,
                              pidl_centroids: np.ndarray,
                              lambda_sup: float = 1.0,
                              loss_kind: str = "mse_log",
                              mask: torch.Tensor | None = None) -> torch.Tensor:
        target = self.target_at_cycle(
            target_kind, cycle_idx, pidl_centroids,
            device=pred_per_elem.device, dtype=pred_per_elem.dtype)
        eps = 1e-12
        if loss_kind == "mse_lin":
            perel = (pred_per_elem - target) ** 2
        elif loss_kind == "mse_log":
            perel = (torch.log10(pred_per_elem.clamp(min=eps))
                   - torch.log10(target.clamp(min=eps))) ** 2
        elif loss_kind == "mse_rel":
            perel = ((pred_per_elem - target) / (target.abs() + eps)) ** 2
        else:
            raise ValueError(f"unknown loss_kind={loss_kind}")

        if mask is not None:
            mask_b = mask.to(perel.device).bool()
            return lambda_sup * (perel[mask_b].mean() if int(mask_b.sum()) else perel.new_zeros(()))
        return lambda_sup * perel.mean()
