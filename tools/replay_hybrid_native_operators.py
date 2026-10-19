"""Read-only full saved-field operator replay; never solves a new FEM state."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from damage_conditioned_equilibrium import equilibrium_internal_force
from hybrid_inputs import load_backend, read_manifest, sha256
from hybrid_history import AcceptedState


def replay(root):
    root = Path(root)
    started = perf_counter()
    backend, state0, _, _ = load_backend(root, read_manifest(root / "inputs.json"))
    rows = []
    for step in range(1, 6):
        tick = perf_counter()
        with np.load(root / f"seen_s{step}.npz", allow_pickle=False) as z:
            old = AcceptedState(z["u_old"], z["d_old"], z["A_old"], z["r_old"], z["f_old"],
                                z["opaque"], step-1, step-1, backend.mesh_id, backend.physics_id,
                                f"seen_pre_s{step}")
            psi, q = backend.trial(old, z["u"], z["d"])
            qp = backend.damage_problem(psi, q.fatigue, old)
            rd = qp.hessian @ z["d"] + qp.linear
            ru = equilibrium_internal_force(backend.kin, z["d"], z["u"], **backend.material)
            errors = dict(raw=float(np.max(np.abs(psi-z["psi"]) / np.maximum(1., np.abs(z["psi"])))),
                          force=float(np.max(np.abs(ru-z["native_ru"]))),
                          damage=float(np.max(np.abs(rd-z["native_rd"]))),
                          A=float(np.max(np.abs(q.accumulated-z["A"]))),
                          r=float(np.max(np.abs(q.driver-z["r"]))),
                          f=float(np.max(np.abs(q.fatigue-z["f"]))))
            rows.append(dict(step=step, errors=errors, passed=all(np.isfinite(v) and v <= 1.e-10
                                                               for v in errors.values()),
                             wall_seconds=perf_counter()-tick))
    return dict(schema="hybrid-native-operator-replay-v1", rows=rows,
                passed=all(r["passed"] for r in rows), tolerance=1.e-10,
                inputs_sha256=sha256(root / "inputs.json"), state0_id=state0.fingerprint(),
                total_wall_seconds=perf_counter()-started, new_fem_solves=0, training_updates=0,
                scope="known five c1 saved fields; coefficient/DOF/GP/accepted-base map parity only; no convergence/label promotion",
                source_identity="native saved MEX outputs and captured source/binary manifest; not live Fortran byte identity")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = replay(args.inputs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 2)
