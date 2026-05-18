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


# =============================================================================
# Sidecar S2 helpers — adaptive (cycle-wise) refinement
#
# S2a (tip_following): re-derive the tip-centred mask each cycle from current x_tip
# S2b (score_driven):  re-derive the mask from a detached per-element score
#
# Common machinery (refine_marked_elements + state remap) is shared with S1.
# =============================================================================


def refine_marked_elements(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    area: np.ndarray,
    refine_mask: np.ndarray,
    n_refine_passes: int = 1,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """1-to-4 red refinement of all triangles whose `refine_mask[i]` is True,
    plus 1-to-2 / 1-to-3 green closure of non-red neighbours that share split
    edges, so the resulting mesh remains edge-conforming.

    This is the same algorithm used inside `refine_mesh_at_tip`, hoisted so
    it can be re-driven by an arbitrary boolean mask (tip-radius, top-K
    score, etc.). Area is exactly preserved per parent element, so the
    quadrature integral ∫_Ω f dΩ ≈ Σ_e area_e · f(centroid_e) is invariant
    under refinement and the Deep Ritz / Carrara loss is untouched.

    Returns
    -------
    X_new, Y_new, T_new, area_new, parent_of_new, midpoint_parents

      - X_new, Y_new, T_new, area_new : refined mesh in parse_mesh conventions.
      - parent_of_new : (n_elem_new,) int. Each new triangle's parent in the
        pre-refinement T.
      - midpoint_parents : (n_midpoints, 2) int. For each NEW node (those with
        index ≥ n_old in X_new/Y_new), the two old-node indices that bracket
        the split edge. Old nodes (index < n_old) preserve their old indices
        in the new mesh, so the lineage map is sparse and stored only for
        newly-added midpoints. Used by `edge_lineage_transport` for L2-safe
        transfer of nodal irreversibility fields (hist_alpha).

    Note: lineage is currently exact for n_refine_passes == 1. For multi-pass,
    midpoint_parents tracks the latest split (parents may themselves be
    midpoints from an earlier pass); this is still correct for transport as
    long as values_old in `edge_lineage_transport` already reflects the
    inter-pass state.
    """
    X = np.asarray(X, dtype=np.float64).copy()
    Y = np.asarray(Y, dtype=np.float64).copy()
    T = np.asarray(T, dtype=np.int64).copy()
    area = np.asarray(area, dtype=np.float64).copy()
    refine_mask = np.asarray(refine_mask, dtype=bool).copy()

    parent = np.arange(T.shape[0], dtype=np.int64)  # identity for current mesh
    midpoint_parents_all: list = []   # (a, b) per new midpoint, accumulates across passes

    for _pass in range(int(n_refine_passes)):
        n_red = int(refine_mask.sum())
        if n_red == 0:
            break

        edge_mid: Dict[Tuple[int, int], int] = {}
        new_nodes_X: list = []
        new_nodes_Y: list = []
        pass_midpoint_parents: list = []
        next_node_id = X.shape[0]

        def _mid_node(a: int, b: int) -> int:
            nonlocal next_node_id
            key = (a, b) if a < b else (b, a)
            if key in edge_mid:
                return edge_mid[key]
            new_nodes_X.append(0.5 * (X[a] + X[b]))
            new_nodes_Y.append(0.5 * (Y[a] + Y[b]))
            pass_midpoint_parents.append((key[0], key[1]))
            edge_mid[key] = next_node_id
            next_node_id += 1
            return edge_mid[key]

        red_edges_split: Dict[Tuple[int, int], int] = {}
        new_tris: list = []
        new_parent: list = []

        for tri_idx in np.where(refine_mask)[0]:
            a, b, c = int(T[tri_idx, 0]), int(T[tri_idx, 1]), int(T[tri_idx, 2])
            m_ab = _mid_node(a, b)
            m_bc = _mid_node(b, c)
            m_ca = _mid_node(c, a)
            for (p, q, m) in ((a, b, m_ab), (b, c, m_bc), (c, a, m_ca)):
                key = (p, q) if p < q else (q, p)
                red_edges_split[key] = m
            par = parent[tri_idx]
            for tri in ((a, m_ab, m_ca), (m_ab, b, m_bc),
                        (m_ca, m_bc, c), (m_ab, m_bc, m_ca)):
                new_tris.append(tri)
                new_parent.append(par)

        for tri_idx in np.where(~refine_mask)[0]:
            a, b, c = int(T[tri_idx, 0]), int(T[tri_idx, 1]), int(T[tri_idx, 2])
            edges = (
                ((a, b) if a < b else (b, a), a, b, c),
                ((b, c) if b < c else (c, b), b, c, a),
                ((c, a) if c < a else (a, c), c, a, b),
            )
            split_edges = [(ek, e0, e1, eo) for (ek, e0, e1, eo) in edges if ek in red_edges_split]
            par = parent[tri_idx]
            if len(split_edges) == 0:
                new_tris.append((a, b, c))
                new_parent.append(par)
                continue
            if len(split_edges) == 1:
                ek, e0, e1, eo = split_edges[0]
                m = red_edges_split[ek]
                new_tris.append((e0, m, eo)); new_parent.append(par)
                new_tris.append((m, e1, eo)); new_parent.append(par)
                continue
            if len(split_edges) == 2:
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
                new_tris.append((sv, m_svL, m_svR));  new_parent.append(par)
                new_tris.append((m_svL, vL, vR));     new_parent.append(par)
                new_tris.append((m_svL, vR, m_svR));  new_parent.append(par)
                continue
            # 3 shared edges → full red split (rare).
            m_ab = red_edges_split[(a, b) if a < b else (b, a)]
            m_bc = red_edges_split[(b, c) if b < c else (c, b)]
            m_ca = red_edges_split[(c, a) if c < a else (a, c)]
            for tri in ((a, m_ab, m_ca), (m_ab, b, m_bc),
                        (m_ca, m_bc, c), (m_ab, m_bc, m_ca)):
                new_tris.append(tri); new_parent.append(par)

        if new_nodes_X:
            X = np.concatenate([X, np.asarray(new_nodes_X, dtype=np.float64)])
            Y = np.concatenate([Y, np.asarray(new_nodes_Y, dtype=np.float64)])
            midpoint_parents_all.extend(pass_midpoint_parents)
        T = np.asarray(new_tris, dtype=np.int64)
        area = _signed_area(X, Y, T)
        parent = np.asarray(new_parent, dtype=np.int64)
        # For subsequent passes, refine_mask must be re-derived by the caller;
        # we mark NO elements for the next pass by default (caller decides).
        refine_mask = np.zeros(T.shape[0], dtype=bool)

    midpoint_parents = (np.asarray(midpoint_parents_all, dtype=np.int64)
                        if midpoint_parents_all else
                        np.zeros((0, 2), dtype=np.int64))
    return X, Y, T, area, parent, midpoint_parents


def remap_element_field(values_old: np.ndarray, parent_new: np.ndarray) -> np.ndarray:
    """Carry a per-element field across a refinement step.

    Each new triangle inherits the value of its parent in the pre-refinement
    mesh. Because parents and children share centroid neighbourhoods (each
    child is geometrically contained in its parent), this is the natural
    element-wise transport: no interpolation drift, simple, deterministic.
    """
    return np.asarray(values_old)[np.asarray(parent_new, dtype=np.int64)]


def nearest_element_transport(
    values_old: np.ndarray,
    X_old: np.ndarray,
    Y_old: np.ndarray,
    T_old: np.ndarray,
    X_new: np.ndarray,
    Y_new: np.ndarray,
    T_new: np.ndarray,
) -> np.ndarray:
    """Transport a per-element field from one refined mesh to another via
    centroid-nearest-neighbour lookup (KDTree).

    Use case: sidecar S2 maintains the cumulative fatigue field hist_fat in
    REFINED-MESH coordinates throughout the run. When the refinement target
    changes (tip moved past hysteresis, or new top-K from score), a new
    refined mesh is built and hist_fat must be carried across.

    Why this beats aggregate-to-original + expand-from-original (the previous
    approach in sidecar_S2): cumulative quantities can have large sub-parent
    variation (the tip-side child of a refined parent accumulates ᾱ much
    faster than the back-side child). Aggregate-then-expand replaces every
    child with the parent's area-weighted MEAN — destroying exactly the
    sub-parent locality the refinement was meant to resolve. Centroid-nearest
    transport preserves sub-parent variation: each new-mesh element inherits
    the value of its geometrically closest old-mesh element, which for
    overlapping refined meshes (only the tip neighbourhood differs cycle to
    cycle) is almost always identity.

    Cost: O((n_old + n_new) log n_old) via scipy.spatial.cKDTree.
    """
    from scipy.spatial import cKDTree
    cx_old = (X_old[T_old[:, 0]] + X_old[T_old[:, 1]] + X_old[T_old[:, 2]]) / 3.0
    cy_old = (Y_old[T_old[:, 0]] + Y_old[T_old[:, 1]] + Y_old[T_old[:, 2]]) / 3.0
    cx_new = (X_new[T_new[:, 0]] + X_new[T_new[:, 1]] + X_new[T_new[:, 2]]) / 3.0
    cy_new = (Y_new[T_new[:, 0]] + Y_new[T_new[:, 1]] + Y_new[T_new[:, 2]]) / 3.0
    tree = cKDTree(np.column_stack((cx_old, cy_old)))
    _, idx = tree.query(np.column_stack((cx_new, cy_new)), k=1)
    return np.asarray(values_old, dtype=np.float64)[idx]


def edge_lineage_transport(
    values_old: np.ndarray,
    midpoint_parents: np.ndarray,
    n_old: int,
    reduce: str = "max",
) -> np.ndarray:
    """L2 conservative transport of a per-node field across 1-to-4 red
    refinement using edge lineage.

    Old node indices are preserved in the new mesh (indices 0..n_old-1), so
    they get exact copies of `values_old`. New midpoint nodes (indices
    n_old..n_old+M-1) each come from splitting an edge (a, b); the midpoint
    value is `reduce(values_old[a], values_old[b])` — defaults to `max` for
    irreversibility fields (hist_alpha) so the floor is never weaker than
    either endpoint.

    Parameters
    ----------
    values_old : (n_old,) per-node field on the pre-refinement mesh
    midpoint_parents : (M, 2) int array; row k = (a, b) for new node n_old+k
    n_old : number of old nodes (indices in the new mesh < n_old are
            inherited 1-to-1)
    reduce : "max" (default, conservative for irreversibility), "mean"
            (smoother), or "min" (weakest case).

    Returns
    -------
    values_new : (n_old + M,) per-node field on the refined mesh.

    Compared to nearest_node_transport: avoids the KDTree tie-break, which
    would arbitrarily pick one endpoint when the midpoint is exactly between
    two old nodes — and for hist_alpha that arbitrary choice can be
    `α=0` (resetting irreversibility floor) when the two endpoints are 1 and
    0. Edge-lineage with `max` reduction guarantees the conservative
    direction for any irreversibility field.
    """
    values_old = np.asarray(values_old, dtype=np.float64)
    mp = np.asarray(midpoint_parents, dtype=np.int64)
    n_old = int(n_old)
    M = int(mp.shape[0])
    out = np.empty(n_old + M, dtype=np.float64)
    out[:n_old] = values_old[:n_old]
    if M > 0:
        a_vals = values_old[mp[:, 0]]
        b_vals = values_old[mp[:, 1]]
        if reduce == "max":
            out[n_old:] = np.maximum(a_vals, b_vals)
        elif reduce == "min":
            out[n_old:] = np.minimum(a_vals, b_vals)
        elif reduce == "mean":
            out[n_old:] = 0.5 * (a_vals + b_vals)
        else:
            raise ValueError(f"unknown reduce: {reduce!r}")
    return out


def nearest_node_transport(
    values_old: np.ndarray,
    X_old: np.ndarray,
    Y_old: np.ndarray,
    X_new: np.ndarray,
    Y_new: np.ndarray,
) -> np.ndarray:
    """Transport a per-NODE field from one mesh to another via nearest-node
    KDTree lookup.

    Use case: sidecar S2 v3 maintains `hist_alpha` (per-node irreversibility
    floor) in the current refined-mesh's node coordinates. When the mesh
    changes (REFINE event), node-level `hist_alpha` is carried across without
    re-evaluating NN.fieldCalculation — preserves any built-up irreversibility
    that the NN-smooth-interpolation might or might not inherit.

    Two cases handled by the single KDTree:
      - new node = old node (preserved across refinement): distance = 0 →
        exact copy of value, identity transport.
      - new node = midpoint of an old edge (added by refinement): distance > 0
        → copy value of nearest old node (typically the closer of the two
        edge endpoints).

    Cost: O((n_old + n_new) log n_old) via scipy.spatial.cKDTree.
    """
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack((np.asarray(X_old, dtype=np.float64),
                                    np.asarray(Y_old, dtype=np.float64))))
    _, idx = tree.query(np.column_stack((np.asarray(X_new, dtype=np.float64),
                                          np.asarray(Y_new, dtype=np.float64))), k=1)
    return np.asarray(values_old, dtype=np.float64)[idx]


def aggregate_to_original(
    values_current: np.ndarray,
    area_current: np.ndarray,
    parent: np.ndarray,
    n_elem_orig: int,
) -> np.ndarray:
    """Inverse of `remap_element_field`: take a per-element field on the
    refined mesh and aggregate it back to the original mesh by area-weighted
    average over each parent's children.

    Identity:  expand(aggregate(v)) == v   IFF v is constant on each parent's
    child cluster. Otherwise the aggregation acts as a sub-grid smoother
    (loses sub-parent variation, preserves the area-weighted mean).

    Used by sidecar S2 to maintain hist_fat / psi_plus_prev / detached score
    in the **original** (un-refined) mesh's element coordinates across
    cycles, so that each cycle's refinement is a one-step transport from
    the canonical reference mesh rather than a compounding sequence of
    interpolations.
    """
    values_current = np.asarray(values_current, dtype=np.float64)
    area_current = np.asarray(area_current, dtype=np.float64)
    parent = np.asarray(parent, dtype=np.int64)
    weighted_sum = np.zeros(int(n_elem_orig), dtype=np.float64)
    area_sum = np.zeros(int(n_elem_orig), dtype=np.float64)
    np.add.at(weighted_sum, parent, values_current * area_current)
    np.add.at(area_sum, parent, area_current)
    # Guard against zero-area parents (shouldn't happen but kept for safety)
    area_sum = np.where(area_sum > 0, area_sum, 1.0)
    return weighted_sum / area_sum


def select_top_score_elements(
    score: np.ndarray,
    target_fraction: float = 0.07,
    min_count: int = 50,
) -> np.ndarray:
    """Return a boolean mask marking the top-`target_fraction` elements by
    `score`. Used by S2b (score-driven refinement).

    `target_fraction` controls the budget: e.g. 0.07 selects ~7% of elements,
    roughly comparable to the S1 static r=0.05 tip neighbourhood (6.80%) so
    S1/S2a/S2b have a similar refinement cost.

    `min_count` is a floor to avoid degenerate empty masks on small meshes.
    """
    score = np.asarray(score)
    n = score.shape[0]
    k = max(int(min_count), int(np.ceil(n * float(target_fraction))))
    if k >= n:
        return np.ones(n, dtype=bool)
    # argpartition is O(n)
    idx_top = np.argpartition(-score, k - 1)[:k]
    mask = np.zeros(n, dtype=bool)
    mask[idx_top] = True
    return mask


def adaptive_refine_for_cycle(
    X_orig: np.ndarray,
    Y_orig: np.ndarray,
    T_orig: np.ndarray,
    area_orig: np.ndarray,
    cfg: dict,
    tip_xy: Tuple[float, float] | None = None,
    score: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """Per-cycle adaptive refinement dispatcher for sidecar S2.

    Always operates on the ORIGINAL (un-refined) mesh — refinement is not
    cumulative across cycles. This keeps the mesh size bounded and the
    history transport one-step (no compounding remap error).

    Parameters
    ----------
    X_orig, Y_orig, T_orig, area_orig : the canonical parse_mesh output.
    cfg : sidecar_S2_dict. Required keys: 'mode', 'r_tip_sample',
          'n_refine_passes', 'tip_xy' (fallback for mode=tip_following if
          tip_xy arg is None), 'target_fraction' (for score_driven).
    tip_xy : current crack-tip position (used by S2a). If None, falls back
        to cfg['tip_xy'].
    score : per-element detached score for S2b. Required for mode='score_driven'.

    Returns
    -------
    X_new, Y_new, T_new, area_new, parent_new, summary : same as
        refine_marked_elements + a diagnostic summary dict.
    """
    mode = str(cfg.get("mode", "tip_following"))
    n_passes = int(cfg.get("n_refine_passes", 1))
    r_tip = float(cfg.get("r_tip_sample", 0.05))

    # Build the mask for the first pass.
    cx = (X_orig[T_orig[:, 0]] + X_orig[T_orig[:, 1]] + X_orig[T_orig[:, 2]]) / 3.0
    cy = (Y_orig[T_orig[:, 0]] + Y_orig[T_orig[:, 1]] + Y_orig[T_orig[:, 2]]) / 3.0

    if mode == "tip_following":
        if tip_xy is None:
            tip_xy = cfg.get("tip_xy", (0.0, 0.0))
        tx, ty = float(tip_xy[0]), float(tip_xy[1])
        refine_mask = (np.hypot(cx - tx, cy - ty) < r_tip)
        diag = {"mode": mode, "tip_xy": (tx, ty), "r_tip_sample": r_tip,
                "n_marked": int(refine_mask.sum())}
    elif mode == "score_driven":
        if score is None:
            # First cycle: no prior score available, fall back to tip-radius.
            tx, ty = float((tip_xy or cfg.get("tip_xy", (0.0, 0.0)))[0]), float((tip_xy or cfg.get("tip_xy", (0.0, 0.0)))[1])
            refine_mask = (np.hypot(cx - tx, cy - ty) < r_tip)
            diag = {"mode": mode, "fallback": "tip_radius (no prior score)",
                    "tip_xy": (tx, ty), "n_marked": int(refine_mask.sum())}
        else:
            target_frac = float(cfg.get("target_fraction", 0.07))
            min_count = int(cfg.get("min_count", 50))
            refine_mask = select_top_score_elements(score, target_frac, min_count)
            diag = {"mode": mode, "target_fraction": target_frac,
                    "n_marked": int(refine_mask.sum()),
                    "score_min": float(np.min(score)),
                    "score_max": float(np.max(score)),
                    "score_thr": float(np.min(score[refine_mask])) if refine_mask.any() else 0.0}
    else:
        raise ValueError(f"sidecar S2 unknown mode: {mode!r}")

    # Single-pass refinement (n_passes>1 would refine same-radius nested children;
    # for adaptive S2 we keep n_passes=1 since cycle-wise re-marking is the
    # adaptation mechanism — repeated passes within one cycle would just blow
    # up the mesh).
    X, Y, T, area, parent, midpoint_parents = refine_marked_elements(
        X_orig, Y_orig, T_orig, area_orig, refine_mask, n_refine_passes=1
    )
    for _ in range(max(0, n_passes - 1)):
        # Optional extra pass: re-derive the mask in the NEW mesh using the
        # same tip-radius criterion (S2a) or by inheriting the parent's mask
        # bit (S2b — children of refined parents are also refined).
        cx = (X[T[:, 0]] + X[T[:, 1]] + X[T[:, 2]]) / 3.0
        cy = (Y[T[:, 0]] + Y[T[:, 1]] + Y[T[:, 2]]) / 3.0
        if mode == "tip_following":
            mask2 = (np.hypot(cx - tx, cy - ty) < r_tip)
        else:
            mask2 = refine_mask[parent]  # propagate refinement bit to children
        X, Y, T, area, par2, mp2 = refine_marked_elements(X, Y, T, area, mask2, n_refine_passes=1)
        parent = parent[par2]
        # Multi-pass: append the new midpoints' parents. Note: these parents
        # may themselves be midpoints from the previous pass — the lineage
        # is still valid for edge_lineage_transport as long as `values_old`
        # already reflects the inter-pass state.
        if mp2.size:
            midpoint_parents = np.concatenate([midpoint_parents, mp2], axis=0)

    diag["n_elem_before"] = int(T_orig.shape[0])
    diag["n_elem_after"] = int(T.shape[0])
    diag["n_nodes_after"] = int(X.shape[0])
    diag["area_drift"] = float(abs(area.sum() - area_orig.sum()))
    diag["midpoint_parents"] = midpoint_parents
    diag["n_old_nodes"] = int(X_orig.shape[0])
    return X, Y, T, area, parent, diag


def apply_s2_swap_for_cycle(
    cfg: dict,
    X_orig: np.ndarray,
    Y_orig: np.ndarray,
    T_orig: np.ndarray,
    area_orig: np.ndarray,
    n_elem_orig: int,
    hist_fat_orig: np.ndarray,
    psi_plus_prev_orig: np.ndarray,
    s2_score_orig,
    tip_xy: Tuple[float, float],
    field_comp,
    device,
):
    """Per-cycle mesh swap for sidecar S2.

    Returns (inp, T_conn, area_T, hist_alpha, hist_fat, psi_plus_prev,
             n_elem, elem_centroids, right_bdy_mask, parent, diag).

    The caller is responsible for:
      - rebuilding the DataLoader (training_set) from the new `inp`
      - recomputing f_fatigue from the new hist_fat
      - calling aggregate_to_original at the end of the cycle to refresh
        hist_fat_orig / psi_plus_prev_orig / s2_score_orig for the next cycle
    """
    import torch  # local import — sidecar_sampling is otherwise torch-free

    X_new, Y_new, T_new, area_new, parent, diag = adaptive_refine_for_cycle(
        X_orig, Y_orig, T_orig, area_orig, cfg,
        tip_xy=tip_xy, score=s2_score_orig,
    )

    inp = torch.from_numpy(np.column_stack((X_new, Y_new))).to(torch.float).to(device)
    T_conn = torch.from_numpy(T_new).to(torch.long).to(device)
    area_T = torch.from_numpy(area_new).to(torch.float).to(device)
    n_elem = int(T_new.shape[0])

    cx = (X_new[T_new[:, 0]] + X_new[T_new[:, 1]] + X_new[T_new[:, 2]]) / 3.0
    cy = (Y_new[T_new[:, 0]] + Y_new[T_new[:, 1]] + Y_new[T_new[:, 2]]) / 3.0
    elem_centroids = torch.from_numpy(np.column_stack((cx, cy))).to(torch.float).to(device).detach()

    hist_fat = torch.from_numpy(remap_element_field(hist_fat_orig, parent)).to(torch.float).to(device)
    psi_plus_prev = torch.from_numpy(remap_element_field(psi_plus_prev_orig, parent)).to(torch.float).to(device)

    # Re-evaluate NN at the (possibly new) midpoint nodes so hist_alpha is
    # consistent with the current NN state. Detach: hist_alpha is a saved
    # snapshot, not part of any autograd graph this cycle.
    with torch.no_grad():
        _, _, alpha_new = field_comp.fieldCalculation(inp)
    hist_alpha = alpha_new.detach()

    right_bdy_mask = (inp[:, 0] > 0.48).detach()
    return (
        inp, T_conn, area_T, hist_alpha, hist_fat, psi_plus_prev,
        n_elem, elem_centroids, right_bdy_mask, parent, diag,
    )


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
