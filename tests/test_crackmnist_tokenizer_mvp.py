from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "crackmnist_tokenizer_mvp.py"
SPEC = importlib.util.spec_from_file_location("crackmnist_tokenizer_mvp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_model_forward_contract():
    import torch

    model = MODULE.build_model()
    latent, reconstruction, tip_logits, sif = model(torch.zeros(2, 2, 28, 28))
    assert latent.shape == (2, 32)
    assert reconstruction.shape == (2, 2, 28, 28)
    assert tip_logits.shape == (2, 784)
    assert sif.shape == (2, 3)


def test_batch_losses_are_finite_with_visible_and_empty_masks():
    import torch

    model = MODULE.build_model()
    losses = MODULE.batch_losses(
        model,
        torch.zeros(3, 2, 28, 28),
        torch.tensor([0, 1, 2]),
        torch.tensor([True, False, True]),
        torch.zeros(3, 3),
    )
    assert all(torch.isfinite(value) for value in losses[:4])
    empty_losses = MODULE.batch_losses(
        model,
        torch.zeros(2, 2, 28, 28),
        torch.tensor([0, 1]),
        torch.tensor([False, False]),
        torch.zeros(2, 3),
    )
    assert float(empty_losses[2].detach()) == 0.0


def test_lineage_average_weights_lineages_equally():
    values = np.asarray([[0.0], [2.0], [10.0]])
    ids, averaged = MODULE.lineage_average(values, np.asarray([5, 5, 9]))
    assert ids.tolist() == [5, 9]
    assert averaged[:, 0].tolist() == [1.0, 10.0]


def test_split_indices_use_released_names_only():
    class Dummy:
        split_names = np.asarray(["train", "train", "val", "test"])

    result = MODULE.split_indices(Dummy())
    assert result["train"].tolist() == [0, 1]
    assert result["val"].tolist() == [2]
    assert result["test"].tolist() == [3]


def test_representative_row_never_uses_empty_tip_mask():
    lineage_ids = np.asarray([1, 1, 2, 2])
    reconstruction_error = np.asarray([0.01, 0.02, 0.20, 0.30])
    tip_visible = np.asarray([False, False, True, True])
    selected = MODULE.select_representative_visible_row(
        lineage_ids, reconstruction_error, tip_visible
    )
    assert selected in (2, 3)
    assert bool(tip_visible[selected])


def test_producer_guard_binds_reviewed_commit_and_authorised_host():
    valid = dict(
        audit_pass=True,
        epochs=MODULE.EPOCHS,
        batch_size=MODULE.BATCH_SIZE,
        latent_dim=MODULE.LATENT_DIM,
        seed=MODULE.SEED,
        device="cuda",
        git_commit="reviewed-sha",
        git_dirty="",
        reviewed_commit="reviewed-sha",
        hostname=MODULE.AUTHORIZED_PRODUCER_HOSTNAME,
    )
    assert MODULE.producer_violations(**valid) == []
    assert "HEAD must equal the independently reviewed commit" in MODULE.producer_violations(
        **{**valid, "reviewed_commit": "other-sha"}
    )
    assert any(
        "authorised producer" in finding
        for finding in MODULE.producer_violations(**{**valid, "hostname": "other-host"})
    )
