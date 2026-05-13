"""sidecar_sampling.py — true adaptive sampling sidecar (S1: static-tip oversampling).

Spec: docs/sidecar_true_adaptive_sampling.md (Stage S1).

Goal: change WHERE collocation points come from without touching the physical
energy functional. Refines the input triangular mesh near the crack tip via
1-to-4 red refinement; non-refined neighbours of refined elements get a
1-to-2 green closure split to keep the mesh edge-conforming.

This module operates on the (X, Y, T, area) tuple returned by
`utils.parse_mesh(..., gradient_type='numerical')` BEFORE the data is wrapped
into torch tensors. It returns a new (X', Y', T', area') of the same dtype.

Sidecar rules respected (see docs/sidecar_true_adaptive_sampling.md sec 5):
  1. Loss formula untouched — area conservation guarantees the energy integral
     is invariant under refinement (sum of child areas == parent area).
  2. No detached score here — S1 is a pure geometric prior.
  3. Geometry prior is explicit and reported via `summary` dict.
  4. Baseline comparison stack unchanged: only the mesh changes.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Dict


def _signed_area(X: np.ndarray, Y: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Same formula as utils.parse_mesh — keep the convention identical."""
    a = (
        X[T[:, 0]] * (Y[T[:, 1]] - Y[T[:, 2]])
        + X[T[:, 1]] * (Y[T[:, 2]] - Y[T[:, 0]])
        + X[T[:, 2]] * (Y[T[:, 0]] - Y[T[:, 1]])
    )
    return 0.5 * a


def _build_edge_to_tris(T: np.ndarray) -> Dict[Tuple[int, int], list]:
    e2t: Dict[Tuple[int, int], list] = {}
    for i, tri in enumerate(T):
        for (a, b) in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            key = (a, b) if a < b else (b, a)
            e2t.setdefault(key, []).append(i)
    return e2t


def refine_mesh_at_tip(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    area: np.ndarray,
    tip_xy: Tuple[float, float] = (0.0, 0.0),
    r_tip_sample: float = 0.05,
    n_refine_passes: int = 1,
    return_summary: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict]:
    """Refine triangles whose centroid lies within r_tip_sample of `tip_xy`.

    Algorithm (per pass):
      1. Mark every triangle with centroid distance < r_tip_sample as "red".
      2. For each red triangle, create midpoints on its three edges and split
         it into 4 sub-triangles (standard red refinement).
      3. For each green triangle that shares one or two edges with red
         triangles, split it via the midpoint(s) of those shared edges so
         that the resulting mesh is edge-conforming.
         - 1 shared edge  → 1-to-2 split
         - 2 shared edges → 1-to-3 split
         - 3 shared edges → 1-to-4 split (effectively also red)
      4. Append all new sub-triangles, drop the parents, rebuild area.

    Repeated `n_refine_passes` times so r_tip_sample stays a global radius
    (each pass uses the same radius; the same elements that were refined are
    not refined again because their centroids may move slightly, but in
    practice this concentrates density progressively as nested refinement.)

    Parameters
    ----------
    X, Y : (n_nodes,) float arrays — nodal coordinates.
    T    : (n_elem, 3) int array  — triangle node indices.
    area : (n_elem,) float array  — signed-area (matches parse_mesh).
    tip_xy : crack-tip location in domain coordinates.
    r_tip_sample : refinement radius (centroid distance).
    n_refine_passes : how many sequential refinement passes to apply.
        1 → ~4× density inside r_tip_sample.
        2 → ~16× density inside r_tip_sample (children of pass 1 may also be
            inside r_tip if centroids fall within radius).

    Returns
    -------
    X_new, Y_new, T_new, area_new : refined mesh in same conventions.
    summary : dict with diagnostic info (n_elem before/after, area sums,
        rho_tip before/after, etc.).
    """
    X = np.asarray(X, dtype=np.float64).copy()
    Y = np.asarray(Y, dtype=np.float64).copy()
    T = np.asarray(T, dtype=np.int64).copy()
    area = np.asarray(area, dtype=np.float64).copy()

    n_elem_orig = T.shape[0]
    area_total_orig = float(area.sum())

    tip_x, tip_y = float(tip_xy[0]), float(tip_xy[1])

    def _rho_tip(Xv: np.ndarray, Yv: np.ndarray, Tv: np.ndarray) -> float:
        cx = (Xv[Tv[:, 0]] + Xv[Tv[:, 1]] + Xv[Tv[:, 2]]) / 3.0
        cy = (Yv[Tv[:, 0]] + Yv[Tv[:, 1]] + Yv[Tv[:, 2]]) / 3.0
        r = np.hypot(cx - tip_x, cy - tip_y)
        return float((r < r_tip_sample).mean())

    rho_tip_orig = _rho_tip(X, Y, T)

    for _ in range(int(n_refine_passes)):
        cx = (X[T[:, 0]] + X[T[:, 1]] + X[T[:, 2]]) / 3.0
        cy = (Y[T[:, 0]] + Y[T[:, 1]] + Y[T[:, 2]]) / 3.0
        r = np.hypot(cx - tip_x, cy - tip_y)
        red_mask = r < r_tip_sample
        n_red = int(red_mask.sum())
        if n_red == 0:
            break

        # Edge -> midpoint cache (so adjacent reds / green-closure share midpoint nodes)
        edge_mid: Dict[Tuple[int, int], int] = {}
        new_nodes_X: list = []
        new_nodes_Y: list = []
        next_node_id = X.shape[0]

        def _mid_node(a: int, b: int) -> int:
            nonlocal next_node_id
            key = (a, b) if a < b else (b, a)
            if key in edge_mid:
                return edge_mid[key]
            new_nodes_X.append(0.5 * (X[a] + X[b]))
            new_nodes_Y.append(0.5 * (Y[a] + Y[b]))
            edge_mid[key] = next_node_id
            next_node_id += 1
            return edge_mid[key]

        # First pass: subdivide every RED triangle 1->4 and register its 3 edges.
        red_edges_split: Dict[Tuple[int, int], int] = {}
        new_tris: list = []

        for tri_idx in np.where(red_mask)[0]:
            a, b, c = int(T[tri_idx, 0]), int(T[tri_idx, 1]), int(T[tri_idx, 2])
            m_ab = _mid_node(a, b)
            m_bc = _mid_node(b, c)
            m_ca = _mid_node(c, a)
            # Mark the 3 edges as "split" so green-closure neighbours pick them up.
            for (p, q, m) in ((a, b, m_ab), (b, c, m_bc), (c, a, m_ca)):
                key = (p, q) if p < q else (q, p)
                red_edges_split[key] = m
            # 4 children — same orientation order as parent (a,b,c CCW or CW).
            new_tris.append((a, m_ab, m_ca))
            new_tris.append((m_ab, b, m_bc))
            new_tris.append((m_ca, m_bc, c))
            new_tris.append((m_ab, m_bc, m_ca))

        # Second pass: for each GREEN triangle that shares 1+ edges with a red,
        # split using those midpoints (green closure).
        green_handled: Dict[int, bool] = {}
        for tri_idx in np.where(~red_mask)[0]:
            a, b, c = int(T[tri_idx, 0]), int(T[tri_idx, 1]), int(T[tri_idx, 2])
            edges = (
                ((a, b) if a < b else (b, a), a, b, c),
                ((b, c) if b < c else (c, b), b, c, a),
                ((c, a) if c < a else (a, c), c, a, b),
            )
            split_edges = [(ek, e0, e1, eo) for (ek, e0, e1, eo) in edges if ek in red_edges_split]

            if len(split_edges) == 0:
                # Wholly green and untouched — keep parent triangle.
                new_tris.append((a, b, c))
                continue
            if len(split_edges) == 1:
                ek, e0, e1, eo = split_edges[0]
                m = red_edges_split[ek]
                new_tris.append((e0, m, eo))
                new_tris.append((m, e1, eo))
                green_handled[tri_idx] = True
                continue
            if len(split_edges) == 2:
                # 1-to-3 split. Find the shared vertex (touching both split
                # edges), then rotate (a,b,c) -> (sv, vL, vR) preserving CCW
                # so child triangles inherit the parent's orientation.
                v_counts: Dict[int, int] = {a: 0, b: 0, c: 0}
                for (ek, e0, e1, eo) in split_edges:
                    v_counts[e0] += 1
                    v_counts[e1] += 1
                shared_v = max(v_counts, key=lambda k: v_counts[k])
                if shared_v == a:
                    sv, vL, vR = a, b, c
                elif shared_v == b:
                    sv, vL, vR = b, c, a
                else:
                    sv, vL, vR = c, a, b
                m_svL = red_edges_split[(sv, vL) if sv < vL else (vL, sv)]
                m_svR = red_edges_split[(sv, vR) if sv < vR else (vR, sv)]
                # 3 CCW children:
                new_tris.append((sv, m_svL, m_svR))
                new_tris.append((m_svL, vL, vR))
                new_tris.append((m_svL, vR, m_svR))
                green_handled[tri_idx] = True
                continue
            # 3 shared edges → full red split (rare; happens when neighbour is
            # surrounded by reds).
            a, b, c = int(T[tri_idx, 0]), int(T[tri_idx, 1]), int(T[tri_idx, 2])
            m_ab = red_edges_split[(a, b) if a < b else (b, a)]
            m_bc = red_edges_split[(b, c) if b < c else (c, b)]
            m_ca = red_edges_split[(c, a) if c < a else (a, c)]
            new_tris.append((a, m_ab, m_ca))
            new_tris.append((m_ab, b, m_bc))
            new_tris.append((m_ca, m_bc, c))
            new_tris.append((m_ab, m_bc, m_ca))
            green_handled[tri_idx] = True

        # Append the new midpoint nodes and rebuild arrays.
        if new_nodes_X:
            X = np.concatenate([X, np.asarray(new_nodes_X, dtype=np.float64)])
            Y = np.concatenate([Y, np.asarray(new_nodes_Y, dtype=np.float64)])
        T = np.asarray(new_tris, dtype=np.int64)
        area = _signed_area(X, Y, T)

    rho_tip_new = _rho_tip(X, Y, T)
    area_total_new = float(area.sum())

    summary = {
        "n_elem_before": int(n_elem_orig),
        "n_elem_after": int(T.shape[0]),
        "n_nodes_after": int(X.shape[0]),
        "rho_tip_before": rho_tip_orig,
        "rho_tip_after": rho_tip_new,
        "area_total_before": area_total_orig,
        "area_total_after": area_total_new,
        "area_drift": abs(area_total_new - area_total_orig),
        "r_tip_sample": float(r_tip_sample),
        "n_refine_passes": int(n_refine_passes),
        "tip_xy": (tip_x, tip_y),
    }

    if return_summary:
        return X, Y, T, area, summary
    return X, Y, T, area, {}




def maybe_refine_for_sidecar(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    area: np.ndarray,
    cfg: dict | None,
    label: str = "",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Hook helper. If cfg is None or cfg['enable'] is False, return inputs
    unchanged. Otherwise apply refine_mesh_at_tip and print a one-line report.
    """
    if cfg is None or not cfg.get("enable", False):
        return X, Y, T, area

    X2, Y2, T2, area2, summary = refine_mesh_at_tip(
        X, Y, T, area,
        tip_xy=cfg.get("tip_xy", (0.0, 0.0)),
        r_tip_sample=cfg.get("r_tip_sample", 0.05),
        n_refine_passes=cfg.get("n_refine_passes", 1),
    )
    print(
        f"[sidecar-S1{(' ' + label) if label else ''}] mesh refined: "
        f"elem {summary['n_elem_before']} -> {summary['n_elem_after']}  "
        f"rho_tip(r<{summary['r_tip_sample']:.3f}) "
        f"{summary['rho_tip_before']*100:.2f}% -> {summary['rho_tip_after']*100:.2f}%  "
        f"area_drift={summary['area_drift']:.2e}"
    )
    return X2, Y2, T2, area2
