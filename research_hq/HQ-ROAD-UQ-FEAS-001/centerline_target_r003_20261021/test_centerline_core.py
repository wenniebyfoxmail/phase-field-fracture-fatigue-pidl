"""Read-only tests for the frozen D5 target and metric semantics."""
import numpy as np

from centerline_core import (aggregate, centreline_metrics, field_dice, paired_bootstrap,
                             resize_bool_short_side, soft_centreline_field)


def test_scale_normalisation():
    a = np.zeros((512, 1024), bool); a[240:273, 100:925] = True
    b = np.zeros((1024, 2048), bool); b[480:546, 200:1850] = True
    fa = soft_centreline_field(a); fb = soft_centreline_field(b)
    assert fa.shape == a.shape and fb.shape == b.shape
    assert np.isclose(fa.max(), 1.0) and np.isclose(fb.max(), 1.0)
    # Integer rasterisation changes the band by at most a small relative amount.
    assert np.isclose(float((fa >= .5).mean()), float((fb >= .5).mean()), rtol=.15)
    assert resize_bool_short_side(a).shape == resize_bool_short_side(b).shape == (512, 1024)


def test_identical_and_shifted_metrics():
    mask = np.zeros((128, 256), bool); mask[60:68, 20:230] = True
    probability = soft_centreline_field(mask)
    exact = centreline_metrics(probability, mask)
    assert exact["cl4_f1"] > .99 and exact["reference_components_omitted"] == 0
    shifted = np.roll(probability, 12, axis=0)
    moved = centreline_metrics(shifted, mask)
    assert moved["cl1_f1"] < exact["cl1_f1"] and moved["cl4_f1"] < exact["cl4_f1"]


def test_empty_and_components():
    empty = np.zeros((64, 64), bool)
    row = {"id": "empty", **centreline_metrics(np.zeros((64, 64), np.float32), empty)}
    assert row["target_empty"] and row["pred_empty"] and row["cl1_f1"] == 1.0
    mask = np.zeros((64, 64), bool); mask[10:14, 5:25] = True; mask[45:49, 35:58] = True
    prediction = soft_centreline_field(mask); prediction[32:] = 0
    row2 = {"id": "two", **centreline_metrics(prediction, mask)}
    result = aggregate([row, row2])
    assert result["reference_components"] == 2 and result["reference_components_omitted"] == 1
    assert result["empty_reference_false_positive_n"] == 0


def test_pairing_and_field_dice():
    baseline = [{"id": str(i), "target_empty": False, "cl2_f1": .2 + .01 * i} for i in range(10)]
    candidate = [{"id": str(i), "target_empty": False, "cl2_f1": .4 + .01 * i} for i in range(10)]
    paired = paired_bootstrap(candidate, baseline, replicates=200, seed=7)
    assert np.isclose(paired["candidate_minus_baseline_mean"], .2)
    target = np.asarray([[0, 1], [0, 1]], dtype=float)
    assert field_dice(target, target) == 1.0


if __name__ == "__main__":
    test_scale_normalisation(); test_identical_and_shifted_metrics(); test_empty_and_components(); test_pairing_and_field_dice()
    print("PASS: target, scale, tolerance, component, empty-reference, pairing checks")
