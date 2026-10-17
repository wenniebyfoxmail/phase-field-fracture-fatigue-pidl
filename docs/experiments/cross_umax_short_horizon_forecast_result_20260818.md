# Cross-Umax short-horizon field forecast — development result

**Decision:** `DIAGNOSTIC_NEGATIVE__NO_ARCHITECTURE_EXPANSION`  
**Stiffness:** `STIFFNESS_INCREMENTAL_NEGATIVE`  
**Scope:** exact-FEM-state, same Hard5 family, development-only

The frozen protocol is
[`cross_umax_short_horizon_forecast_preregistration_20260818.md`](cross_umax_short_horizon_forecast_preregistration_20260818.md).
The local evidence package is
`local_archive/after_strict_setting_alignment/fem/cross_umax_short_horizon_forecast_v1_20260818/`.

## Main result

The fixed ridge passed the loose absolute field thresholds because adjacent
cycles are highly similar, but failed the predeclared incremental gate at both
horizons. It achieved the required three-of-four primary error improvement on
zero of three ordinary held-out Umax trajectories.

| Horizon | folds with 3/4 primary improvements | worst primary error ratio vs persistence | incremental gate |
|---:|---:|---:|---|
| h1 | 0/3 | 5.397 | fail |
| h2 | 0/3 | 4.892 | fail |

The failure is driven by damage and degradation. The ridge improved history and
usually raw/active energy, but its ordinary damage MAE was 2.73-5.40 times
persistence at h1 and 2.71-4.89 times persistence at h2. It therefore does not
qualify as a four-state transition operator.

## Strong simple control

The causal two-frame secant was the strongest general control. Relative to
persistence it reduced ordinary active log-MAE by:

| Umax | h1 reduction | h2 reduction |
|---:|---:|---:|
| 0.11 | 14.1% | 33.8% |
| 0.12 | 17.2% | 41.6% |
| 0.13 | 41.1% | 48.2% |

Secant also reduced history/degradation errors sharply. Damage improvement was
small and not universal: U0.13 worsened by 2.8% at h1 and 6.6% at h2. This is a
useful bounded result: recent state velocity carries short-horizon energetic
information, but not reliable transition-topology information.

## Stiffness ablation

Adding only `K_t/K_1`, `Delta log K_t`, and `Delta2 log K_t` did not satisfy the
frozen all-trajectory incremental rule at either horizon. It often improved
U0.11/U0.12 damage/history components, but worsened multiple U0.13 components
and sometimes active-energy error. Stiffness remains a causal monitoring signal
and first-detect precursor correlate; it is not promoted as a general field
forecast input by this test.

## Uncertainty

The three-member trajectory-jackknife spread was severely under-covering. On
ordinary windows, nominal-90% descriptive coverage ranged approximately:

- damage: 0.45-0.69;
- history: 0.04-0.18;
- degradation: 0.10-0.24;
- raw energy: 0.10-0.26.

These are explicitly uncalibrated diagnostics. They reinforce that three
trajectories cannot support a calibrated uncertainty claim.

## Claim boundary and next action

This result rejects only the frozen coordinate-free local ridge and its fixed
stiffness augmentation as a transferable four-field `t+1/t+2` map. It does not
reject short-horizon forecasting in general.

Do not escalate to a neural operator, GNN, penalty sweep, or new producer
trajectory from this gate. Retain two-frame secant as the honest short-horizon
control. Topology remains a localization prior, while PIDL-strain remains a
synthetic observation-support diagnostic rather than DIC evidence.

An initial run produced identical metrics but emitted BLAS warnings and is
preserved as
`cross_umax_short_horizon_forecast_v1_20260818_warning_v1/`. The final package
uses an explicit finite check and `einsum`; its metrics and decisions are
byte-identical to the warning run. The earlier CSV-write failure is preserved
as `cross_umax_short_horizon_forecast_v1_20260818_failed_v0/`.

