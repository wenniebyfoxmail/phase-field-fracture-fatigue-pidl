# Coverage inventory — 2026-10-05

Question: same Umax=0.12 teacher precision across early/middle/late cycles and within-cycle loading phases. Inventory is not a numerical PASS.

| Requested coverage | Located evidence | Status under native prior/oracle contract |
|---|---|---|
| c20/c40 early/middle | fixed_calendar v3 canonical_cycle_end/u012 MAT files contain only alpha_bar_elem, d_elem, f_alpha_elem, psi_elem; formal run has cycle-end VTK | NOT_EVALUABLE: element views/cycle-end fields are not peak nodal state plus accepted prior/GP history/oracle |
| c60 middle | formal run cycle-end VTK exists; no qualified peak pre_phase/oracle package found in checked native exports | NOT_EVALUABLE pending export |
| c76/c82/c83 peak | exact_peak_native_q4 v1, native captures plus v2.1 normalized current fields; single c0→c83 replay, source cdf4e337 | Candidate evaluable; c83 first, c76 bridge only |
| c87/c89 peak | formal native_q4_staging includes pre_phase_input, matlab_residual, converged_peak_solution | Candidate only: verify state/source lineage and event semantics before combining with replay captures |
| Within-cycle loading/unload at above cycles | scalar histories and cycle-end field views; exact native request deliberately captured s4 only | NOT_EVALUABLE for hard KKT until corresponding accepted prior and oracle exported |
| U0.13 c5 loading and 11 peak staggers | Request27 original anchors and residual vectors available | Method regression only; cannot substitute for U0.12 early states |

Sources (OneDrive griphfith root):
- hard5_u012_exact_peak_native_q4_c76_c82_c83_20260821_v1/README.md, state_index.csv, provenance/source_receipt.txt.
- hard5_fixed_calendar_exposure_states_20260824_v3/anchors/canonical_cycle_end/u012/cycle_0020.mat: inspected using scipy.io.whosmat (MAT v5, not HDF5).
- Umax_012_all_versions_20260729/05_hard_5step_formal_pidl_native_q4/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/native_q4_staging/: inspected MAT group inventory for c76/c87/c89.

## Minimal missing export

For U0.12 c20/c40/c60 and selected later-cycle loading/peak/unload states, export from the original accepted trajectory (or a separately qualified minimal replay):

1. cycle, physical load branch, substep and effective load, convergence/stagger index and exact state timing; source/config and trajectory identity;
2. native mesh/node numbering/GP order, current nodal u,d;
3. the immediately preceding ACCEPTED d_old and pre-step GP histories; do not use last stagger trial damage or the current committed state as its own predecessor;
4. full/free endpoint displacement and phase residual vectors, prescribed/free masks and reaction vectors, residual sign and external-force convention;
5. actual frozen coefficient used for the phase endpoint and separately reconstructed target-point trial coefficient, plus raw stopping scalars;
6. for timing localization only: preclip phase output, postclip damage, and post-update state at the same final stagger.

First inspect retained native checkpoints on the original Windows producer. If these fields were never captured, a file conversion cannot recover them; use a reviewed replay plan with explicit checkpoint/lineage and bounded compute. No request has yet been sent to a human or original producer; this is the executable data specification. No expensive trajectory rerun has been launched.

## Additional checks

The actual replay load-displacement file records a five-step cycle: s1 about0.03, s2 about0.06, s3 about0.09, s4 peak0.11999988, s5 near-zero unload. Therefore the minimal within-cycle request is **s2/s4/s5**, not a guessed s8. Normalized residuals must use the same trajectory peak Us at all three substeps.

Read-only check of the user-authorized gpu-server found neither C:/q4runs nor C:/Users/xw436/GRIPHFiTH. This available compute host does not expose the original producer archive paths listed in the replay receipt. It cannot supply missing accepted states merely through computation access.

Deeper inventory also found fixed_calendar v3/data/u012/c0020_s004_post_commit.mat (and c0040 counterpart): request28_snapshot contains current u_node/d_node/native GP fields, but history_vars_old is explicitly post-history-commit, with no independent pre_phase accepted predecessor or endpoint oracle. These current-state exports improve field availability but do not close the KKT input gap. The formal checkpoint.mat stores only one accepted snapshot, not a indexed c20/c40/c60 substep history; it cannot be assumed to be the required predecessor.
