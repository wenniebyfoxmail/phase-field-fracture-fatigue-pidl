"""Read-only endpoint diagnostics: no optimiser, fitting or parameter updates."""
import argparse
import copy
import csv
import json
import resource
import sys
from pathlib import Path

import numpy as np
import torch

from run_s04_e019_frozen_residual_screen import (
    validate_reference, admit_backbone, predict_in_chunks, anchor_component_geometry, US, sha256,
)
from s04_e019_frozen_residual import build_model, state_digest
from s04_e018_global_local import compact_window
from s04_e020_delayed_decay import CONTROL_LOCKS, check_pair_identity, region_values
from aggregate_s04_e020_delayed_decay import validate_schedule_and_pair

REGIONS = ("damage", "background", "background_inside")
CAP = 2 * 1024**3


def rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    value = int(value if sys.platform == "darwin" else value * 1024)
    if value >= CAP:
        raise MemoryError(f"diagnostic RSS cap exceeded: {value}")
    return value


def gradient_summary(named, ga, gb):
    result = []
    groups = {"all": list(range(len(named)))}
    for i, (name, _) in enumerate(named):
        groups.setdefault(name.rsplit(".", 1)[0], []).append(i)
    for name, indices in groups.items():
        a = sum(float(torch.sum(ga[i]**2)) for i in indices)
        b = sum(float(torch.sum(gb[i]**2)) for i in indices)
        dot = sum(float(torch.sum(ga[i] * gb[i])) for i in indices)
        result.append(dict(group=name, damage_norm=a**.5, background_norm=b**.5,
            total_norm=max(0., a+b+2*dot)**.5,
            cosine=None if min(a,b) <= 1e-60 else dot/(a*b)**.5))
    return result


def stream_measure(model, data, base, chunk=1024):
    """Full nodal pass; regional gradients are contributions to the original loss."""
    before = state_digest(model)
    named = list(model.residual.named_parameters())
    params = [p for _, p in named]
    grad = [[torch.zeros_like(p) for p in params] for _ in range(2)]
    layers = [model.residual.input_layer, *model.residual.hidden_layers]
    nlayer = len(layers)
    width = model.residual.output_layer.in_features
    w = data["mass"] / data["mass"].sum()
    all_damage = data["damage"] > .1
    xy_np = data["xy"]
    inside = np.all((xy_np > model.lower.numpy()-.02) & (xy_np < model.upper.numpy()+.02), axis=1)
    masks = [all_damage, ~all_damage, ~all_damage & inside]
    pmass = [float(w[m].sum()) for m in masks]
    stats = [[dict(pos=np.zeros(width), raw_pos=np.zeros(width), raw_neg=np.zeros(width), mean=np.zeros(width), second=np.zeros(width),
                   ever=np.zeros(width, dtype=bool)) for _ in masks] for _ in layers]
    gram = [np.zeros((width+1, width+1)) for _ in masks]
    loss = np.zeros(2)
    max_uv_diff = 0.
    grad_identity_error = 0.
    for start in range(0, len(w), chunk):
        stop = min(start+chunk, len(w))
        xy = torch.tensor(xy_np[start:stop], dtype=torch.float64)
        z = (xy-model.center)/model.scale
        factor = ((xy[:,1]+.5)*(.5-xy[:,1]))[:,None] * compact_window(xy, model.lower, model.upper)
        acts, preacts = [], []
        for layer, activation in zip(layers, model.residual.activations):
            pre = layer(z); preacts.append(pre)
            z = activation(pre); acts.append(z)
        predicted = torch.tensor(base[start:stop]) + factor*model.residual.output_layer(z)
        target = torch.tensor(data["equilibrated_uv"][start:stop])
        sq = torch.sum((predicted-target)**2, dim=1) / abs(US)**2
        wt = torch.tensor(w[start:stop])
        active = torch.tensor(all_damage[start:stop])
        pieces = [(wt*sq*active).sum(), (wt*sq*(~active)).sum()]
        gd = torch.autograd.grad(pieces[0], params, retain_graph=True)
        gb = torch.autograd.grad(pieces[1], params, retain_graph=start == 0)
        if start == 0:
            full = torch.autograd.grad(sum(pieces), params)
            grad_identity_error = max(float(torch.max(torch.abs(a+b-f))) for a,b,f in zip(gd,gb,full))
            for a,b,f in zip(gd,gb,full):
                torch.testing.assert_close(a+b, f, rtol=1e-9, atol=1e-14)
        for r, g in enumerate((gd, gb)):
            for dest, source in zip(grad[r], g): dest.add_(source)
            loss[r] += float(pieces[r].detach())
        with torch.no_grad():
            expected = torch.tensor(base[start:stop])+model.correction_physical(xy)
            max_uv_diff = max(max_uv_diff, float(torch.max(torch.abs(predicted-expected))))
            features = (factor * torch.cat((z, torch.ones_like(factor)), dim=1)).detach().numpy()
            for r, mask in enumerate(masks):
                selected = mask[start:stop]
                weights = w[start:stop]*selected
                gram[r] += features.T @ (weights[:,None]*features)
                for li, act in enumerate(acts):
                    a = act.detach().numpy()
                    raw = preacts[li].detach().numpy()
                    stats[li][r]["pos"] += weights @ (a>0)
                    stats[li][r]["raw_pos"] += weights @ (raw>0)
                    stats[li][r]["raw_neg"] += weights @ (raw<0)
                    stats[li][r]["mean"] += weights @ a
                    stats[li][r]["second"] += weights @ (a*a)
                    if selected.any(): stats[li][r]["ever"] |= (a[selected]>0).any(axis=0)
        rss()
        del acts, preacts, predicted, expected, sq, pieces, gd, gb, z
    assert state_digest(model) == before, "diagnostic changed model parameters/buffers"
    assert all(p.grad is None for p in model.parameters()), "unexpected .grad mutation"
    activation_rows, spectrum = [], []
    for li in range(nlayer):
        coeff = float(model.residual.activations[li].coeff.detach())
        for r, name in enumerate(REGIONS):
            s = stats[li][r]
            mean = s["mean"] / pmass[r]
            std = np.sqrt(np.maximum(0, s["second"]/pmass[r]-mean**2))
            activation_rows.append(dict(layer=li, region=name, coeff=coeff,
                mean_active_fraction=float(np.mean(s["pos"]/pmass[r])),
                raw_positive_fraction=float(np.mean(s["raw_pos"]/pmass[r])),
                raw_negative_fraction=float(np.mean(s["raw_neg"]/pmass[r])),
                dead_units=int((~s["ever"]).sum()), width=width,
                near_constant_units=int((std <= 1e-12*max(1.,float(np.max(np.abs(mean))))).sum()),
                rms_activation=float(np.sqrt(np.sum(s["second"])/pmass[r]/width))))
    for r, name in enumerate(REGIONS):
        matrix = gram[r]/pmass[r]
        eigen = np.linalg.eigvalsh((matrix+matrix.T)/2)[::-1]
        positive = np.maximum(eigen, 0)
        total = positive.sum(); probs = positive/total if total>0 else positive
        nz = probs>0
        spectrum.append(dict(region=name, trace=float(total),
            min_raw_eigenvalue=float(eigen.min()), eigenvalues=eigen.tolist(),
            entropy_rank=float(np.exp(-np.sum(probs[nz]*np.log(probs[nz])))) if total>0 else 0.,
            participation_rank=float(total**2/np.sum(positive**2)) if total>0 else 0.,
            rank_relative_1e_12=int(np.sum(positive > positive[0]*1e-12)) if total>0 else 0,
            rank_relative_1e_8=int(np.sum(positive > positive[0]*1e-8)) if total>0 else 0,
            top_fraction=float(probs[0]) if total>0 else None))
    return dict(activations=activation_rows, spectrum=spectrum,
        gradients=gradient_summary(named, *grad), loss_damage=float(loss[0]),
        loss_background=float(loss[1]), full_rms=float(np.sqrt(loss.sum())),
        formula_max_abs_difference=max_uv_diff, first_chunk_gradient_additivity_max_error=grad_identity_error,
        parameter_buffer_digest_unchanged=before, peak_rss_bytes=rss())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.set_default_dtype(torch.float64)
    results = []
    for state, lock in CONTROL_LOCKS.items():
        data = validate_reference(state, args.old/"inputs"/f"{state}.npz")
        backbone, base, _ = admit_backbone(state, args.old/"backbones"/state, data)
        geometry = anchor_component_geometry(data["xy"], data["damage"], data["conn"], data["mass"])
        for label in ("initial_reconstruction", "E019", "E020"):
            model = build_model(7, "localized", geometry, copy.deepcopy(backbone))
            check_pair_identity(state, geometry, state_digest(model.backbone), state_digest(model.residual))
            asset = dict(reference_sha256=data["reference_sha256"], initial_reconstruction=label=="initial_reconstruction")
            if label != "initial_reconstruction":
                path = args.old/"runs"/lock["run_id"] if label == "E019" else next((args.new/"runs").glob(f"*-{state}-localized-s7"))
                record = json.loads((path/"metrics.json").read_text())
                if label == "E019":
                    for name, digest in lock["files"].items(): assert sha256(path/name) == digest
                else: validate_schedule_and_pair(path/"metrics.json")
                assert sha256(path/"final_step_10000.pt") == record["checkpoint_sha256"]
                checkpoint = torch.load(path/"final_step_10000.pt", map_location="cpu", weights_only=True)
                model.load_state_dict(checkpoint["model_state_dict"], strict=True)
                assert state_digest(model.backbone) == lock["backbone_digest"]
                for name in ("lower", "upper", "center", "scale"):
                    torch.testing.assert_close(getattr(model,name),torch.tensor(geometry[name]),rtol=0,atol=0)
                saved = np.load(path/"prediction.npz")["uv"]
                asset.update(checkpoint_sha256=sha256(path/"final_step_10000.pt"), run_id=path.name)
            else: saved = base
            model.eval()
            predicted = predict_in_chunks(model, torch.tensor(data["xy"])).numpy()
            np.testing.assert_allclose(predicted,saved,rtol=0,atol=1e-12)
            regions = region_values(data,predicted)
            saved_regions = region_values(data,saved)
            for key in regions: np.testing.assert_allclose(regions[key],saved_regions[key],rtol=0,atol=1e-14)
            result = stream_measure(model,data,base)
            np.testing.assert_allclose(result["full_rms"],regions["full"],rtol=0,atol=1e-14)
            result.update(state=state, arm=label, assets=asset, regions=regions,
                prediction_max_abs_difference=float(np.max(np.abs(predicted-saved))))
            results.append(result)
            (args.out/f"{state}_{label}.json").write_text(json.dumps(result,indent=2))
            print(json.dumps(dict(state=state,arm=label,full=regions["full"],grad_all=result["gradients"][0],
                last_damage=next(s for s in result["spectrum"] if s["region"]=="damage"),peak_rss_bytes=rss())),flush=True)
            del model, predicted
        del backbone,data
    (args.out/"summary.json").write_text(json.dumps(dict(training=False,parameter_updates=0,
        scope="exploratory endpoint diagnostic; not a full Jacobian/NTK or causal training-path proof",
        peak_rss_bytes=rss(),chunk=1024,results=results),indent=2))


if __name__ == "__main__":
    main()
