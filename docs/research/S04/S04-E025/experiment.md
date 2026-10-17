# S04-E025 — one fatigue-state/raw interaction, exploratory matched ridge

Prepared 2026-10-17, Europe/London. Storyline S04. New Experiment, not an E021
retry or revised verdict. Design authority: user approval of
`82cd09258bb09604a3f89809dd7005ac77631b8c` for protocol, input inventory, minimal
implementation and independent code review. **No real input access, fitting,
worker/guard execution, confirmation access or new tests are approved now.**
Status: IMPLEMENTED_PENDING_INDEPENDENT_STATIC_REVIEW; scientific evidence NONE.
Exact future execution card/command and human approval are separate.

## 1. Question and evidence boundary

With the same physical raw residual objective, can one explicit PIN-only
fatigue-state × raw interaction reduce already-viewed U0.11 late error relative
to a newly fitted, identically configured additive baseline? What early/overall
cost accompanies it? Only the representation changes between arms.

Prior E021/ATTR saved records motivate the hypothesis; they do not establish
physical phase causation, gradient conflict, source authenticity or absence of
a common upstream cause. No old result, threshold, cycle or source is removed.
The approved proposal in E021 is unchanged. This is C2 synthetic, same-state,
retrospective native-archive imitation, not a qualified physical teacher,
future forecast, fresh holdout, confirmation or road-validation claim. U0.11
helped form this hypothesis and must be called viewed development evaluation.

## 2. Exact input inventory and roles

`input_manifest.json` enumerates **nine exact absolute paths and inherited SHA256
identities** from the Git-held E016 paired-s4 lock. This preparation compared
Git records only, not scientific file existence, metadata, hashes or content.
Runtime uses the frozen lock plus the narrow G5 archive admission record, not
the lock's historical pending-status text as current teacher qualification.

| Role | Trajectory prefix | Scientific files |
|---|---|---|
| Public geometry | 86,408 native cells; 85,112 admitted | one mapping NPZ |
| Train only | U0.115 C1–99; U0.12 C1–82; U0.13 C1–55 | three PIN NPZ + three FEM MAT |
| Evaluation after both fits | already-viewed U0.11 C1–121 | one PIN NPZ + one FEM MAT |

236 training cycles, 121 evaluation cycles. Origin `cN_s4_post_history_commit`,
horizon 0, PIN raw-step `5*c−1`. Native geometry centers/areas/contained and
cycles/raw_steps metadata are used. PIN channels: damage, alpha_bar, fatigue_f,
psi_raw_direct. FEM labels/state checks: damage, alpha_bar, psi_raw_direct.
No FEM fatigue_f/H, audit/event files, old models/selection, ATTR four scalar
sources, extra exports or U0.1175/U0.125/confirmation data. Old event facts only
fix retrospective admitted prefixes; no event/lifetime feature. C0 is absent,
not fabricated; lag missing masks are retained. Contract B simultaneous native
s4; Contract A remains audit-only, no confirmation opening. Nominal peak match
is not exact imposed displacement equality (PIN 1, FEM 0.999999).

Future reader hashes and decodes each allowlisted file on the same no-follow
descriptor with before/after identity checks. **Hashing reads whole files;
selected NPZ/MAT variables can decompress beyond the admitted prefix before
slicing.** Permission for the future run must cover those full nine files,
not claim byte-level prefix-only access. Only fixed prefixes enter numerical
work. No linked audit/model paths are followed. Hashes are reused external-input
identities, not a new forest of routine implementation/output hashes.

## 3. The two and only two fitted arms

Unchanged original 32 causal PIN-only features include current/c−1/c−2 values,
missing masks, physical_cycle, public geometry/Umax, current native-area globals
and 9NN means. They already contain stage-related information. New column:

```text
q(c) = 1 − X32.current_global_fatigue_f
u(c,x) = X32.current_psi_raw_direct = log1p(PIN.raw/r_T)
z(c,x) = q(c) * u(c,x)
B32: X32; C33: [X32,z]
```

Both use fixed alpha=1 ridge, unpenalised intercept, float64, exactly one linear
solve each. Shared train-only h_T/r_T PIN scales, physical target
`(FEM.raw−PIN.raw)/r_T`, weighted centered feature/target moments and original
32-column normalisation. No alpha/CV/seed/proxy search, inner folds, four outer
repeats, NN/Pareto algorithm, new variable head or FEM/PINN solve.
The 33-column common weighted Gram's leading block supplies B32. Equal cases,
equal C1–20/C21–40/C41+ strata and native cell area weights; deterministic 2048
geometry positions, unchanged sampling/normalisation convention from E021.
The unnormalised centred second moment has total weight 1 (tolerance 1e-12);
standard deviations <1e-12 use sentinel 1 as before. h_T/r_T must exceed 1e-12.
No evaluation arrays enter training scales/moments/Gram. Training arrays are
released before opening U0.11. Source arrays stay resident per training set;
features/Gram/predictions are streamed by cycle, never all-cycle feature stacks.
No runtime memory or equivalence result is asserted by this preparation.

PINN stays frozen. Physical raw reconstruction is
`max(0, PIN.raw + r_T*(ystd*linear_score + ymean))`; signed latent residual is
allowed, nonfinite latent is rejected before max. Damage/history are exactly
V0's admissible outputs, not new heads or feedback states. V0 is an unfit
background, and B32 is **not** historical selected V1.

q is a fatigue-state proxy, not verified physical stage. Record train/evaluation
q range, train pre-sentinel z std, and near-constant flag (q range≤1e-12 or z
std<1e-12). Near-constant proxy is not a performance veto; it may duplicate raw
and change effective ridge shrinkage. Even an improvement cannot identify phase
mechanism. No automatic replacement proxy or third arm.

## 4. Exploratory decision, costs and numerical errors

Only primary: U0.11 C41–121, equal cycle/native-area full admitted support,
`R_late = sqrt(MSE_C33)/sqrt(MSE_B32)`. B32 late MSE must exceed 1e-24; otherwise
stop as unidentified, no floor or substituted denominator. EPS=1e-10:

| Observation after valid complete output | Interpretation |
|---|---|
| R_late < 1−EPS | DIRECTIONAL_SIGNAL; report magnitude, tiny gains are weak |
| within inclusive 1±EPS | NUMERICAL_TIE, no resolvable direction |
| R_late > 1+EPS | NO_DIRECTIONAL_GAIN for this candidate only |

Not a 5%/10%, p-value, all-case/all-variable/all-phase win requirement. Early,
middle and balanced-overall C33/B32 RMSE ratios, plus both arms vs V0, are
reported costs/context, **not fatal performance guards or metric voting**.
Auxiliary denominator≤1e-24 is null/unidentified, never a rescued ratio; only
primary non-identifiability stops interpretation. Old E021 Q/early rules stay
unchanged. No new result upgrades historical verdicts.

Finite values, state/prefix/support identity, train-only information, positive
weights/scales, output nonnegative raw, damage/history equality, exactly two
fits and all 121 evaluation cycles remain necessary validity checks. Invalid
inputs/numerics, unidentified primary, missing files or exceptions are failed/
incomplete evidence, not physical counterexamples. No arbitrary dropping of
cycles/cells or silent fallback. Worker failure records stage/type and activity;
an absent/invalid worker receipt leaves actual read/fit flags unknown.

## 5. Future one-shot resource and authorization contract

Proposed single joint Run `S04-E025-R001` output:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E025/runs/S04-E025-R001`.
Not created now. This is a new real fitting action, not reused ATTR access.
300 seconds, 2 GiB **aggregate sampled** parent/worker tree RSS, 100 MiB **all**
run output, CPU/single-thread libraries/GPU hidden. No hard OS memory guarantee
or sub-sample transient peak claim. Guard execute timer starts before Git
preflight/directory allocation; worker time shares it. Stop work at 295 seconds
for cleanup/receipt; terminal checks retain 300-second cap. Imports before guard
execute are launcher setup, not measured execution; do not claim whole process
startup is measured. All run logs, authorisation, model/table/report/PNG,
matplotlib/temp caches and receipts are accounted inside this one budget.

Guard requires a separately approved exact source commit, approval and independent
review references, explicit `--allow-real-fit`, clean tracked source/contracts,
fixed new output, and unchanged approved proposal. Child checks fixed parent,
output/environment/references and matching read-only grant before scientific
metadata access. These are accidental-use interlocks, **not authentication of
human consent or an OS sandbox**. The operator must check actual human approval.
No command/root/input override; source diffs or used output stop. Owned output
directory consumes the attempt; no overwrite, resume, retry, extension, extra
fit or confirmation opening on failure/cap. Cleanup touches only this child
process group. Preserve primary failure and receipt/cleanup errors separately.
Execution remains forbidden under current user authority.

## 6. Minimal evidence / future figure contract

Nine core output files: authorization.json, models.json, percycle.csv,
summary.json, diagnostic.png, README_analysis.md, receipt.json, run.log,
guard_receipt.json; bounded own cache directory. No full predicted trajectories.
Small models retain scales, coefficient/normalizer vectors, sample positions,
feature names and proxy status. CSV has all 121 V0/B32/C33 physical raw MSEs plus
nonnegative/raw-min and damage/history identity checks. Summary records the one
primary, three strata/overall costs, context and claim boundaries. Receipts log
source read attempts/verified identities, invocation flags, fits, code/approval/
review, timing/RSS/inventory and actual exit. A completed fit is not method success.

One same-run PNG from that CSV/summary: A all 121 physical MSE cycles of V0/B32/C33
with fixed boundaries20/40; B three fixed strata C33/B32 RMSE against1, late
primary and other costs visible. Title includes Run, viewed synthetic U0.11,
s4/horizon0, units; colour distinguishes baseline/newarms, no cropped cycles or
secondary report fit. README explains source→table→figure→one bounded question.
No figure is generated now. Figure requirements add no performance criterion.

## 7. Ownership, static preparation and next authority

Owner: this S04 main chat, sole Obsidian writer. Dedicated child-repo worktree
`codex/s04-e025-phase-interaction-20261017`, based on82cd092; preserve E021 and
all other branches/edits. Method chat `01a12d15-9b60-7280-8248-18386d6ef741`
is independent **static read-only** reviewer, not a second implementation/run.
No push/remote producer or new automation needed.

Preparation checks only stdlib AST/JSON/Git metadata and source/manifest binding;
no importing project modules, running mocks/sanity/guard/worker, scientific
metadata/content IO, numerical recomputation, fits or confirmation data.
Independent review must check source closure, information flow, identical arm
normalisation, weights/two-solves, primary/cost boundary, permission ordering,
failure receipts/cleanup and joint budget. Do not substitute static review for
dynamic correctness, resource feasibility or scientific validity. On accepted
static review, next prepare exact final command and one-shot execution card for
human approval; do not automatically run.
