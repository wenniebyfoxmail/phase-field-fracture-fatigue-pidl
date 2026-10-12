#!/usr/bin/env python3
"""Separate prepare / producer-fit / held-response validation for E014.

No fit path opens stage9 response. Real fit must run on Taobo after review.
This is normalized fixed-state elasticity, not fatigue/phase-field evolution.
"""
import argparse
import hashlib
import json
import socket
import sys
import time
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from aa2024_triplet_structure import inspect, parse_nodemap, read_member
from aa2024_patch_mechanics import rectangular_mesh, candidate_basis, solve_patch, sample_regular_mesh
from aa2024_rigid_observable import quotient_residual


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):
            h.update(b)
    return h.hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False))


def require_completion(root, mode, artifacts):
    """Reject failed/partial stages before consuming their output or held data."""
    receipt_path=root/"execution_receipt.json"
    if not receipt_path.is_file():
        raise ValueError("missing completion receipt")
    receipt=json.loads(receipt_path.read_text())
    if receipt.get("mode")!=mode or receipt.get("execution_status")!="succeeded":
        raise ValueError("unsuccessful or wrong-mode completion receipt")
    if receipt.get("runner_sha256")!=digest(__file__):
        raise ValueError("completion receipt runner mismatch")
    hashes=receipt.get("artifacts_sha256",{})
    for name in artifacts:
        if not (root/name).is_file() or hashes.get(name)!=digest(root/name):
            raise ValueError("completion receipt artifact mismatch")
    return receipt


def vector_error(residual, weights):
    return float(np.sum(weights*np.linalg.norm(residual,axis=1))/weights.sum())


def prepare(archive, output):
    structural = inspect(archive)
    with zipfile.ZipFile(archive) as z:
        a,b = [parse_nodemap(read_member(z,f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{s}.txt"),allow_displacements=True) for s in (7,8)]
        connections = read_member(z,"global_3d_dic/Connections/global_3d_dic_results_1_7_connections.txt")
        # Freeze bytes only, without converting any held displacement/strain.
        high_sha = hashlib.sha256(read_member(z,"global_3d_dic/Nodemaps/global_3d_dic_results_1_9.txt").encode("utf-8")).hexdigest()
    ids = a["ids"]
    if not np.array_equal(ids,b["ids"]) or not np.array_equal(ids,np.arange(1,len(ids)+1)):
        raise ValueError("unexpected frozen facet numbering")
    fit = a["finite_xyz"]&b["finite_xyz"]&a["finite_u"]&b["finite_u"]
    xy = a["xyz"][:,:2]
    v = b["u"][:,:2]-a["u"][:,:2]
    rows = [[int(x.strip()) for x in l.split(";")] for l in connections.splitlines()[1:] if l.strip()]
    rows = np.asarray(rows,dtype=int)
    if np.any(rows[:,0]!=3):
        raise ValueError("area-weight construction requires connection Type3")
    tri = rows[:,2:]
    tri = tri[np.all(tri>=0,axis=1)]
    if np.any(tri>=len(ids)):
        raise ValueError("connection index out of range")
    tri = tri[np.all(fit[tri],axis=1)]
    p = xy[tri]
    areas = np.abs((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]))*.5
    if np.any(areas<=1e-12):
        raise ValueError("training geometry degenerate")
    weights = np.bincount(tri.ravel(),weights=np.repeat(areas/3,3),minlength=len(ids))
    interior = fit&(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)&(weights>0)
    if interior.sum()<10:
        raise ValueError("insufficient fit interior")
    mesh, elements, bd = rectangular_mesh()
    dist, nearest = cKDTree(xy[fit]).query(mesh[bd],k=4)
    if np.any(dist[:,3]>2.):
        raise ValueError("training-only boundary interpolation support exceeds2mm")
    bc = []
    finite_xy,finite_v = xy[fit],v[fit]
    for point,idx in zip(mesh[bd],nearest):
        local = finite_xy[idx]-point
        A = np.c_[np.ones(4),local]
        coeff,_,rank,_ = np.linalg.lstsq(A,finite_v[idx],rcond=1e-12)
        if rank != 3:
            raise ValueError("boundary affine interpolation rank")
        bc.append(coeff[0])
    d0,basis = candidate_basis(mesh)
    forces = [float(structural["stages"][str(s)]["headers"]["force"]) for s in (7,8,9)]
    alpha = (forces[2]-forces[0])/(forces[1]-forces[0])
    np.savez_compressed(output/"prepared.npz",mesh=mesh,tri=elements,boundary=bd,
        bc=np.array(bc),d0=d0,basis=basis,obs_xy=xy[interior],ids=ids[interior],
        weights=weights[interior],train_v=v[interior],u7=a["u"][interior,:2],alpha=alpha)
    dump(output/"preparation.json",{
        "status":"prepared_training_only_no_FEM_solve","source_archive":str(archive),
        "archive_identity":structural["archive_identity"],"cycles":"126873.5",
        "stages_fit":[7,8],"response_holdout":9,"forces":forces,
        "prepared_sha256":digest(output/"prepared.npz"),"mesh_nodes":len(mesh),
        "held_member_sha256":high_sha,"held_force":forces[2],
        "triangles":len(elements),"boundary_nodes":int(bd.sum()),
        "interior_observations":int(interior.sum()),
        "boundary_farthest_fourth_neighbor_mm":float(dist[:,3].max()),
        "BC":"four_training_neighbors_affine_LS_reproduces_rigid_and_affine",
        "basis":"training-derived_prior_NOT_measured_true_crack",
        "nu":.3,"E":1,"q_grid":np.linspace(0,.95,21).tolist()})


def fit(prepared_root, output):
    require_completion(prepared_root,"prepare",("preparation.json","prepared.npz"))
    meta = json.loads((prepared_root/"preparation.json").read_text())
    if digest(prepared_root/"prepared.npz") != meta["prepared_sha256"]:
        raise ValueError("prepared lock mismatch")
    with np.load(prepared_root/"prepared.npz",allow_pickle=False) as src:
        a = {k:src[k] for k in src.files}
    if len(a["mesh"])>2000 or len(a["ids"])!=len(set(a["ids"].tolist())):
        raise ValueError("asset budget/identity")
    profiles,fields = [],[]
    for q in np.linspace(0,.95,21):
        d = a["d0"]+(1-a["d0"])*q*a["basis"]
        u,residual = solve_patch(a["mesh"],a["tri"],a["boundary"],a["bc"],d)
        sampled = sample_regular_mesh(u,a["obs_xy"])
        # One global quotient, never a separate crack-side alignment.
        r = quotient_residual(a["obs_xy"],sampled-a["train_v"],a["weights"])
        profiles.append({"q":float(q),"train_vector_MAE_mm":vector_error(r,a["weights"]),"solver_relative_residual":residual})
        fields.append(sampled)
    sensitivity = max(vector_error(quotient_residual(a["obs_xy"],u-fields[0],a["weights"]),a["weights"]) for u in fields)
    dump(output/"q_profile.json",{"profile":profiles,"response_span_mm":sensitivity,
        "meaning":"numerical_conditional_sensitivity_NOT_noise-qualified_physical_identifiability"})
    if sensitivity<=1e-10:
        raise ValueError("q response numerically invisible; no held-response access")
    # Deterministic first minimum = lowest q for EXACT computed ties; no retuning.
    selected = min(range(21),key=lambda i:profiles[i]["train_vector_MAE_mm"])
    intact,_ = solve_patch(a["mesh"],a["tri"],a["boundary"],a["bc"],np.zeros(len(a["mesh"])))
    alpha = float(a["alpha"])
    np.savez_compressed(output/"frozen_predictions.npz",ids=a["ids"],xy=a["obs_xy"],
        weights=a["weights"],u7=a["u7"],candidate=alpha*fields[selected],
        secant=alpha*a["train_v"],intact=alpha*sample_regular_mesh(intact,a["obs_xy"]),
        d0_only=alpha*fields[0])
    dump(output/"fit.json",{"status":"frozen_before_high_response_access",
        "prepared_sha256":meta["prepared_sha256"],"q":profiles[selected]["q"],
        "held_member_sha256":meta["held_member_sha256"],"held_force":meta["held_force"],
        "response_span_mm":sensitivity,"prediction_sha256":digest(output/"frozen_predictions.npz"),
        "scope":"one_fixed_basis_static_conditional_patch_NOT_material_or_fatigue_recovery"})


def validate(fit_root, high_member, output):
    require_completion(fit_root,"fit",("fit.json","frozen_predictions.npz","q_profile.json"))
    meta = json.loads((fit_root/"fit.json").read_text())
    if meta["status"]!="frozen_before_high_response_access" or digest(fit_root/"frozen_predictions.npz")!=meta["prediction_sha256"]:
        raise ValueError("prediction freeze mismatch")
    if high_member.stat().st_size>16_000_000:
        raise ValueError("high member size cap")
    if digest(high_member)!=meta["held_member_sha256"]:
        raise ValueError("held external member identity mismatch")
    high = parse_nodemap(high_member.read_text(),allow_displacements=True)
    if high["headers"].get("current_stage_index")!="9" or high["headers"].get("reference_stage_index")!="1" or high["headers"].get("cycles")!="126873.5":
        raise ValueError("held-state identity")
    if float(high["headers"]["force"])!=meta["held_force"]:
        raise ValueError("held force mismatch")
    with np.load(fit_root/"frozen_predictions.npz",allow_pickle=False) as src:
        a={k:src[k] for k in src.files}
    lookup={int(v):i for i,v in enumerate(high["ids"])}
    if any(int(v) not in lookup for v in a["ids"]):
        raise ValueError("held facet identity missing")
    index=np.array([lookup[int(v)] for v in a["ids"]])
    valid=np.isfinite(high["xyz"][index,:2]).all(1)&np.isfinite(high["u"][index,:2]).all(1)
    if valid.sum()<10 or not np.allclose(high["xyz"][index[valid],:2],a["xy"][valid],atol=1e-6,rtol=0):
        raise ValueError("held reference/support mismatch")
    target=high["u"][index[valid],:2]-a["u7"][valid]
    xy,w=a["xy"][valid],a["weights"][valid]
    metrics={};residuals={}
    for name in ("candidate","secant","intact","d0_only"):
        r=quotient_residual(xy,a[name][valid]-target,w)
        residuals[name]=r
        metrics[name]=vector_error(r,w)
    dump(output/"metrics.json",{"q":meta["q"],"vector_MAE_mm":metrics,
        "primary_candidate_minus_secant_mm":metrics["candidate"]-metrics["secant"],
        "eligible":int(valid.sum()),"frozen_support":len(valid),"missing":int((~valid).sum()),
        "area_coverage":float(w.sum()/a["weights"].sum()),
        "estimand":"global_planar_rigid_quotient_displacement_increment",
        "scope":"single_cycle_conditional_diagnostic_no_physical_identification_or_future_skill"})
    np.savez_compressed(output/"validation_fields.npz",xy=xy,weights=w,target=target,
        **{k:a[k][valid] for k in residuals},**{k+"_residual":v for k,v in residuals.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","fit","validate"))
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--high-member",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-commit",required=True)
    p.add_argument("--run-id",required=True)
    args=p.parse_args()
    if args.mode=="fit" and socket.gethostname()!="GPUServer8":
        raise ValueError("real-data fit restricted to declared Taobo producer")
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.time()
    receipt={"run_id":args.run_id,"mode":args.mode,"hostname":socket.gethostname(),
             "source_commit_declared":args.source_commit,"runner_sha256":digest(__file__),
             "command":sys.argv,"start_utc":datetime.now(timezone.utc).isoformat(),
             "input":str(args.input),"execution_status":"running"}
    receipt["dependencies_sha256"]={p:digest(Path(__file__).with_name(p)) for p in
        ("aa2024_triplet_structure.py","aa2024_patch_mechanics.py","aa2024_rigid_observable.py")}
    receipt["numpy_version"]=np.__version__
    receipt["pid"]=os.getpid()
    receipt["thread_environment"]={k:os.environ.get(k) for k in
        ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")}
    try:
        if args.mode=="prepare":prepare(args.input,args.output)
        elif args.mode=="fit":fit(args.input,args.output)
        else:
            if args.high_member is None:raise ValueError("held member required")
            validate(args.input,args.high_member,args.output)
        receipt["execution_status"]="succeeded"
    except Exception as exc:
        receipt["execution_status"]="failed"
        receipt["error"]=str(exc)
        raise
    finally:
        expected={"prepare":("prepared.npz","preparation.json"),
                  "fit":("frozen_predictions.npz","fit.json","q_profile.json"),
                  "validate":("metrics.json","validation_fields.npz")}[args.mode]
        receipt["artifacts_sha256"]={name:digest(args.output/name) for name in expected if (args.output/name).is_file()}
        receipt["elapsed_seconds"]=time.time()-started
        receipt["end_utc"]=datetime.now(timezone.utc).isoformat()
        dump(args.output/"execution_receipt.json",receipt)


if __name__=="__main__":main()
