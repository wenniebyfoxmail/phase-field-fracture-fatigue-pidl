"""Convert exactly the known c1 archive. No solve, training or holdout scan."""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np

from hybrid_inputs import (sha256, blocked_to_interleaved, native_dofs_to_canonical,
                           state_from_native_group)
from hybrid_incremental import NativeQ4Backend
from hybrid_transaction import StateStore
from native_q4_damage_qp import build_native_q4_kinematics
from damage_conditioned_equilibrium import sens_displacement_boundary_conditions


def prepare(archive, out):
    archive, out = Path(archive), Path(out)
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    base = archive / "retrieved/output/c1_commit"
    native_manifest = json.loads((archive / "retrieved/input_manifest.json").read_text())
    material = dict(youngs_modulus=1., poisson_ratio=.3, gc=.01, length_scale=.01,
                    alpha_t=.5, power=2., thickness=1.)
    source_hashes = {"common_initial.mat": sha256(base / "common_initial.mat"),
                     "input_manifest.json": sha256(archive / "retrieved/input_manifest.json")}
    with h5py.File(base / "common_initial.mat") as f:
        points, cells = np.asarray(f["node_coords"]).T, np.asarray(f["connectivity"]).T.astype(np.int32) - 1
        fd = np.asarray(f["free_dof_d"]).ravel().astype(int) - 1
        fu = np.asarray(f["free_dof_u"]).ravel().astype(int) - 1
        crack = np.ones(len(points), bool)
        crack[fd] = False
        kin = build_native_q4_kinematics(points, cells)
        backend = NativeQ4Backend(kin, crack, **material)
        state = state_from_native_group(f["common"], backend, version=0, load_index=0,
                                        load_id="state0_prescribed_recovered_unloaded")
        if (len(points) != 86756 or len(cells) != 86408 or crack.sum() != 251
                or not np.array_equal(state.damage, np.asarray(f["common/lower"]).ravel())
                or np.any(state.displacement != 0) or np.any(state.accumulated != 0)
                or np.any(state.driver != 0) or np.any(state.fatigue != 1)):
            raise RuntimeError("known common state0 contract differs; no implicit repair")
        dofs, unit_values = sens_displacement_boundary_conditions(points, 1.)
        native_fixed = np.setdiff1d(np.arange(2 * len(points)), fu)
        if not np.array_equal(np.sort(native_dofs_to_canonical(native_fixed, len(points))), dofs):
            raise RuntimeError("native/canonical boundary free DOFs differ after permutation")
    np.savez_compressed(out / "mesh.npz", points=points, cells=cells, crack=crack,
                        bc_dofs=dofs, bc_unit_values=unit_values)
    StateStore(out / "state0.npz").initialize(state)
    for step, load in enumerate([.02999988, .05999988, .08999988, .11999988, 0.], 1):
        path = base / f"repaired/s{step}/accepted_commit.mat"
        source_hashes[f"repaired/s{step}/accepted_commit.mat"] = sha256(path)
        with h5py.File(path) as f:
            old = state_from_native_group(f["pre"], backend, version=step-1, load_index=step-1,
                                          load_id=f"seen_c1_pre_s{step}")
            new = state_from_native_group(f["proposed"], backend, version=step, load_index=step,
                                          load_id=f"seen_c1_s{step}")
            if np.max(np.abs(new.displacement[dofs] - load * unit_values)) > 1.e-12:
                raise RuntimeError("seen loaded boundary mismatch after permutation")
            values = dict(u_old=old.displacement, d_old=old.damage, A_old=old.accumulated,
                          r_old=old.driver, f_old=old.fatigue, opaque=old.opaque,
                          u=new.displacement, d=new.damage, A=new.accumulated, r=new.driver,
                          f=new.fatigue, psi=np.asarray(f["candidate/raw"]).T,
                          native_ru=blocked_to_interleaved(np.asarray(f["proof/ru"]).ravel()),
                          native_rd=np.asarray(f["proof/rd"]).ravel(), load=np.array(load))
            np.savez_compressed(out / f"seen_s{step}.npz", **values)
    manifest = dict(schema="hybrid-native-inputs-v1", native_source_commit=native_manifest["source_commit"],
                    native_source_checks=native_manifest["source_checks"],
                    native_binary_checks=native_manifest["binary_checks"],
                    source_hashes=source_hashes, material=material, mesh_id=backend.mesh_id,
                    physics_id=backend.physics_id, state0_id=state.fingerprint(),
                    state0_role="prescribed admissible recovered initial condition, not a learned label",
                    displacement_layout="interleaved; native blocked explicitly permuted",
                    gp_order="(+,+),(-,+),(+,-),(-,-)",
                    seen_candidates=5, qualified_labels=0,
                    assets={x.name: sha256(x) for x in sorted(out.glob("*.npz"))})
    (out / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seen-c1-archive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.seen_c1_archive, args.out)
    print(json.dumps({k: result[k] for k in ("mesh_id", "physics_id", "state0_id", "qualified_labels")}, indent=2))
