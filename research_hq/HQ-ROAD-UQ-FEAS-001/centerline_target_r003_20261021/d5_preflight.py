"""Zero-step producer admission for the reviewed D5 package."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

import d5_runner as runner
from centerline_core import centreline_metrics, soft_centreline_field


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--approval", required=True); parser.add_argument("--lock", required=True)
    parser.add_argument("--trainzip", required=True); parser.add_argument("--valzip", required=True)
    parser.add_argument("--cfd", required=True); parser.add_argument("--gapszip", required=True); parser.add_argument("--weights", required=True)
    parser.add_argument("--d1-checkpoint", required=True); parser.add_argument("--d2-checkpoint", required=True)
    parser.add_argument("--d3-old-cfd-csv", required=True); parser.add_argument("--d3-old-gaps-csv", required=True)
    parser.add_argument("--d3-repair-cfd-csv", required=True); parser.add_argument("--d3-repair-gaps-csv", required=True)
    parser.add_argument("--cache", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); approval = json.loads(Path(args.approval).read_text()); lock = json.loads(Path(args.lock).read_text())
    runner.approval_gate(approval, args.lock, args)
    identities = {}
    for key in ("trainzip", "valzip", "gapszip", "weights", "d1_checkpoint", "d2_checkpoint",
                "d3_old_cfd_csv", "d3_old_gaps_csv", "d3_repair_cfd_csv", "d3_repair_gaps_csv"):
        path = Path(getattr(args, key)); identities[key] = {"bytes": path.stat().st_size, "sha256": runner.sha256(path)}
        if identities[key] != {name: lock[key][name] for name in ("bytes", "sha256")}:
            raise RuntimeError(f"identity mismatch {key}")
    if runner.base.cfd_lock(Path(args.cfd)) != lock["cfd_lock"]: raise RuntimeError("CFD identity mismatch")
    cache = Path(args.cache); runner.extract_verified(args.trainzip, cache / "train"); runner.extract_verified(args.valzip, cache / "val")
    train = runner.base.crack_pairs(cache / "train", "traincrop", set(runner.base.PROTOCOL["crack500_excluded_train_parents"]))
    val = runner.base.crack_pairs(cache / "val", "valcrop", set(runner.base.PROTOCOL["crack500_excluded_val_parents"]))
    cfd = runner.base.cfd_pairs(Path(args.cfd)); gaps = runner.d2.gaps_pairs(args.gapszip)
    gaps_nonempty = sum(bool(runner.d2.load_gaps(row)[1].any()) for row in gaps)
    counts = {"train_pairs":len(train),"train_groups":len({r['group'] for r in train}),"val_pairs":len(val),
              "val_groups":len({r['group'] for r in val}),"cfd_labeled":len(cfd),
              "gaps_labeled":len(gaps),"gaps_nonempty":gaps_nonempty,"gaps_empty":len(gaps)-gaps_nonempty}
    if counts != runner.PROTOCOL["expected"]: raise RuntimeError(f"inventory mismatch {counts}")
    _, mask = runner.base.load_crack(train[0]); field = soft_centreline_field(mask)
    if not (field.shape == mask.shape and np.isfinite(field).all() and field.min() >= 0 and field.max() <= 1): raise RuntimeError("target transform invalid")
    synthetic = centreline_metrics(field, mask)
    device = torch.device("cuda:0")
    candidate = runner.ResNet18UNet(args.weights).to(device).eval()
    with torch.no_grad(): logits, features = candidate(torch.zeros((1,3,65,99), device=device), return_feature=True)
    if tuple(logits.shape) != (1,1,65,99) or tuple(features.shape) != (1,512): raise RuntimeError("candidate forward contract")
    d1_model = runner.base.UNet().to(device); d1_model.load_state_dict(torch.load(args.d1_checkpoint,map_location=device,weights_only=True)["model"])
    d2_model = runner.ResNet18UNet().to(device); d2_model.load_state_dict(torch.load(args.d2_checkpoint,map_location=device,weights_only=True)["model"])
    receipt = {"status":"PASS_ZERO_STEP_PREFLIGHT","run_id":approval["run_id"],"hostname":runner.socket.gethostname(),
               "gpu":runner.os.environ.get("CUDA_VISIBLE_DEVICES"),"environment":runner.environment(),"code_snapshot":runner.snapshot(),
               "data_lock_sha256":runner.sha256(args.lock),"identities":identities,"counts":counts,
               "launch_identity":runner.os.environ.get("HQ_RUN_LAUNCH_ID"),
               "task_dependency_path":approval["task_dependency_path"],
               "thread_environment":{key:runner.os.environ.get(key) for key in approval["thread_environment"]},
               "synthetic_metrics":synthetic,"training_steps":0,"optimizer_steps":0,"road420_access":False}
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__": main()
