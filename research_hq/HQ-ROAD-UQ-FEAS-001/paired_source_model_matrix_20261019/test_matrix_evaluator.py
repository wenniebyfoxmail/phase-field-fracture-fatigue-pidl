"""No-inference contract checks for the paired matrix evaluator."""
import numpy as np

import paired_matrix_evaluator as matrix


def row(identity, error, empty=False):
    return {"id": identity, "error": error, "dice": 1 - error, "target_empty": False,
            "pred_empty": empty, "pred_full": False, "U_LC": error, "U_H": error,
            "U_Z": error, "tol2_f1": 1 - error / 2, "tol4_f1": 1 - error / 4}


def main():
    target = np.zeros((9, 9), bool); target[4, 4] = True
    shifted = np.zeros((9, 9), bool); shifted[4, 6] = True
    strict = matrix.tolerance_overlap(shifted, target, 0)[2]
    tolerant = matrix.tolerance_overlap(shifted, target, 2)[2]
    assert strict == 0 and tolerant == 1
    old = [row(f"i{i}", 0.8) for i in range(12)]
    new = [row(f"i{i}", 0.5) for i in range(12)]
    delta = matrix.bootstrap_delta(old, new)
    assert abs(delta["new_minus_old_mean_error"] + 0.3) < 1e-12
    summary = matrix.summarize(old)
    assert summary["accepted_n"] == 3 and summary["n_nonempty"] == 12
    ids = matrix.selected_ids(old, new)
    assert ids and len(ids) <= 8
    print({"status": "pass", "training_steps": 0, "road420_access": False})


if __name__ == "__main__": main()
