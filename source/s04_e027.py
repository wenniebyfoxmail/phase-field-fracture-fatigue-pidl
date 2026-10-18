"""S04-E027 fixed-state preparation and three-arm definitions; no import-time IO.

Import by adding this repository's source/ to sys.path, rather than importing
source.__init__, which imports historical training entry points.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import torch

from network import NeuralNet
from q4_quadrature import q4_shape_data, q4_gradient, q4_interpolate
from compute_energy import strain_energy_with_split
from material_properties import MaterialProperties
from pff_model import PFFModel

PROTOCOL = "S04-E027/v1-source-faithful-P-20261018"
US = .11999988


def finite(x, name):
    if not bool(torch.isfinite(x).all()):
        raise ValueError(f"nonfinite {name}")
    return x


def read_mat(path, group, key, axes=None):
    with h5py.File(path, "r") as h:
        a = np.asarray(h[f"{group}/{key}" if group else key])
    return a.transpose(axes).copy() if axes is not None else a.reshape(-1).copy()


def verify_payload(root, row):
    relative = Path(row["relative"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("payload path escape")
    p = root / relative
    if p.resolve() != root.resolve() / relative or p.is_symlink():
        raise ValueError("linked payload")
    if p.stat().st_size != row["bytes"]:
        raise ValueError("payload size")
    digest = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(b)
    if digest.hexdigest() != row["sha256"]:
        raise ValueError("payload identity")
    return p


def load_reference(root: Path, lock: dict):
    """Read exactly four allowlisted files, never discover adjacent states."""
    if lock["protocol"] != PROTOCOL:
        raise ValueError("protocol mismatch")
    expected = {"mesh": "inputs/common_common_initial.mat",
                "predecessor": "inputs/c0020_s003_post_commit.mat",
                "case": "output/mcs/c20_s4/case.mat",
                "reference": "output/mcs/c20_s4/outer_18.mat"}
    if set(lock["payloads"]) != set(expected):
        raise ValueError("payload roles")
    if any(lock["payloads"][k]["relative"] != v for k, v in expected.items()):
        raise ValueError("payload allowlist")
    paths = {k: verify_payload(root, v) for k, v in lock["payloads"].items()}
    xy = read_mat(paths["mesh"], "", "node_coords", (1, 0))
    conn_raw = read_mat(paths["mesh"], "", "connectivity", (1, 0))
    if not np.equal(conn_raw, np.floor(conn_raw)).all():
        raise ValueError("noninteger connectivity")
    conn = conn_raw.astype(np.int64) - 1
    n = len(xy)
    if xy.shape != (86756, 2) or conn.shape != (86408, 4):
        raise ValueError("native geometry shape")
    if conn.min() < 0 or conn.max() >= n:
        raise ValueError("connectivity range")
    fu_raw = read_mat(paths["mesh"], "", "free_dof_u")
    fd_raw = read_mat(paths["mesh"], "", "free_dof_d")
    for raw, size in ((fu_raw, 2*n), (fd_raw, n)):
        if not np.equal(raw, np.floor(raw)).all() or len(np.unique(raw)) != len(raw):
            raise ValueError("DOF integer/uniqueness")
        if raw.min() < 1 or raw.max() > size:
            raise ValueError("DOF range")
    u = read_mat(paths["reference"], "point", "u")
    d = read_mat(paths["reference"], "point", "d")
    prev = read_mat(paths["case"], "pre", "lower")
    history = read_mat(paths["case"], "pre", "history", (2, 1, 0))
    prior_d = read_mat(paths["predecessor"], "request28_snapshot", "d_node")
    prior_h = read_mat(paths["predecessor"], "request28_snapshot", "history_vars_old", (2, 1, 0))
    prior_xy = read_mat(paths["predecessor"], "request28_snapshot", "node_coords", (1, 0))
    prior_conn = read_mat(paths["predecessor"], "request28_snapshot", "connectivity", (1, 0))
    for a, b in ((prev, prior_d), (history, prior_h), (xy, prior_xy), (conn_raw, prior_conn)):
        if not np.array_equal(a, b):
            raise ValueError("immutable predecessor identity")
    for key, expected in (("cycle", 20), ("substep", 3), ("history_committed", 1), ("damage_committed", 1)):
        if read_mat(paths["predecessor"], "request28_snapshot", key).item() != expected:
            raise ValueError("predecessor timing")
    for key, expected in (("outer", 18), ("policy_pass", 1)):
        if read_mat(paths["reference"], "point", key).item() != expected:
            raise ValueError("reference endpoint")
    controls = "point/controls"
    for key, expected in (("physical_cycle", 20), ("substep", 4)):
        if read_mat(paths["reference"], controls, key).item() != expected:
            raise ValueError("reference timing")
    if abs(read_mat(paths["reference"], controls, "target_u").item() - US) > 1e-14:
        raise ValueError("reference load")
    h234 = read_mat(paths["reference"], "point", "history234", (2, 1, 0))
    raw = read_mat(paths["reference"], "point", "raw", (1, 0))
    ru = read_mat(paths["reference"], "point", "ru")
    if (u.shape != (2*n,) or d.shape != (n,) or prev.shape != (n,)
            or history.shape != (86408, 4, 4) or h234.shape != (86408, 4, 3)
            or raw.shape != (86408, 4) or ru.shape != (2*n,)):
        raise ValueError("state shape")
    if np.any(d < prev-1e-12) or np.any(d > 1+1e-12) or np.any(prev < -1e-12):
        raise ValueError("reference feasibility")
    fixed_d = np.setdiff1d(np.arange(n), fd_raw.astype(np.int64)-1)
    if not np.array_equal(d[fixed_d], prior_d[fixed_d]):
        raise ValueError("prescribed damage identity")
    f = h234[:, :, 2]
    if np.any(f <= 0) or np.any(f > 1):
        raise ValueError("trial f bounds")
    arrays = dict(xy=xy, conn=conn, free_u=fu_raw.astype(np.int64)-1,
                  free_d=fd_raw.astype(np.int64)-1,
                  ref=np.column_stack((u[:n], u[n:], d)), previous=prev,
                  history=history, trial_history234=h234, f=f, ref_raw=raw, ref_force=ru)
    if not all(np.isfinite(a).all() for a in arrays.values()):
        raise ValueError("nonfinite payload")
    return arrays


class Problem:
    def __init__(self, arrays, device="cpu"):
        t = lambda a: torch.as_tensor(a, dtype=torch.float64, device=device)
        self.xy = t(arrays["xy"])
        self.conn = torch.as_tensor(arrays["conn"], dtype=torch.long, device=device)
        self.ref, self.previous, self.f = map(t, (arrays["ref"], arrays["previous"], arrays["f"]))
        self.free = torch.as_tensor(arrays["free_u"], dtype=torch.long, device=device)
        free_d = torch.as_tensor(arrays["free_d"], dtype=torch.long, device=device)
        self.fixed_d = torch.ones(len(self.xy), dtype=torch.bool, device=device)
        self.fixed_d[free_d] = False
        self.N, self.B, self.w = q4_shape_data(self.xy, self.conn)
        self.mass = torch.zeros(len(self.xy), dtype=torch.float64, device=device)
        for j in range(4):
            self.mass.scatter_add_(0, self.conn[:, j], (self.w*self.N[:, j]).sum(1))
        gp = torch.einsum("gn,enx->egx", self.N, self.xy[self.conn])
        z = lambda x: (x[..., 0] >= 0) & (x[..., 0] <= .5) & (x[..., 1].abs() <= .03)
        self.zone, self.gp_zone = z(self.xy), z(gp)
        if not self.zone.any() or not self.gp_zone.any() or (self.mass <= 0).any():
            raise ValueError("empty support/nonpositive mass")
        self.mat = MaterialProperties(1., .3, 1., .01)
        self.pff = PFFModel("AT1", "volumetric", .005, residual_stiffness=0.)
        self.old_gp = q4_interpolate(self.previous, self.conn, self.N)

    def parts(self, u, v, d):
        gu, gv, gd = (q4_gradient(q, self.conn, self.B) for q in (u, v, d))
        dg = q4_interpolate(d, self.conn, self.N)
        elastic, raw = strain_energy_with_split(gu[:, :, 0], gv[:, :, 1],
                        .5*(gu[:, :, 1]+gv[:, :, 0]), dg, self.mat, self.pff)
        damage = self.f*.375*(dg+.0001*gd.square().sum(2))
        irrev = .5*16875*torch.relu(self.old_gp-dg).square()
        return (self.w*elastic).sum(), (self.w*damage).sum(), (self.w*irrev).sum(), raw, raw*(1-dg).square()

    def force(self, fields, create_graph=False):
        u, v, d = fields.unbind(1)
        energy = self.parts(u, v, d)[0]
        gu, gv = torch.autograd.grad(energy, (u, v), create_graph=create_graph)
        return torch.cat((gu, gv))

    def sample(self, generator):
        global_ids = torch.multinomial(self.mass.cpu(), 2048, True, generator=generator)
        local_ids = torch.multinomial((self.mass*self.zone).cpu(), 2048, True, generator=generator)
        return global_ids.to(self.xy.device), local_ids.to(self.xy.device)

    def supervised(self, fields, ids):
        # Sampling probabilities already include mass; do not multiply mass again.
        lu, ld = self.supervised_components(fields, ids)
        return lu+ld

    def supervised_components(self, fields, ids):
        # Each support has probability mass 1/2; ids already use mass sampling.
        eu, ed = [], []
        for q in ids:
            e = fields[q]-self.ref[q]
            eu.append(e[:, :2].square().sum(1).mean()/US**2)
            ed.append(e[:, 2].square().mean())
        return .5*(eu[0]+eu[1]), .5*(ed[0]+ed[1])

    def score(self, fields):
        q = fields.detach().clone().requires_grad_(True)
        force = self.force(q).detach()
        with torch.no_grad():
            predicted = self.parts(*q.unbind(1))
            reference = self.parts(*self.ref.unbind(1))
            w = self.w[self.gp_zone]
            err = predicted[4][self.gp_zone]-reference[4][self.gp_zone]
            abs_rmse = torch.sqrt((w*err.square()).sum()/w.sum())
            ref_rms = torch.sqrt((w*reference[4][self.gp_zone].square()).sum()/w.sum())
            out = dict(active_RMSE=float(abs_rmse), active_ref_RMS=float(ref_rms),
                       active_error=float(abs_rmse/ref_rms) if ref_rms > 1e-12 else None,
                       free_force=float(torch.linalg.vector_norm(force[self.free])),
                       d_min=float(q[:, 2].min()), d_max=float(q[:, 2].max()),
                       healing=float(torch.relu(self.previous-q[:, 2]).max()),
                       top_reaction=float(force[len(q):][self.xy[:, 1] == .5].sum()),
                       upper_violation=float(torch.relu(q[:, 2]-1).max()),
                       notch_error=float((q[self.fixed_d, 2]-self.ref[self.fixed_d, 2]).abs().max()) if self.fixed_d.any() else 0.)
            for name, mask in (("global", torch.ones_like(self.zone)), ("zone", self.zone)):
                m = self.mass[mask]; e = q[mask]-self.ref[mask]
                out[f"{name}_uv_RMS_Us"] = float(torch.sqrt((m*e[:, :2].square().sum(1)).sum()/m.sum())/US)
                out[f"{name}_d_RMS"] = float(torch.sqrt((m*e[:, 2].square()).sum()/m.sum()))
            for name, mask in (("global", torch.ones_like(self.gp_zone)), ("zone", self.gp_zone)):
                ww = self.w[mask]
                for j, channel in ((3, "raw"), (4, "active")):
                    delta = predicted[j][mask]-reference[j][mask]
                    out[f"{name}_{channel}_RMSE"] = float(torch.sqrt((ww*delta.square()).sum()/ww.sum()))
            for v in out.values():
                if v is not None and not np.isfinite(v):
                    raise ValueError("nonfinite score")
            return out


def fields(model, xy):
    """Source-faithful default FieldComputation; no spatial feature transform."""
    raw = model(xy)
    y = xy[:, 1]
    bubble = (y+.5)*(.5-y)
    r = raw[:, 2]
    damage = torch.where(r > 2, .001*(r-2)+1,
                        torch.where(r < -2, .001*(r+2), r/4+.5))
    return torch.stack((US*bubble*raw[:, 0], US*(bubble*raw[:, 1]+y+.5), damage), 1)


def make_model(state, device="cpu"):
    model = NeuralNet(2, 3, 8, 400, "TrainableReLU", 1.).double().to(device)
    model.load_state_dict(state, strict=True)
    for p in model.parameters():
        finite(p, "initial model")
    return model


def physical_loss(problem, prediction, model):
    e = sum(problem.parts(*prediction.unbind(1))[:3])
    finite(e, "energy")
    if e <= 0:
        raise ValueError("nonpositive physical energy; no log floor")
    reg = sum(p.square().sum() for name, p in model.named_parameters() if "weight" in name)
    return torch.log10(e)+1e-5*reg


def mechanical_loss(problem, prediction, normalizer):
    if not np.isfinite(normalizer) or normalizer <= 1e-12:
        raise ValueError("mechanical normalization unavailable")
    r = problem.force(prediction, create_graph=True)[problem.free]
    return r.square().sum()/normalizer**2


def clone_branch(model, optimizer, generator):
    result = copy.deepcopy(model)
    opt = torch.optim.Adam(result.parameters(), lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0)
    opt.load_state_dict(copy.deepcopy(optimizer.state_dict()))
    rng = torch.Generator().set_state(generator.get_state().clone())
    return result, opt, rng


def decision(scores):
    a, b = scores["C"]["active_error"], scores["S"]["active_error"]
    if a is None or b is None or b <= 1e-12:
        return dict(R_active=None, status="NA", conclusion="report absolute components")
    if not np.isfinite(a) or not np.isfinite(b) or a < 0 or b < 0:
        raise ValueError("invalid active score")
    r = a/b
    return dict(R_active=r, status="DIRECTIONAL_SIGNAL" if r < 1-1e-8 else
                "NUMERICAL_TIE" if r <= 1+1e-8 else "NO_DIRECTIONAL_GAIN",
                conclusion="single-state synthetic component; inspect costs separately")


def prepare(root, lock):
    arrays = load_reference(Path(root), lock)
    p = Problem(arrays)
    ref = p.ref.detach().clone().requires_grad_(True)
    force = p.force(ref).detach().numpy()
    err = float(np.max(np.abs(force-arrays["ref_force"])))
    free = float(np.linalg.norm(force[arrays["free_u"]]))
    with torch.no_grad():
        parts = p.parts(*p.ref.unbind(1))
        raw = parts[3].numpy()
        active = parts[4].numpy()
    alpha = arrays["history"][:, :, 1]+np.maximum(active-arrays["history"][:, :, 2], 0)
    expected_f = np.minimum(1, (1/(alpha+.5))**2)
    expected_history = np.stack((alpha, active, expected_f), axis=2)
    trial_gap = float(np.max(np.abs(expected_history-arrays["trial_history234"])/np.maximum(1, np.abs(arrays["trial_history234"]))))
    if trial_gap > 1e-10:
        raise ValueError("fresh trial history/f identity")
    raw_gap = float(np.max(np.abs(raw-arrays["ref_raw"])/np.maximum(1, np.abs(arrays["ref_raw"]))))
    fixed = np.setdiff1d(np.arange(2*len(p.xy)), arrays["free_u"])
    n = len(p.xy)
    expected = np.zeros(2*n)
    expected[n+np.flatnonzero(arrays["xy"][:, 1] == .5)] = US
    bc = float(np.max(np.abs(np.r_[arrays["ref"][:, 0], arrays["ref"][:, 1]][fixed]-expected[fixed])))
    if err > 1e-10 or free > 1e-8 or raw_gap > 1e-10 or bc > 1e-12:
        raise ValueError(f"reference replay mismatch: {err=}, {free=}, {raw_gap=}, {bc=}")
    return dict(protocol=PROTOCOL, execution="NONTRAINING_REFERENCE_CHECK_ONLY",
                optimizer_steps=0, history_commits=0, reference_force_maxabs=err,
                reference_free_force=free, reference_raw_maxscaled=raw_gap, trial_history_maxscaled=trial_gap, reference_BC=bc,
                nodes=n, elements=len(p.conn), init_status="UNRESOLVED_NOT_READ")
