"""Current FEM/PIDL alignment protocol constants.

This module is deliberately small: it records the comparison convention that
should be used for the soft-hist0 reverseBC audit track so scripts do not drift
between old geom2 PIDL, FEM-mesh PIDL, and ambiguous cycle indexing.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ANALYSIS_DIR = ROOT / "_analysis_fem_mechanism_20260528"

ONEDRIVE_PIDL_RESULT = (
    Path.home()
    / "Library"
    / "CloudStorage"
    / "OneDrive-UniversityofCambridge"
    / "PIDL result"
)

FEM_SOFT_HIST0_DIR = (
    ONEDRIVE_PIDL_RESULT
    / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28"
)
FEM_SOFT_HIST0_FIELDS = FEM_SOFT_HIST0_DIR / "reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat"
FEM_SOFT_HIST0_METRICS = FEM_SOFT_HIST0_DIR / "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv"
FEM_SOFT_HIST0_STATE_TIMING_DIR = (
    ONEDRIVE_PIDL_RESULT
    / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29"
)

PIDL_FEMMESH_ARCHIVE = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0"
)
PIDL_FEMMESH_MESH = HERE / "meshed_geom_fem_soft_hist0.msh"

# FEM cycle c1 maps best to PIDL saved j=0 in the state-timing audit.
PIDL_SAVED_INDEX_OFFSET_FOR_FEM_CYCLE = -1
PRIMARY_COMPARISON_CYCLES = (1, 20, 40, 69)

PROTOCOL_NOTE = (
    "soft-hist0 reverseBC retained-material track; FEM c1 mixed timing maps "
    "to PIDL saved j=0; compare absolute and incremental E_d separately"
)
