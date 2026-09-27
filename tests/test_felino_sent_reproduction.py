from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
SENS = ROOT / "SENS_tensile"
for path in (SOURCE, SENS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compute_energy import (get_felino_icla_drive_per_elem,
                            strain_energy_with_split)
from fatigue_history import compute_fatigue_degrad, update_fatigue_history
from material_properties import MaterialProperties
from pff_model import PFFModel


def _material():
    return MaterialProperties(
        mat_E=torch.tensor(210000.0), mat_nu=torch.tensor(0.3),
        w1=torch.tensor(2.7 / 0.016), l0=torch.tensor(0.016),
    )


def test_locked_contract_is_internally_consistent():
    contract = json.loads(
        (SENS / "felino_sent" / "contract.json").read_text(encoding="utf-8")
    )
    fatigue = contract["fatigue"]
    assert fatigue["accepted_steps"] * fatigue["cycle_jump"] == fatigue["total_cycles"]
    assert contract["material"]["phase_field"] == "AT2"
    assert contract["reference"]["physical_truth"] is False


def test_felino_icla_drive_and_cycle_jump_for_uniaxial_strain():
    inp = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    conn = torch.tensor([[0, 1, 2]])
    area = torch.tensor([0.5])
    eps = 1e-3
    u = torch.zeros(3)
    v = eps * inp[:, 1]
    drive = get_felino_icla_drive_per_elem(
        inp, u, v, _material(), area, conn,
        load_ratio=0.5, material_constant_n=0.5,
    )
    factor = ((1 + 0.5) / 2) ** 2 * ((1 - 0.5) / 2) ** 0.5
    expected = 2 * 210000.0 * eps**2 * factor
    assert torch.allclose(drive, torch.tensor([expected]), rtol=1e-6)
    updated = update_fatigue_history(
        torch.zeros(1), drive, torch.zeros(1),
        {"loading_type": "cyclic", "accum_type": "felino_icla", "cycle_jump": 100},
    )
    assert torch.allclose(updated, torch.tensor([expected * 100]), rtol=1e-6)


def test_spectral_split_and_felino_residual_degradation():
    model = PFFModel(
        PFF_model="AT2", se_split="spectral", tol_ir=1e-3,
        residual_stiffness=torch.tensor(1e-6),
        degradation_mode="multiplicative_residual",
    )
    mat = _material()
    alpha = torch.tensor([0.0, 1.0])
    g, _ = model.Edegrade(alpha)
    assert torch.allclose(g, torch.tensor([1.0, 1e-6]), atol=1e-8)
    tension = torch.tensor([1e-3])
    zero = torch.tensor([0.0])
    e_t, e_p = strain_energy_with_split(tension, zero, zero, torch.tensor([0.0]), mat, model)
    assert torch.allclose(e_t, e_p)
    e_c, e_c_p = strain_energy_with_split(-tension, zero, zero, torch.tensor([1.0]), mat, model)
    assert float(e_c) > 0
    assert float(e_c_p) == 0.0


def test_asymptotic_degradation_matches_locked_formula():
    hist = torch.tensor([62.5, 125.0])
    f = compute_fatigue_degrad(
        hist, {"degrad_type": "asymptotic", "alpha_T": 62.5}
    )
    assert torch.allclose(f, torch.tensor([1.0, (125.0 / 187.5) ** 2]))
