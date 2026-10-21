"""Frozen scale-normalised centreline target and evaluation operations."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, label
from skimage.morphology import skeletonize

SHORT_SIDE = 512
HALF_VALUE_RADIUS = 2.0
CUTOFF_RADIUS = 8.0
TOLERANCES = (1, 2, 4)


def _shape_at_short_side(shape, short_side=SHORT_SIDE):
    h, w = shape
    scale = short_side / min(h, w)
    return max(1, round(h * scale)), max(1, round(w * scale))


def resize_bool_short_side(mask, short_side=SHORT_SIDE):
    nh, nw = _shape_at_short_side(mask.shape, short_side)
    image = Image.fromarray((np.asarray(mask, dtype=np.uint8) * 255)).resize((nw, nh), Image.Resampling.NEAREST)
    return np.asarray(image) > 0


def resize_probability_short_side(probability, short_side=SHORT_SIDE):
    probability = np.asarray(probability, dtype=np.float32)
    nh, nw = _shape_at_short_side(probability.shape, short_side)
    image = Image.fromarray(probability, mode="F").resize((nw, nh), Image.Resampling.BILINEAR)
    output = np.asarray(image, dtype=np.float32)
    return np.clip(output, 0.0, 1.0)


def centreline(mask):
    mask = np.asarray(mask, dtype=bool)
    return skeletonize(mask) if mask.any() else mask.copy()


def soft_centreline_field(mask, short_side=SHORT_SIDE, half_value_radius=HALF_VALUE_RADIUS,
                          cutoff_radius=CUTOFF_RADIUS):
    """Return a native-grid field whose distances are measured at a 512-px short side.

    The value is 1 on the skeleton, 0.5 at exactly ``half_value_radius``
    normalised pixels, and zero beyond ``cutoff_radius``.
    """
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        return np.zeros(mask.shape, dtype=np.float32)
    skeleton = centreline(mask)
    distance_native = distance_transform_edt(~skeleton)
    distance_normalised = distance_native * short_side / min(mask.shape)
    field = np.exp(-math.log(2.0) * (distance_normalised / half_value_radius) ** 2)
    field[distance_normalised > cutoff_radius] = 0.0
    return field.astype(np.float32)


def _tolerance_scores(prediction, reference, radius):
    if not prediction.any() and not reference.any():
        return 1.0, 1.0, 1.0
    if not prediction.any() or not reference.any():
        return 0.0, 0.0, 0.0
    precision = float((distance_transform_edt(~reference)[prediction] <= radius).mean())
    recall = float((distance_transform_edt(~prediction)[reference] <= radius).mean())
    f1 = 0.0 if precision + recall == 0 else 2.0 * precision * recall / (precision + recall)
    return precision, recall, f1


def _component_counts(prediction, reference, radius=4):
    ref_labels, ref_count = label(reference, structure=np.ones((3, 3), dtype=np.uint8))
    pred_labels, pred_count = label(prediction, structure=np.ones((3, 3), dtype=np.uint8))
    distance_to_pred = distance_transform_edt(~prediction) if prediction.any() else np.full(reference.shape, np.inf)
    distance_to_ref = distance_transform_edt(~reference) if reference.any() else np.full(reference.shape, np.inf)
    ref_hit = sum(bool((distance_to_pred[ref_labels == component] <= radius).any()) for component in range(1, ref_count + 1))
    pred_matched = sum(bool((distance_to_ref[pred_labels == component] <= radius).any()) for component in range(1, pred_count + 1))
    return {"reference_components": int(ref_count), "predicted_components": int(pred_count),
            "reference_components_hit": int(ref_hit), "reference_components_omitted": int(ref_count - ref_hit),
            "predicted_components_matched": int(pred_matched), "predicted_components_extra": int(pred_count - pred_matched)}


def centreline_metrics(probability, published_mask, threshold=0.5):
    reference_mask = resize_bool_short_side(published_mask)
    probability_normalised = resize_probability_short_side(probability)
    predicted_band = probability_normalised >= threshold
    reference_line = centreline(reference_mask)
    predicted_line = centreline(predicted_band)
    output = {"target_empty": bool(not reference_mask.any()), "pred_empty": bool(not predicted_band.any()),
              "target_band_fraction": float(reference_mask.mean()), "pred_band_fraction": float(predicted_band.mean()),
              "reference_centreline_pixels": int(reference_line.sum()), "predicted_centreline_pixels": int(predicted_line.sum())}
    for tolerance in TOLERANCES:
        precision, recall, f1 = _tolerance_scores(predicted_line, reference_line, tolerance)
        output.update({f"cl{tolerance}_precision": precision, f"cl{tolerance}_recall": recall, f"cl{tolerance}_f1": f1})
    output.update(_component_counts(predicted_line, reference_line, radius=4))
    return output


def aggregate(rows):
    nonempty = [row for row in rows if not row["target_empty"]]
    if not nonempty:
        raise ValueError("No nonempty reference rows")
    reference_components = sum(row["reference_components"] for row in nonempty)
    omitted = sum(row["reference_components_omitted"] for row in nonempty)
    predicted_components = sum(row["predicted_components"] for row in nonempty)
    extra = sum(row["predicted_components_extra"] for row in nonempty)
    result = {"n_all": len(rows), "n_nonempty": len(nonempty), "n_empty": len(rows) - len(nonempty),
              "reference_components": reference_components, "reference_components_omitted": omitted,
              "component_omission_rate": float(omitted / reference_components) if reference_components else 0.0,
              "predicted_components": predicted_components, "predicted_components_extra": extra,
              "component_extra_rate": float(extra / predicted_components) if predicted_components else 0.0}
    for tolerance in TOLERANCES:
        for name in ("precision", "recall", "f1"):
            key = f"cl{tolerance}_{name}"
            result[f"mean_{key}"] = float(np.mean([row[key] for row in nonempty]))
    result["empty_reference_false_positive_n"] = sum(not row["pred_empty"] for row in rows if row["target_empty"])
    return result


def paired_bootstrap(candidate_rows, baseline_rows, key="cl2_f1", replicates=5000, seed=20261020):
    candidate = {row["id"]: row for row in candidate_rows if not row["target_empty"]}
    baseline = {row["id"]: row for row in baseline_rows if not row["target_empty"]}
    identities = sorted(candidate.keys() & baseline.keys())
    if len(identities) != len(candidate) or len(identities) != len(baseline):
        raise ValueError("Paired identities do not match")
    delta = np.asarray([candidate[identity][key] - baseline[identity][key] for identity in identities], dtype=float)
    rng = np.random.default_rng(seed)
    samples = np.empty(replicates, dtype=float)
    for index in range(replicates):
        samples[index] = delta[rng.integers(0, len(delta), len(delta))].mean()
    return {"n": len(delta), "candidate_minus_baseline_mean": float(delta.mean()),
            "bootstrap_95_ci": [float(np.quantile(samples, .025)), float(np.quantile(samples, .975))],
            "replicates": replicates, "seed": seed}


def field_dice(probability, target):
    prediction = np.asarray(probability) >= 0.5
    reference = np.asarray(target) >= 0.5
    denominator = int(prediction.sum() + reference.sum())
    return 1.0 if denominator == 0 else float(2 * np.logical_and(prediction, reference).sum() / denominator)
