# Missing U0.115 PINN acquisition candidate

Status: `PROPOSED_NEW_ACQUISITION__NOT_RUN_READY`. Existing trajectory lookup
did not establish a reusable exact U0.115 PINN counterpart. This is a new
costly PINN solve, distinct from export/verification of stored states and from
the later supervised Delta experiment. No launch is implied by this card.

Single decision: acquire one exact-family development PINN trajectory so the
U0.115 FEM asset can become a paired same-state s4 development axis.

Reference settings read on Taobo from
`/mnt/data2/drtao/pidl_archives/pf_hard_d1_u0_recovery_e9dc263_20260630_043100/*/model_settings.txt`:
runner `run_fem_mesh_probe_driver_umax.py`; seed1; 8 hidden layers, 400 neurons;
10000 RPROP epochs maximum per training step; LBFGS0; optim_rel_tol5e-7;
history mode current_active; history reduction fem_gp_tri3_g_mean; FEM-GP
irreversibility penalty; hard initial alpha1; recovery offset1; five load
factors [.25,.5,.75,1,0]. These settings identify a candidate family, not a
fully frozen executable source snapshot. Parent source/mesh/state0 identities,
CLI support and independent Code Ready review must be locked before execution.

Proposed scope: Umax0.115 only, seed1, fixed 120 physical cycles (601 training
steps including recovery), which covers the existing 103-cycle FEM archive
without using FEM event time as an input or stopping feature. Retain every
s4/s5 checkpoint and corresponding committed histories; true recovery state
and all source receipts; map s4=5c-1 and s5=5c only under the verified offset.
Record native support and centroid/cell projection. No amplitude sweep, no
hyperparameter tuning, no U0.1175 or U0.125 labels/fields.

Proposed cap: one Taobo GPU selected from live availability, <=48h wall and
<=50GiB task-owned outputs; no automatic continuation after the cap or failure.
This cap bounds resources, not an evidence-based runtime estimate. Cap hit
means partial/unqualified; never shorten the declared trajectory silently.
Paths under `/mnt/data2/drtao/wennie/<fresh_run_id>` and
`/mnt/data2/drtao/pidl_archives/<fresh_run_id>`; detached execution and process
receipt required. No Mac training or Windows FEM.

Success: executed/retrieved exact source/settings/cadence; full declared
checkpoint coverage; finite matching timing/support arrays and contiguous
lineage. Then finish G5; acquisition does not establish Delta learnability,
native FEM truth, or multiobjective gain. Budget and scientific design need
approval/review before producer execution. The G5 owner remains sole executor.
