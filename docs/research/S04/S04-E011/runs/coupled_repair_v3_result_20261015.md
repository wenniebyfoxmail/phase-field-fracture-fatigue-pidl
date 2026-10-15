# Coupled displacement / constrained damage diagnostic — completed 2026-10-15

The approved CR-v3/r1 run closes both fresh equations at all four independent peak starts. The late-cycle active fields become much less similar to PIDL. These are different conclusions: bounded numerical closure supports the predeclared criterion, while field agreement does not improve at c83.

## Execution and identity

User approved nine-filev3 +15local snapshots, then the two-file comment/hash-only patch r1; local independent review explicitly replaces old Pro review for this version. Installed producer clean commit `5cf59f8c20c800a65bb594ced761b604df33bef6`, branch `codex/hard5-q4-t3-2x2-20261005`. CITPC12/AD\xw436, MATLABR2025b single CPU thread; root `C:\Users\xw436\jobs\E011_CR_20261015_v3`. WMI wrapper36764, launcher25304, worker1460, UTC19:46:13.994→19:51:45 (BST20:46:13→20:51:45), approximately331s. No relaunch or other process disturbance.

All nine installed files match approved combined manifest, Windows entrycheckcode empty and remaining diagnostics NASGU/MSNU only;12algebra selftests pass. The same actual worker passed io_preflight15inputs/540736827bytes, native mesh import and both accepted-s3 geometry checks before cases. Observed DONE order: c1baseline, c1last_accepted, c83baseline, c83last_accepted. Terminal statuscompleted/states4/historycommits0. Retrieval verified51files1058569769bytes, every SHA256/size matched; no failure marker and no own MATLAB left running.

## Primary and comparator

Exactly the preceding DR-v1 constrained endpoints are the starts, labelled by original saved outer3/13/20/28; these labels are not new accepted trajectory states. Native Q4 mesh86756nodes/86408elements,2x2GP, E1,nu.3,Gc.01,ell.01,alphaT.5,p2,eta0, native GP penalties421875/13781.25, actual peakU=.11999988. Accepted original s3 history/lower remain immutable. Full u→d blocks use fresh-return mechanical stopping plus byte-identical constrained phase helper; raw, mechanical and phase are reassembled at identical returnedu,d. No trial-f chain fix or new outer damping/line search; the phase helper retains its existing inner globalization. No tolerance change or accepted history update.

Frozen primary `C=max((Ru+Rd_feasible)/4e-6,Ru/1e-8)<=1`, with bounds/finite/fixed-BC checks. This is stricter than DR's phase-only screen. Previous fixed-u mechanical residuals were7.93469638e-5/5.26444778e-6/2.41066330e-4/3.08923851e-4. Full-field replay verifies initial raw refresh separately; c83baseline maximum absolute raw change8.286e-7 but active relative change only1.946e-8. It does not explain the large terminal field change.

| start (saved origin) | completed blocks | Ru final | Rd feasible final | C final (<=1) | u/d calls |
|---|---:|---:|---:|---:|---:|
|c1 baseline (outer3)|4|2.84228885e-15|2.59077714e-06|0.647694285|31/15|
|c1 last_accepted (outer13)|1|2.83130835e-15|7.70022147e-07|0.192505537|10/6|
|c83 baseline (outer20)|17|2.52009512e-15|3.75507820e-07|0.0938769557|97/65|
|c83 last_accepted (outer28)|15|2.51514786e-15|2.87912902e-08|0.00719782319|87/59|

Total225u+145d native calls,370overall, versus predeclared2000maximum. Counts include admissions, attempts, completed-block audits and root final audit; per-case<=250each, blocks<=20. At each final block damage update is exactlyzero and the displacement solve leaves Ru around2.5–2.8e-15; feasible phase remains under4e-6. Raw bound reaction is not the declared feasible residual.

Both c83 trajectories are nonmonotonic: C peaks82545.8 at block13 (baseline) and82445.5 at block11 (last), then falls sharply. Last damage updates before the final equilibrium-only block are0.155956 and0.152814. This is nonlinear same-peak outer-iteration evolution, not evidence of linear/exponential cycle-to-cycle error accumulation.

## Field comparison and location

Same Q4 GP/Jacobian weights, paired PIDL c1s4/c83s4 checkpoints4/414; the601-state archive includes recovery checkpoint0. No training or new PIDL inference. Both denominators are shown to avoid an apparent improvement caused by normalization. Initial uses coherent fresh raw at exactly the old DRu,d, whose difference from old fixed raw is independently small.

| start | active integral initial → final | fixed PIDL-denominator relL2 | varying FEM-denominator relL2 | weighted correlation |
|---|---|---|---|---|
|c1 baseline|0.00480083333 → 0.00479617892|23.8055% → 22.6870%|23.8550% → 22.6250%|0.950773 → 0.955685|
|c1 last_accepted|0.0047945772 → 0.00479456818|22.5891% → 22.6204%|22.5423% → 22.5667%|0.956024 → 0.955926|
|c83 baseline|0.000691265119 → 2.07113365e-05|48.2533% → 104.1585%|49.9259% → 346.6764%|0.877108 → 0.006643|
|c83 last_accepted|0.000667737752 → 2.07112287e-05|58.2910% → 104.1585%|59.6642% → 346.6762%|0.822255 → 0.006642|

At c83 active integral falls to2.99615%/3.10170% of its initial value, while fixed-PIDL-denominator error grows to104.1585%; varying FEM-denominator error grows to346.676%. PIDL/FEM integrated active becomes36.0416/36.0417 (excess3504.16%/3504.17%). Near-zero weighted correlation confirms this is not solely a changing denominator.

Largest c83 nodal damage increase is0.998470/0.998469 at right-edge(x=.5,y=-.00299391365); the crack-band map shows right-ligament damage extending and widespread active suppression. This is consistent with stiffness loss and displacement redistribution under the coupled iteration. It does not establish a unique physical cause or energy-minimizing branch. Both c83 starts reach close, not identical, endpoints: maxu difference2.82451e-7, maxd difference.00348763, weightedactive relL2 between finals2.55253e-5. Two starts do not prove uniqueness.

c1baseline changes modestly (maxd.0271734 nearx.000293,y.002103), PIDL fixed-den error23.8055→22.6870%; c1last dunchanged and onlyurebalances, gap22.5891→22.6204%. Thus closure does not monotonically improve PIDL agreement even early.

## Independent verification and decision

Independent local review rehashed all51files and replayed all16snapshots: max residual mismatch1.66344e-16, raw scaled mismatch3.06253e-12; original accepted history/lower exact, initialu,d exact DR, final residual exact rootaudit. Counter reconstruction agrees, PIDL coords/topology/checkpoint and all dual-denominator metrics independently agree. Two figures visually inspected; sidecar validator2/2. Full local evidence includes `analysis/coupled_analysis.json`, snapshots/traceCSV, `coupled_closure.png`, `coupled_fields.png`, field reductions and start-sensitivityJSON; compact [metrics](coupled_repair_v3_metrics_20261015.csv)/[trace](coupled_repair_v3_outer_trace_20261015.csv) travel with Git.

Verdict: **supports bounded same-peak numerical coupled closure at these four starts**; dispositionadvance for this numerical component. Prior stagnation is not an unavoidable residual floor at these states. The combined constraint/globalization, fresh same-field stopping and displacement feedback repair works without a trial-f tangent-chain change; this is not a factorial attribution to one change. c83 field similarity is descriptively much worse, so no overall FEM/PIDL alignment success.

Next smallest discriminator, not executed or uploaded: a reviewed sequential substep/commit test of the repaired solver from a verified c1 accepted initial state, saving every substep and committing history exactly once after a joint-pass state. Use original constitutive/history law and compare the unmodified same-initial trajectory; first validate one complete loading/unloading cycle, then decide whether to trace earlier-to-later onset with bounded fresh runs. A same-peak frozen-history closure cannot answer when the full trajectory should fracture or whether errors accumulate linearly/exponentially. Do not directly overwrite accepted c83 states or launch120cycles.

Original E003/E011 trajectories, estimands and teacher status remain frozen. No physical certificate, teacher qualification, repaired fatigue-life prediction or unique branch is established; PIDL fixed-committed-f vs FEMtrial-f and jointDeepRitz vs staggered/Picard differences remain. No GitHub push or new external send.

Raw asset: `local_archive/experiments/S04-E011/runs/pf_s04e011_coupled_repair_20261015_v3`. Producer receipts/source/inputs/logs/retrieved and analysis retained. This terminal numerical diagnostic supersedes the earlier pending-static-patch status, while failed v1/v2 receipts remain historical.
