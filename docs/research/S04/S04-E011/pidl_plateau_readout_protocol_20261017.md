# S04-E011-NCP/r1 — native checkpoint plateau readout, no training

Authorized user task2026-10-17: compare latest FEM/PIDL and distinguish a flat
loss from a well-solved state or optimization stagnation. This is a synthetic
diagnostic on the unchanged E011 paired-Q4 baselinead749c8, not a new trained
baseline or physical qualification. It accompanies MCS/r1, never selects FEM
using PIDL agreement, and never consumes a new holdout.

Use original stored models at c1/20/60/80/83 eachs2/s4, k=5(c-1)+s (recovery0).
Bind originalsource/model_settings/mesh/model/currentcheckpoint/previousk-1
checkpoint/loss arrays and pre-history-refresh energy-gradient table. Verify
stored arity4/historyq4_gp4/previous_accepted_nodal/current_active/eta0, shape
and source schedule. Content cycle metadata is checked where present; otherwise
state identity relies explicitly on frozen production naming/schedule/receipts,
not an invented checkpoint field. Never use checkpointk postcommit f or lower
to reconstruct its optimization objective: use k-1 hist_alpha andhist_fat.

Reuse original source constructor/field parameterization/nativecompute_energy,
explicitfem_gp_q4 penalty, frozenf=Carrara(pre.hist_fat), no clipping. Objective
is original log10(Eel+Ed+Ehist)+1e-5*sum(namedweight^2), histweight1. Compare
recomputed post-step components to original pre-history-refresh diagnostic row
k, not just final trainingloss: fit.py stores loss BEFORE optimizer.step,
while modelk is AFTER that update. OriginalRPROPstate was not stored; do not
claim exact optimizer continuation. Confirm no additional enabled losses.

CPU1thread on Taobo, CUDA_VISIBLE_DEVICES empty, nice10, fresh attributable
/mnt/data2/drtao/wennie and /mnt/data2/drtao/pidl_archives roots; TMPDIR and
XDG_CACHE_HOME under ownroot. Firstread-only CPU/RAM/disk/sourceprocess check;
require at least32GiBavailableRAM and10GiBownmountspace. No sharedGPU use, no
Mac training, no original archive/code write, no optimizer.step/train loop or
acceptedhistory updates. Actual full-network forward/backward uses CPU; full
batch avoids changing quadrature, field sampling or microbatch activation paths.
Soft30minute evaluation-start deadline, 10state readouts, onebackward plus8independent directional evaluations
perstate (plus deterministic baseline repeat). Check before every objective evaluation; an evaluation
already running may finish beyond30min, but no new evaluation starts thereafter.
Save completed rows/trials and a partial marker on deadline; restore perturbed parameters in finally. Baseline nonfinite/identity failure stops global; unavailable later
states remain missing. No retries/capgrowth. Save completed state artifacts as
they finish and an attributable detached PID/command/log/commit receipt.

For each state: energies/log/reg, originalloss length and exactlast10relative
loss changes, component/node gradients, network total/physical/reg gradients
and cancellation cosine, damagebox/lower violations, own-prehistory f, reaction-
excluded free-u nodal energygradient, originalpoststep componenterrors, and
deterministic repeatloss. Sourceenergy reproduction is a float32 cross-device
readout check: each component relativeerror<=1e-4 with absolute floor1e-10;
failures remain source-readout mismatches and cannot support original-objective
optimization attribution. This is not an energyaccuracy/physical tolerance.

Probe same-parameter directions only after this source-readout check. Every
trial starts from exacttheta0; direction=-g/||g||*max(1,||theta0||), dimensionless
fractions1e-7,3e-7,1e-6,3e-6,1e-5,3e-5,1e-4,3e-4. Evaluate full fixedobjective,
restoretheta aftereachtrial, no historyadvance/model save/acceptance. Nonfinite
candidate is recorded invalid and restored, not a new baseline. Report all
fractions, not just winner. A loss drop above deterministic repeatvariation+
32float32eps*max(1,|L|) demonstrates an available lower fixedobjective at this
scale, not physical accuracy or certified optimizer failure on all scales.
Small/no drop or small networkgradient does NOT prove a good continuum solution:
nodal residuals, bounds, parameterization saturation and reference mismatch
remain separate. Hard-bound violations block interpreting these as feasible
physical damage equilibria even if their soft-penalty objective is stationary.

Minimum outputs: tenunchangedbaseline nodal field NPZs withownprehistory and
loss/gradient rows, alltriallosses, originalscalar evolution arrays and all600
lossstop summaries, input/source integrity identities, complete/partial marker.
Then offline same-state FEM/PIDL comparisons under MCS/r1, own-objective
stationarity/plateau figure, exacttables and limits. Independent exactcode/
protocol/package review before execution and independent evidence review after
retrieval. Fullsource outputs preserved; no NNcapacity/uniqueoptimum/physical
teacher or correctedtrajectory claim. Choose subsequent PIDL repair from the
qualified FEM subset plus measured bounds/representation/optimization limit,
not from lossflatness alone.

## Pre-result engineering amendment2026-10-17

Run pf_s04e011_ncp_06742d7_20261017T2024Z stopped on the first completed
state's rows.json serialization (NumPy bool not JSON type); no complete marker,
parameter update or history commit. Preserve failed run, log and partial fields.
One fresh reviewed engineering execution converts two result booleans and
component errors to built-in JSON scalars, with unchanged data, objective,
state set, direction grid and per-run30min start deadline. No numerical limit
relaxation or successful-result selection; no further automatic retry. Failed
readout is not source-objective or optimization evidence.
