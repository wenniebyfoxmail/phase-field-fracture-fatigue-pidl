# S04-E021-R001 — single approved attempt completed and frozen

2026-10-15 Europe/London. Execution:succeeded. Retrieval:verified (produced
locally, no transfer). Frozen-rule outcome:DIRECTIONAL_DEVELOPMENT_GAIN.
Main-chat evidence check complete; independent evidence review still pending.
Disposition:advance only to read-only evidence review, not another computation.

Current update2026-10-15:independent review now accepted. The original pending
statements elsewhere below preserve the pre-review record; see evidence_review.md
and final update at the end. No raw output or frozen result changed.

## Authority, identity and execution

Direct user approval names6aa21e3, S04-E021-R001 and300s/2GiB/100MiB with no
retry. One guard invocation only; no failed attempt, smoke, retry or refit.
Runtime:`6aa21e3c469d53c92240c9689d07a3ffb316d67c`; reviewed sources byte-identical
to c883bfd; design45b8d32/lock unchanged. Branch:
`codex/s04-e021-physical-raw-20261015`. Prelaunch tracked tree clean; only the
six approved leaf input symlinks give the guard's `?? local_archive/` dirty
entry. No whole-archive mount or confirmation link. Data/control paths and
exact approved command are in immutable6aa21e3 run_card.md.

Producer:`Wennies-MacBook-Pro-14.local`; Python
`/Users/wenxiaofang/miniconda3/bin/python3`, CPU4/noGPU, local unified exec
session2300. GuardPID23520; fitPID23541; reportPID24187, both exit0. All three
PIDs absent at terminal check. Guard start2026-10-15T15:49:26.437554+00:00.
Source hash/state/admission checks executed in the bounded loader before fit.
No SSH, Windows/FEM solve, PINN/NN training, MOO or other-chat task launched.

| Joint guard quantity | Observed | Limit |
|---|---:|---:|
| wall from reviewed timer |106.372758292s|300s|
| sampled guard+child-tree peakRSS |1,648,459,776bytes (1.53525GiB)|2GiB|
| final frozen output+log/receipts |7,410,199bytes (7.06692MiB)|100MiB|

Terminal guard's own pre-write size field=7,408,410bytes; final inventory adds
its1,789-byte receipt. This is expected accounting, not missing output. Parent
startup, polling peak limitations and original cap scope remain as disclosed
in run_card.md. No runtime warnings or traceback were found in the saved log: the
saved log has six inner and four outer completion lines, with no Warning or
Traceback token. Guard `real_fit_performed=null` is not a false or an automatic
scientific assertion; actual fitting is evidenced by its attributed fit child,
exit0, models/selection and full saved scores.

## Frozen results — physical raw RMSE, V1/V0

| Whole-Umax holdout | All-cycle balanced R | RMSE reduction | C1–20 G | Early RMSE reduction | alpha | Fallback |
|---|---:|---:|---:|---:|---:|---|
|0.11|0.9673852953|3.2615%|0.9097163624|9.0284%|1|no|
|0.115|0.9478121483|5.2188%|0.9319751006|6.8025%|1|no|
|0.12|0.8476125342|15.2387%|0.8411589707|15.8841%|0.01|no|
|0.13|0.9083381015|9.1662%|0.9185162821|8.1484%|1|no|

Q=maxR=0.967385295278036<1-eps; allG<=1+eps. All four outer choices are learned,
made by inner rules before outer scores. No outer-dependent fallback. Inner
alpha.01 fails early eligibility in three folds; eligible alternatives remain.
The four selected alphas and eligibility/ranking were locally recomputed from
saved selection.json by the read-only verifier, not retuned. That local check
is not the pending independent evidence review.

Damage/history are identical between arms by construction and saved checks,
not newly improved learned outputs. Raw final output nonnegative in all357
saved cycle-range records; fixed C20 outputs satisfy d∈[0,1],ab/raw>=0. These
pointwise checks do not establish temporal irreversibility or mechanics.

## Freeze and verification

Raw base:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/`.
Output:`runs/S04-E021-R001/`; guard sidecars adjacent under runs/.
All10 output files and3 guard log/receipt sidecars made read-only after their
processes exited; the approval artifact also made read-only. Recoverable
permission freeze, not cryptographic immutability; no source payload permissions
changed. No files deleted or overwritten. Ordinary-output inventory uses paths,
sizes and mtimes rather than inventing routine package hashes.

Verifier:`verify_r001_outputs.py`, added after the producer run, never imported
by it. It reads only saved outputs; no source trajectory, fitting or rendering.
One verifier execution returned VERIFIED_SAVED_OUTPUTS, recording:

- exact expected10-file set plus3 sidecars; bound code/run/design/lock and child
  identities; all successful receipts/exits; final total within cap;
- 357 unique ordered rows across121/99/82/55cycles, three fixed strata and native
  cycle weights; all finite MSE/ranges, zero negative raw area, d/history identity;
- four outer train/holdout groups, six inner models,32 features/2048sample IDs;
  finite model scales/coefficients, training identities and independent inner
  choice reconstruction without fitting;
- R/G recomputed from saved physical MSE (rtol1e-12/atol1e-14) match all-fold
  table/decision. These are audit arithmetic tolerances, not altered eps gates;
- fixed85112 sorted unique native IDs within86408, finite/bounded saved fields;
  file sizes/mtime unchanged during audit. No source-map reread was performed;
  mapping identity comes from the bounded loader and saved ID checks, not a new
  independent spatial registration qualification.

Audit/inventory:`control/S04-E021-R001_saved_output_verification.json`.
Operational consent:`control/S04-E021-R001_authorization.json`.
Both are local evidence, not a renewed execution permit.

Visual QA was completed separately: both PNGs opened,
readable labels/no blank panels; all four cases and reference1 shown. Fixed
U0.115/C20 uses FEM/V0/V1 shared physical linear scale and signed residual with
symmetric limits. Strong localisation means most domain looks dark and small
differences are visually subdued: do not infer spatial closure from appearance.
No new plot/render generated to make the result look stronger.

Per-figure explanations are tracked as `V0_V1_holdouts.md` and
`u0115_C20_raw.md`. Byte-identical PNG copies plus these sidecars were checked
in the separate local `analysis/figure_sidecars` directory with the project
native validator: two figures, two unique sidecars, zero errors. The frozen run
directory remained unchanged.

![All-fold physical raw ratios](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001/V0_V1_holdouts.png)

Fixed field image and generated README_analysis.md remain in the frozen output.
The raw README's word “real-data” means actual existing scientific archives
versus generated engineering fixtures; evidence domain here is SYNTHETIC,
not real-road/physical experimental data.

## Interpretation and unique next step

Local bounded verdict:supports the preregistered directional DEVELOPMENT
diagnostic; independent evidence review pending, so not final Evidence Ready.
The minimum single-raw repair has held-out-Umax signal on these four viewed
archives, unlike the previous R002 physical-raw regression. The two designs
jointly change target/output/selector: no causal attribution to one component
or statistical claim follows. Keep R002's original verdict unchanged.

Blocked regardless:physical/teacher qualification, active/process-zone or
energy closure, forecast/lifetime, real-road transfer, fresh confirmation,
superiority to a direct-data model, NN need or multi-objective gradient conflict.
Worst-case3.26% is directional, not a qualified practical/significant margin.

Unique next action:request human approval to send a read-only independent
evidence-review request for this exact frozen package/protocol. Reviewer should
check splits/scales/selection/output metrics, integrity and bounded conclusion;
do not ask it to rerun fits/tests/render or open confirmation. No outgoing
message sent in this result turn. No new fit or extra arm proposed for execution.
After review, decide the smallest further validation separately; do not
automatically activate S04-E017/MOO/NN or U0.1175/U0.125. Main chat remains sole
execution owner; shared Obsidian/Roadmap updated with these boundaries.

## Consolidation and ownership — 2026-10-15

At the user's explicit direction this main chat
`01a1131d-017c-7b03-a95a-ad73ba8fcc9c` now owns all record/Obsidian finalization
and any later approved review send. Coordination chat019fa60d-9b72-72f3-a711-ab2126197932
has completed its turn; no duplicate producer was launched. Its9c1bbcf commit
already includes this result/verifier and two per-figure explanations; all are
preserved as the common result record, not replaced by a competing receipt.
Method chat remains read-only; no messaging, extra fitting/tests/rendering or
new metric computation in this consolidation. Recorded guard size versus final
inventory and figure-scale wording reconciled, no scientific rule/result change.
The review draft is prepared for per-send approval, NOT SENT. It uses direct
professional Chinese following the user's supplied instructions, without a
claim of exact style imitation. The earlier unsent English draft is retained
as history, not another active send or an inherited approval.

## Independent review accepted — 2026-10-15

Review passed with no blocking findings; main chat reconciled every point in
evidence_review.md. E021 closes only as a positive directional-development
diagnostic, not physical/teacher/confirmation qualification. No retry/refit.

Important boundary:U0.11 C41+ has81cycles and its mean physical MSE changes from
4271.04641540382 to4409.53477488090; RMSE ratio1.01608312895644, an increase of
1.6083%. Thus four balanced-total and four early ratios improve, NOT all stages.
This explanatory finding does not change the preregistered Q/early-guard rule.
Independent audit did not replay all point predictions:other cycles use saved
MSE; inner selection uses saved R/G/code. Do not call it complete numerical
reproduction. Existing aggregate figures and sidecars keep their bounded meaning.

Following the user's separately approved handoff, next_validation_plan_v1.md
proposes only a no-refit inference replay on already-admitted development data.
It is unimplemented/unexecuted and not a new claim/holdout or run authorization.
No extra experiment, source export, renderer, NN or MOO started; confirmation
and S04-E017 remain closed/held. Obsidian updated solely by this main chat.
