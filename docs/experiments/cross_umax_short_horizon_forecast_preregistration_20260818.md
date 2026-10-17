# Cross-Umax short-horizon field forecast — frozen development gate

**Status:** preregistered development-only diagnostic  
**Claim class:** trajectory-sufficiency / framework-development  
**Owner:** Mac-PIDL offline analysis  
**Independent units:** three already-seen Hard5 Umax trajectories

## PIDL Experiment Gate

- **Mechanism question:** given exact FEM state fields at calendar cycle `t`, one
  causal field increment, and forcing observed through `t`, is there transferable
  information for predicting fields at `t+1` and recursively at `t+2`?
- **Claim changed if success:** a fixed low-capacity transition is worth freezing
  before acquiring a genuinely unseen same-family trajectory.
- **Claim changed if failure:** stop temporal architecture expansion on these
  three trajectories; current-state history is insufficient for this fixed map.
- **Cheaper diagnostic first:** persistence and physically projected two-frame
  secant controls; no neural training and no producer run.
- **Minimal output asset:** one metrics CSV, one fold-decision CSV, one manifest,
  and one decision note.
- **Code/producer alignment:** deterministic NumPy/SciPy analysis on Mac. No PIDL
  training, FEM solve, GPU job, or new state generation.
- **Success criteria:** the frozen ordinary-window absolute and incremental gates
  below; first-detect stress cases cannot rescue an ordinary-window failure.
- **Failure criteria:** any non-finite/range failure, ordinary incremental gate
  failure, or catastrophic first-detect stress degradation.
- **Registry destination:** the existing cross-Umax experiment family; update the
  curated registry only if this development gate changes the active decision.
- **Decision:** diagnose first.

## Data and event semantics

Use only the three matched FEM trajectories under
`Hard5_eta0_5step_Umax_011_012_013_20260729`.

| Umax | continuous cycles | first detect | confirmed — forbidden selector |
|---:|---:|---:|---:|
| 0.11 | c1-c125 | c122 | c125 |
| 0.12 | c1-c89 | c83 | c86 |
| 0.13 | c1-c62 | c59 | c62 |

The event is always **first detect**. Confirmed cycles and normalized lifetime
are forbidden. Model fitting starts at c20. An origin is admitted while the
state at `t` is pre-first-detect and the requested target does not exceed first
detect. Ordinary versus stress labels are assigned only after prediction.

Outer folds are whole trajectories:

1. train 0.12 + 0.13, challenge 0.11;
2. train 0.11 + 0.13, challenge 0.12;
3. train 0.11 + 0.12, challenge 0.13.

All three challenges are `development-only`, never independent validation.

## State and models

The transformed element state is

`X = [d, log10(alpha_bar + 1e-8), f, log10(psi_raw + 1e-12)]`.

Controls:

- `persistence`: carry `X_t` forward;
- `secant`: `X_t + h * (X_t - X_(t-1))`, followed by the same physical projection.

The sole learned point challenger is a standardized ridge map with fixed
`lambda=1.0`:

`[1, Umax, X_t, X_t-X_(t-1)] -> X_(t+1)-X_t`.

Training moments and normal equations are averaged within trajectory first and
then equally across the two training trajectories. Cell-cycle records estimate
deterministic transition statistics; they are not independent replicates.
Every feature and target standardization statistic is computed strictly from
the two training trajectories inside that outer fold and is frozen before the
held-out Umax is transformed. No holdout distribution enters preprocessing.

The sole stiffness ablation appends exactly three causal scalars:

`[K_t/K_1, Delta log K_t, Delta2 log K_t]`,

where `K_t=abs(F_peak,t)/Umax`. No compliance duplicate is included. At h2 the
stiffness vector observed at origin `t` is held fixed; future reaction is not
available and is never used.

For h2, both ridge models are recursively applied to their own h1 prediction;
true `X_(t+1)` is forbidden. Physical projection enforces nondecreasing damage
and history, nonincreasing degradation, bounded damage/degradation, and finite
raw energy.

No coordinate, cycle index, event distance, first-detect label, final lifetime,
future reaction, or target-derived mask enters fitting.

## Metrics and frozen decisions

Report each Umax, horizon, and ordinary/stress stratum separately. Primary
errors are damage MAE, history log-MAE, degradation MAE, and raw log-MAE.
Safeguards are active log-MAE/correlation, FEM-p99 absolute IoU, own-p99 IoU,
and absolute support-area ratio.

Ordinary absolute reliability requires, at both horizons and on all folds:

- damage MAE <= 0.020;
- history log-MAE <= 0.030;
- active log-MAE <= 0.50;
- active correlation >= 0.80;
- absolute and own-p99 IoU >= 0.50;
- support-area ratio in [0.67, 1.50].

The fixed ridge incremental gate requires at least three of the four primary
errors to improve over persistence on at least two of three ordinary challenge
trajectories at each horizon, with no primary error ratio above 1.25.

The stiffness ablation is positive only if it improves at least three of the
four primary errors relative to fixed ridge on every ordinary challenge
trajectory at each horizon, with no primary error ratio above 1.10. Otherwise
stiffness remains a monitoring correlate, not a promoted forecast input.

A first-detect stress case is catastrophic if any primary error is non-finite or
more than twice its comparator. Stress success cannot repair ordinary failure.

## Uncertainty boundary

For each fold, fit one model to each training trajectory separately in addition
to the pooled equal-trajectory fit. Their three forecasts define an
`uncalibrated descriptive ensemble`. Report empirical 90% cell coverage and
width, but do not claim trajectory-level calibration or treat cells/windows as
independent calibration samples.

## Stop rule

No ridge penalty sweep, feature search, mask tuning, alternative event
alignment, neural operator, GNN, or producer trajectory is authorized by this
gate. A positive result authorizes only a frozen request for at least one
genuinely unseen same-family Umax trajectory.
