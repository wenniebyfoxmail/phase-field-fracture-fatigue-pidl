"""
dataset_element.py — C6 (δ-1) element-level importance sampling dataset.

Implements the element-level DataLoader required for δ-1 adaptive sampling
(plan: references/branch2_c6_delta_plan.md §δ-1).

Key design:
  - Samples ELEMENTS (not nodes) with probabilities p_e ∝ residual_e
  - Returns all node indices for each sampled element so compute_energy can
    operate on the selected subset with 1/p_e importance correction
  - Preserves variational consistency: E[loss_minibatch] = full Deep Ritz integral

Usage (from model_train.py when delta1_dict is enabled):
    ds = ElementDataset(inp, T_conn, p_e=None)   # uniform init
    loader = DataLoader(ds, batch_size=K_elems, sampler=WeightedRandomSampler(...))
    # After each cycle, update p_e from residuals:
    ds.update_weights(new_p_e)

Note: this module is the DATA side of δ-1. The compute_energy side
(element_subset + 1/p correction) is handled by compute_energy.py changes.
See run_delta1_umax.py for the full integration.
"""
from __future__ import annotations

import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler


class ElementDataset(Dataset):
    """Element-level dataset for importance-sampled Deep Ritz training.

    Each item is one ELEMENT, identified by its index into T_conn.
    The model_train loop collects a mini-batch of K elements and passes
    their indices to compute_energy(element_subset=...).

    Args:
        n_elem:    Total number of elements in the fine mesh.
        p_e:       Per-element sampling probabilities (n_elem,).
                   None → uniform (1/n_elem). Updated each cycle via update_weights().
    """

    def __init__(self, n_elem: int, p_e: torch.Tensor | None = None):
        self.n_elem = n_elem
        if p_e is None:
            self.p_e = torch.ones(n_elem) / n_elem
        else:
            self.p_e = self._normalise(p_e)

    def __len__(self):
        return self.n_elem

    def __getitem__(self, elem_idx: int):
        # Returns (element_index, importance_weight = 1/p_e)
        # importance_weight used by compute_energy for unbiased estimation
        return elem_idx, float(1.0 / (self.p_e[elem_idx].item() * self.n_elem))

    def update_weights(self, residuals: torch.Tensor):
        """Recompute p_e from per-element residual proxy.

        Args:
            residuals: (n_elem,) tensor of |E_el_e| + |E_d_e| (detached).
        """
        self.p_e = self._normalise(residuals.detach().cpu())

    @staticmethod
    def _normalise(x: torch.Tensor) -> torch.Tensor:
        x = x.clamp(min=1e-30).float()
        return x / x.sum()

    def make_loader(self, samples_per_epoch: int | None = None,
                    replacement: bool = True) -> DataLoader:
        """Create a WeightedRandomSampler DataLoader over elements.

        Args:
            samples_per_epoch: How many elements to sample per epoch.
                               None → n_elem (full coverage, but resampled).
            replacement:       Sample with replacement (True, standard IS).
        """
        n_samples = samples_per_epoch or self.n_elem
        sampler = WeightedRandomSampler(
            weights=self.p_e,
            num_samples=n_samples,
            replacement=replacement)
        return DataLoader(self, batch_size=n_samples, sampler=sampler)


def compute_residual_proxy(inp, field_comp, hist_alpha, matprop, pffmodel,
                           area_T, T_conn, f_fatigue, device) -> torch.Tensor:
    """Compute per-element |E_el_e| + |E_d_e| as importance-sampling proxy.

    Mirrors the residual source used in compute_adaptive_weights (adaptive_sampling.py)
    but returns raw (n_elem,) tensor for ElementDataset.update_weights().
    E_hist excluded: it's a regularizer (near-zero after hist_alpha update).

    Returns:
        (n_elem,) float32 tensor on CPU (detached).
    """
    from compute_energy import compute_energy_per_elem

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        E_el, E_d, _ = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
            f_fatigue=f_fatigue)
        proxy = (E_el.abs() + E_d.abs()).detach().cpu()
    return proxy
