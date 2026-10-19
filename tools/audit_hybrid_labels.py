"""Read ONLY known, already-seen c1 repaired archive; no FEM/label creation.

Reports source-domain candidates separately from certified new-backend labels.
This is a bounded inventory, not a claim to have searched remote/held-out data.
"""
import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def array_id(*values):
    h = hashlib.sha256()
    for a in values:
        a = np.ascontiguousarray(a)
        h.update(str((a.shape, a.dtype)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def audit_c1(root):
    run = Path(root) / "local_archive/experiments/S04-E011/runs/pf_s04e011_c1_commit_20261016_v4_r1"
    arm = run / "retrieved/output/c1_commit/repaired"
    rows, prior = [], None
    for step in range(1, 6):
        path = arm / f"s{step}/accepted_commit.mat"
        with h5py.File(path) as f:
            d, u = f["candidate/d"][()].ravel(), f["candidate/u"][()].ravel()
            old = f["pre/d"][()].ravel()
            old_u = f["pre/u"][()].ravel()
            lower = f["proof/lower"][()].ravel()
            h_old, h_new = f["pre/history"][()], f["proposed/history"][()]
            g = f["proof/rd"][()].ravel()
            residual = g.copy()
            lo, hi, fixed = d <= lower + 1.e-10, d >= 1 - 1.e-10, lower == 1
            residual[lo & (g > 0)] = 0.
            residual[hi & (g < 0)] = 0.
            residual[fixed] = 0.
            old_id, new_id = array_id(old_u, old, h_old), array_id(u, d, h_new)
            # h5py reverses MATLAB dimensions: channel, GP, element.
            expected_A = h_old[1] + np.maximum(h_new[2] - h_old[2], 0.)
            finite = all(np.isfinite(a).all() for a in (d,u,old,lower,h_old,h_new,g))
            rows.append(dict(step=step, source=str(path),
                             selected_array_sha256=array_id(old_u,old,h_old,u,d,h_new,lower,g),
                             predecessor_id=old_id, state_id=new_id,
                             adjacent_chain_matches=(prior is None or old_id == prior),
                             finite=bool(finite), lower_equals_predecessor=bool(np.array_equal(lower,old)),
                             nodal_min=float(d.min()), nodal_max=float(d.max()),
                             retreat_inf=float(np.maximum(old-d,0.).max()),
                             saved_fresh_feasible_gradient_inf=float(np.max(np.abs(residual))),
                             unit_scale_projected_inf=float(np.max(np.abs(d-np.clip(d-g,lower,1.)))),
                             fatigue_map_A_error_inf=float(np.max(np.abs(h_new[1]-expected_A))),
                             accepted_f_min=float(h_new[3].min()), accepted_f_max=float(h_new[3].max()),
                             native_precommit_joint_pass=bool(f["proof/joint_pass"][()].item()),
                             pre_version=int(f["event/pre_version"][()].item()),
                             post_version=int(f["event/post_version"][()].item()),
                             certified_new_backend_label=False))
            prior = new_id
    return dict(schema="hybrid-existing-label-audit-v1", scope="five known seen c1 repaired transitions only",
                project_data_reads="candidate/pre/proof/proposed fields in these five files; no heldout/remote scan",
                training=False, new_fem=False, source_domain_candidates=5,
                certified_new_backend_labels=0, independent_complete_trajectories=1,
                fatigue_degraded_accepted_transitions=0, rows=rows,
                reasons=[
                    "Repaired native archive already has nodal lower/box/hard-line and fresh precommit; do not reject it as merely soft FEM.",
                    "Four loaded transitions exceed current 1e-7 unit-scale engineering KKT default; old native 4e-6 L2 acceptance remains valid for its original contract.",
                    "Unloading transition has zero feasible damage residual, but inherits an uncertified predecessor under the new acceptance contract.",
                    "No new-backend operator/state/settings/model-input-predictor attestation exists for these labels; no silent recertification or projection.",
                    "All five accepted f=1; one c1 sequence cannot supply disjoint whole-trajectory train/validation/test or fatigue-feedback coverage.",
                ])


def qualify_transition(record, *, physics_id, mesh_id, settings_id):
    """Fail closed on a prospective label manifest, without opening arrays.

    Array/hash/operator equivalence checks must first be attested by the
    authorized producer/reviewer. This validates the metadata contract only.
    """
    reasons = []
    for key, expected in (("physics_id", physics_id), ("mesh_id", mesh_id),
                          ("settings_id", settings_id), ("domain", "nodal-K-v1")):
        if record.get(key) != expected:
            reasons.append(key)
    for key in ("input_accepted_verified", "output_joint_verified", "trial_map_verified",
                "array_hashes_verified", "features_origin_verified", "original_operator_verified"):
        if record.get(key) is not True:
            reasons.append(key)
    for key in ("trajectory_id", "predecessor_id", "state_id", "certificate_sha256",
                "input_predictor_sha256", "label_sha256"):
        if not isinstance(record.get(key), str) or not record[key]:
            reasons.append(key)
    a, b = record.get("load_index_in"), record.get("load_index_out")
    if type(a) is not int or type(b) is not int or a < 0 or b != a + 1:
        reasons.append("consecutive_load_index")
    return {"metadata_eligible": not reasons, "missing_or_mismatched": reasons,
            "array_qualification_performed_here": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = audit_c1(args.project_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("source_domain_candidates", "certified_new_backend_labels",
                                            "independent_complete_trajectories")}, indent=2))
