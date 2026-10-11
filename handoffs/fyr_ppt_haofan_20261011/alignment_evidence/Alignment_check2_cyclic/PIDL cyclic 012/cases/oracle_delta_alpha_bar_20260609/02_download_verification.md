# Download Verification: oracle_delta_alpha_bar_20260609

Status: downloaded and verified on 2026-06-09.

- remote run id: `oracle_triplet_8970066_20260609_182141`
- remote archive: `/mnt/data2/drtao/pidl_archives/oracle_triplet_8970066_20260609_182141/oracle_delta_alpha_bar_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc80_Nstep400_U0.12_oracle_delta_alpha_bar_full_s0.25-0.5-0.75-1-0`
- local archive: `raw_archive/oracle_delta_alpha_bar_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc80_Nstep400_U0.12_oracle_delta_alpha_bar_full_s0.25-0.5-0.75-1-0/`
- local log: `logs/delta_alpha_bar.log`
- local provenance/code snippets: `run_workspace/RUN_PROVENANCE.txt`, `run_workspace/run_fem_mesh_oracle_field_umax.py`, `run_workspace/_launch_oracle_triplet_taobo.sh`

Archive checks:

- file count: 1309 files.
- total size: 2571543076 bytes, about 2.395 GiB.
- final checkpoint/model: found `best_models/checkpoint_step_399.pt` and `best_models/trained_1NN_399.pt`.
- scalar histories: found in `best_models/`, including `Kt_vs_cycle.npy`.
- gradient diagnostics: found `best_models/energy_gradient_terms_vs_cycle.npy`.
- alpha snapshots: 20 files.
- element diagnostics: 15 `.npz` files in `element_diagnostics_oracle_delta_alpha_bar/`, steps `0000, 0003, 0004, 0008, 0009, 0013, 0014, 0098, 0099, 0198, 0199, 0298, 0299, 0343, 0344`.
- analysis package: regenerated; 18 figure files and 9 table files present.

Log stop evidence:

- completed final PIDL step `399` for `Nstep=400`.
- no boundary fracture in the final log tail.
- final visible trace: `alpha_bar_max=1.9532e+01`, `f_min=0.0025`, `f_mean=0.9200`, `alpha_max@bdy=0.2599`, `N_bdy>0.95=0`.

Missing artifacts:

- true unloaded prehistory PIDL state is not available; PIDL step `0000` is load factor `0.25`, not `state0_initial_unloaded_prehistory`.
