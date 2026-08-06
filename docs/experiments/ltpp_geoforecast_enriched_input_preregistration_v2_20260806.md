# LTPP-GeoForecast source-available enriched-input ablation preregistration v2

Date: 2026-08-06  
Status: `CHATGPT_PRO_MINIMAL_REVISIONS_APPLIED__CANDIDATE_FOR_INPUT_FREEZE__NO_FIT_AUTHORIZED`

Revision receipt: ChatGPT Pro reviewed the pre-revision file with SHA-256
`92b1f5081bc9db9d2911d72cdce59369941a959bfc11bfb9aa3ee8713e0a7fc8`
and returned `REVISE_BEFORE_INPUT_FREEZE`. The six requested documentation-only
changes are incorporated below: rationale for `nu=4`, the 10%/4-of-6/5% gates,
positive-only growth, and an exact prior-predictive check. No endpoint, feature,
split, model family, or outcome has changed.

This document replaces the ambiguous parts of the initial enriched-input plan.
It is a review draft, not a completed data freeze and not authorization to fit a
model. The confirmatory task is a forecast made at the source survey with only
information available by that date. Realized source-to-target traffic and
climate are reserved for one explicitly non-confirmatory oracle diagnostic.

## PIDL Experiment Gate

- **Mechanism question:** do source-available traffic demand, pavement
  structure, and FWD response add stable cross-section predictive information
  for future positive crack-length growth beyond source geometry and trailing
  climate?
- **Claim changed if success:** a small observation-conditioned model has
  credible incremental predictive value and justifies a later, separately
  preregistered spatial-allocation study.
- **Claim changed if failure:** these section-level channels are insufficient
  under the frozen six-section protocol; failure does not establish that the
  variables are physically irrelevant and does not authorize architecture
  search.
- **Cheaper diagnostic first:** freeze and validate the source-cutoff feature
  table, including traffic-history and valid-drop FWD coverage, before any fit.
- **Minimal output asset:** one immutable feature table, one split receipt, one
  ablation table, and one decision note.
- **Code/producer alignment:** acquisition and this small statistical model are
  lightweight Mac tasks. No PIDL/FEM training, Taobo run, or CSD3 run is part of
  this experiment.
- **Success criteria:** Section 11 below; they may not be changed after the
  feature-table hash is recorded.
- **Failure criteria:** incomplete required inputs, a source-cutoff violation,
  invalid FWD normalization, failed sampler diagnostics, or failure of the
  locked predictive-value gates.
- **Registry destination:**
  `docs/experiments/ltpp_geoforecast_enriched_input_preregistration_v2_20260806.md`
  and, after a terminal result only, `docs/research_frontier.md`.
- **Decision:** `diagnose first`; external review and the immutable input gate
  remain outstanding, so fitting is prohibited.

## 1. Confirmatory question and claim boundary

The confirmatory question is:

> At an LTPP source survey, can measurements already available by that date
> improve prediction of positive crack-length growth at a declared future
> horizon on a completely unseen section?

This experiment estimates **incremental predictive value under a fixed feature
order**. It does not identify causal effects of ESAL, structure, climate, or
FWD. Because the order is fixed, an increment is conditional on all earlier
blocks and must not be described as a standalone or causal contribution.

The intended paper-level description is “we evaluated whether additional
observational channels provide measurable predictive value,” not “we developed
a predictive model.” The latter would overstate what 31 transitions can support.

## 2. Immutable label and transition scope

The label scope remains fixed:

- six sections: `06-1253`, `06-2041`, `06-2647`, `06-8149`, `06-8150`, and
  `06-8201`;
- 37 adjudicated survey states;
- 31 adjacent-survey transitions;
- 25 development transitions and six frozen final-time transitions;
- no relabeling, section addition/removal, panel substitution, or target-driven
  exclusion;
- no transition crossing a detected maintenance, reconstruction, construction,
  or out-of-study reset.

Existing immutable receipts:

| asset | SHA-256 |
|---|---|
| adjudicated manifest | `6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad` |
| transition manifest | `1c38725d23a9cdaea69e3f71b5eaaa6469d02371c85de7a3b2061ba79e92e918` |
| frozen baseline manifest | `e70564d3e06c81517268c0974845759e7a307769ee3478534cd8f08b8bee2b55` |

The enriched raw package and derived feature table do not yet exist as frozen
assets. Section 13 is therefore a blocking gate, not an administrative detail.

## 3. Forecast origin, information set, and horizon

For transition `i`, let `t_i` be the source survey date, `T_i` the frozen target
survey date, and `h_i=(T_i-t_i)/365.25` years. In benchmark evaluation, `h_i` is
treated as the declared forecast horizon. The information cutoff is the end of
`t_i`; no observation with timestamp after `t_i` may enter a confirmatory
feature.

This creates two deliberately separated tasks:

1. **Primary source-available forecast:** uses only data dated on or before
   `t_i`. This is the only claim-bearing task.
2. **Oracle exposure diagnostic:** replaces trailing climate and traffic with
   the realized values over `[t_i,T_i)`. It is labelled
   `ORACLE_CONDITIONAL_DIAGNOSTIC`, cannot satisfy a success gate, and cannot be
   presented as a deployable source-time forecast.

The existing source-to-target climate join is outcome-leakage-safe but not
deployment-available. It therefore belongs only to the oracle diagnostic in
this preregistration.

## 4. Confirmatory endpoint and reported outputs

For each transition, define:

\[
\Delta L_i^+=\max(0,L_{i,T}-L_{i,t}).
\]

Detected maintenance and reset transitions are already excluded. Remaining
negative signed changes can still reflect annotation/registration variability,
unrecorded treatment, or apparent disappearance and are not interpreted as
physical crack healing. Positive-only growth is therefore the sole
confirmatory endpoint; the complete signed changes remain visible as a
descriptive diagnostic.

The fitted response is `log1p(Delta L positive)`. The primary metric is pooled
LOSO mean absolute error on the original metre scale:

\[
\operatorname{MAE}_{\Delta L^+}=
\frac{1}{31}\sum_i |\widehat{\Delta L_i^+}-\Delta L_i^+|.
\]

Every posterior-predictive draw is returned to metres by
`max(0, exp(y_draw)-1)`. The point forecast is the median of these transformed
draws. This fixed truncation respects the non-negative endpoint despite the
Student-t likelihood's real-valued support. Persistence predicts
`Delta L positive = 0`.

Secondary confirmatory outputs are limited to:

- section-wise MAE for the six held-out sections;
- nominal-90% posterior-predictive interval coverage on `Delta L positive`;
- empirical posterior-predictive CRPS on `Delta L positive`;
- RMSE on `Delta L positive`, reported but not used for promotion.

Raw signed length change is reported descriptively so the truncation is visible,
but it is not an alternative endpoint. This scalar model does **not** generate
future crack placement. Geometry F1, IoU, crack-tip error, and new-geometry area
are removed from the confirmatory gate. A later spatial model requires a new
preregistration and cannot rescue a failed scalar result.

## 5. Fixed feature table and ablation order

All four models use the same qualified transition rows. No feature selection,
PCA, interaction search, polynomial expansion, or automatic term deletion is
allowed.

### M0: source geometry + trailing climate

| ID | frozen feature | exact source-time definition | transform |
|---|---|---|---|
| G1 | source crack length | `source_geometry.crack_line_length_m` at `t_i` | `log1p` |
| G2 | source crack area | `source_geometry.crack_area_m2` at `t_i` | `log1p` |
| G3 | forecast horizon | `(T_i-t_i)/365.25` years | none |
| C1 | trailing temperature | day-weighted mean air temperature over `[t_i-365.25 d,t_i)` | none |
| C2 | trailing precipitation | accumulated precipitation over `[t_i-365.25 d,t_i)` in mm | `log1p` |

### M1: M0 + source-available traffic

The traffic year is the latest complete calendar year strictly before the
source survey year: `y_i = year(t_i)-1`.

| ID | official source field | exact definition | transform |
|---|---|---|---|
| T1 | `TRF_TREND.ANNUAL_ESAL_TREND` | value for `YEAR=y_i` and source-active `CONSTRUCTION_NO` | `log1p` |
| T2 | `TRF_TREND.AADTT_ALL_TRUCKS_TREND` | value for `YEAR=y_i` and source-active `CONSTRUCTION_NO` | `log1p` |

`ESAL_SOURCE` and `AADTT_SOURCE` are retained as provenance columns, not model
features. No class-specific AADTT, GESAL, GVW, cumulative volume, interpolation
from future years, or source-to-target realized traffic may enter M1.

### M2: M1 + source-effective structure

Rows come only from `SECTION_LAYER_STRUCTURE` with the source-active
`CONSTRUCTION_NO`, `RECORD_STATUS != 'D'`, and non-null positive
`REPR_THICKNESS`. InfoPave's converted millimetre value is used.

| ID | exact definition | transform |
|---|---|---|
| S1 | top structural-layer thickness: `REPR_THICKNESS` at the maximum valid `LAYER_NO` | none |
| S2 | total non-subgrade thickness: sum `REPR_THICKNESS` over valid rows with `LAYER_NO > 1` | none |

No material-category dummy, decoded-material grouping, backcalculated thickness,
or target-time construction record is used in v2. This removes the earlier
open-ended material encoding and keeps the structure block at two coefficients.

### M3: M2 + source-prior FWD

The selected FWD test is the latest `MON_DEFL_MASTER.TEST_DATE <= t_i` with the
same `CONSTRUCTION_NO`. The test must contain valid `MON_DEFL_LOC_INFO` and
`MON_DEFL_DROP_DATA` rows in the mapped `0-50 ft` panel (`POINT_LOC` from 0
through 15.24 m), with `RECORD_STATUS != 'D'`, positive `DROP_LOAD`, positive
`PEAK_DEFL_1`, and no non-decreasing-deflection quality flag. The device
configuration must verify that sensor 1 is the loading-centre sensor; otherwise
the transition fails the input gate.

For every valid drop, normalize loading-centre deflection to 566 kPa plate
pressure:

\[
D_{0,566}=\texttt{PEAK_DEFL_1}\frac{566}{\texttt{DROP_LOAD}}.
\]

The test-level value is the median `D0,566` across all valid drops and mapped
panel locations on that latest date.

| ID | exact definition | transform |
|---|---|---|
| F1 | median normalized loading-centre deflection `D0,566` in micrometres | `log1p` |
| F2 | `(t_i - latest_valid_FWD_date)/365.25` years | none |

SCI, BDI, BCI, the complete deflection basin, and backcalculated modulus are
excluded. There is no FWD missingness coefficient because preflight found a
source-prior test for every transition. If valid-drop qualification makes any
FWD value missing, the formal run returns `BLOCKED_INPUT_COVERAGE`; it does not
impute, drop a row, or substitute another FWD metric.

The confirmatory model has exactly 5, 7, 9, and 11 continuous predictors in
M0--M3 respectively.

All source units above remain unchanged through feature construction. Only the
declared transforms and fold-local z-score are allowed; global normalization is
never allowed.

## 6. Missingness, transformations, and fold isolation

- All 31 transitions must have all 11 M3 features before fitting. M0--M3 must
  use the identical 31-row set.
- No confirmatory value is imputed. Any absent required value blocks fitting and
  returns a coverage report for renewed external review.
- The earlier `06-1253` final-interval 0.8333 realized-ESAL coverage does not
  affect the primary source-available model. In the oracle diagnostic it is not
  filled from future years; that oracle row is reported as unavailable and the
  oracle remains descriptive.
- The transforms in Section 5 are fixed before standardization.
- Each outer fold standardizes continuous predictors using only its training
  rows. The held-out section uses those training means and standard deviations.
- For the frozen future-time evaluation, standardization uses only the 25
  development transitions.
- If a feature has zero variance within a training fold, its standardized value
  is fixed to zero and no coefficient is estimated for that fold. The event is
  recorded; it is not a reason to choose another feature.

## 7. Single fixed probabilistic algorithm

The only allowed model family is a Bayesian hierarchical shrinkage regression:

\[
y_i=\log(1+\Delta L_i^+),\qquad
y_i\sim\operatorname{StudentT}(\nu=4,\mu_i,\sigma),
\]

The degrees of freedom are fixed a priori at `nu=4`, not learned or selected.
This gives finite variance while retaining substantially heavier tails than a
Gaussian for occasional extreme crack-growth observations. It is a robustness
choice, not a fitted parameter, and no alternate `nu` is evaluated.

\[
\mu_i=\alpha+X_i\beta+b_{s(i)}.
\]

After fold-local predictor standardization, the fixed priors are:

\[
\alpha\sim N(0,2.5^2),\quad
\beta_j\sim N(0,1),\quad
b_s\sim N(0,\sigma_s^2),
\]

\[
\sigma\sim\operatorname{HalfNormal}(1),\quad
\sigma_s\sim\operatorname{HalfNormal}(1).
\]

This is the probabilistic analogue of ridge shrinkage, but there is no
ridge-versus-Bayesian choice and no tuned `lambda`. The fixed posterior sampler
contract is:

- NUTS;
- four chains;
- 2,000 warm-up and 2,000 retained draws per chain;
- `target_accept=0.90`;
- deterministic seed `260806 + outer_fold_index`;
- required diagnostics: all `R-hat < 1.01`, bulk ESS at least 400, tail ESS at
  least 400, and zero post-warm-up divergences.

One computational retry is allowed only when diagnostics fail: 4,000 warm-up
draws and `target_accept=0.95`, with all model definitions unchanged. Continued
failure yields `INVALID_SAMPLER_DIAGNOSTICS`; it does not authorize different
priors, likelihoods, features, or algorithms.

For a LOSO held-out section, predictions integrate a new section effect
`b_new ~ N(0,sigma_s^2)` rather than estimating an effect from held-out labels.
For the frozen future-time axis, each section effect may be conditioned only on
that section's development transitions.

Random Forest, boosted trees, neural networks, GNNs, neural operators, PIDL,
FEM surrogates, alternate likelihoods, and alternate priors are excluded from
the confirmatory run.

### Prior-predictive check before outcome fitting

After the 31-row feature table and split receipts are frozen, but before any
outcome likelihood is fitted, generate 500 joint prior draws for every M0--M3
model on every LOSO fold and the frozen future-time design. Each draw produces
one predictive value for every evaluation row and uses the same non-negative
inverse transformation defined in Section 4. Seeds are fixed as
`260807 + 100*model_index + fold_index`, where model indices M0--M3 are 0--3 and
the future-time design uses fold index 6.

The benchmark-scale plausibility ceiling is fixed from source geometry only:

\[
L_{prior\_cap}=2\max_i L_{i,t}=100.189733\ \mathrm{m}.
\]

For each model/fold, report the transformed predictive median, 5th and 95th
percentiles, maximum, zero fraction, and fraction above `L_prior_cap`. The check
passes only if no more than 1% of all row-level prior-predictive values in every
model/fold exceed the fixed ceiling. This is a scale-sanity gate, not evidence
of predictive performance. If it fails, return
`PRIOR_PREDICTIVE_REVIEW_REQUIRED`; do not fit outcomes, tune the priors, or try
another likelihood without a new external review and a newly hashed
preregistration.

## 8. Locked validation axes

### Primary: leave-one-section-out

Run six outer folds. Each fold holds out every transition from one complete
section and fits on the other five sections. Held-out outcomes may not affect
standardization, sampler choices, feature definitions, or any decision.

### Secondary: frozen future-time test

Fit once on the 25 transitions already marked `development_transition=true` and
evaluate once on the six transitions already marked `future_time_test=true`.
No future-time result may change the model. This axis tests later-time
forecasting on known sections and cannot replace the primary unseen-section
conclusion.

The original frozen split receipts must be reused byte-for-byte. Random splits
and transition-level cross-validation are prohibited.

## 9. Oracle conditional diagnostic

After the primary M0--M3 outputs are sealed, run exactly one predeclared
diagnostic `O3` with the M3 algorithm and structure/FWD rules unchanged,
replacing:

- C1/C2 by realized climate over `[t_i,T_i)`; and
- T1/T2 by overlap-weighted realized ESAL and mean AADTT over `[t_i,T_i)`.

The oracle set is fixed to the 30 transitions with complete realized-traffic
coverage; `06-1253-T07` is excluded because its realized ESAL coverage is
`0.8333`. For an apples-to-apples descriptive contrast, sealed M3 predictions
are also summarized on those same 30 rows as `M3_MATCHED30`; the 31-row primary
M3 result remains unchanged. If any other realized-exposure value is absent,
O3 returns `ORACLE_INPUT_INCOMPLETE` and no value is imputed.

`O3` answers whether perfect knowledge of future exposure would have been
informative. It is not deployable, receives no pass/fail status, and cannot
rescue M3. If O3 improves while M3 does not, the permitted interpretation is
that exposure availability or forecastability may be a bottleneck. It is not
evidence that traffic or climate caused the observed crack growth.

## 10. Comparisons and fixed execution order

Execute and report every model regardless of an earlier increment's outcome:

1. `B0`: persistence, `Delta L positive = 0`;
2. `M0`: source geometry + trailing climate;
3. `M1`: M0 + source-available traffic;
4. `M2`: M1 + source-effective structure;
5. `M3`: M2 + source-prior FWD;
6. predeclared non-confirmatory `O3` after sealing items 1--5.

The claim-bearing incremental contrasts are M1 versus M0, M2 versus M1, and M3
versus M2. The overall contrast is M3 versus persistence. A failed earlier block
is retained in later models; no block is removed or reordered.

## 11. Locked success and failure rules

An individual block has incremental predictive value only if all conditions
hold against the immediately preceding model on primary LOSO:

1. pooled `MAE_DeltaLpositive` decreases by at least 10%;
2. section-wise MAE improves in at least four of six held-out sections;
3. nominal-90% interval coverage is between 85% and 95%, which for 31 rows means
   exactly 27--29 covered observations;
4. CRPS does not worsen by more than 5%.

These constants are engineering relevance gates fixed before enriched-input
fitting, not statistical significance thresholds. The 10% MAE reduction is the
minimum practically meaningful improvement and is retained from the earlier
locked benchmark gate rather than chosen after the enriched result. Four of six
requires a strict simple majority of unseen sections so that a pooled gain
cannot be driven by a minority of roads. The 5% CRPS tolerance prevents a point
prediction gain from being purchased with material deterioration in
probabilistic accuracy; CRPS penalizes both miscalibration and unnecessarily
diffuse predictive distributions.

Overall success additionally requires M3 versus persistence to satisfy items
1--3 and not worsen CRPS by more than 5%.

Future-time results, RMSE, raw signed changes, and O3 are reported but do not
promote a failed primary result. A section-cluster bootstrap with 10,000 draws
and seed `260806` reports descriptive 95% intervals for MAE differences; these
intervals are not an additional pass/fail gate and no p-value is used.

Allowed terminal interpretations are:

- **increment passes:** the named block provides incremental cross-section
  predictive value under this ordering and protocol;
- **only uncertainty improves:** the block improves probabilistic
  representation but does not establish sufficient point-prediction gain;
- **increment fails:** the block does not show stable incremental predictive
  value in these six sections and 31 transitions;
- **input or sampler gate fails:** no predictive claim is made.

No result may be generalized to “the variable is useless,” “the variable is
unrelated to cracking,” or a causal statement.

## 12. Prohibited post-result actions

After the immutable feature-table hash is recorded, do not:

- change the endpoint, transforms, priors, likelihood, sampler contract, model
  family, feature list, feature order, or success thresholds;
- use realized future climate/traffic in M0--M3;
- select among AADTT variants, traffic classes, material encodings, FWD metrics,
  sensor combinations, backcalculation outputs, or structure summaries;
- remove a section or transition because of its result;
- tune on a LOSO held-out section or the six future-time rows;
- substitute geometry metrics as the headline outcome;
- report only successful increments;
- describe O3 as deployable or causal;
- launch an architecture rescue.

Any later alternative is a new `Exploratory analyses` branch with a new ledger
entry and cannot alter the confirmatory decision.

## 13. Immutable pre-fit evidence gate

Training remains blocked until all of the following exist and validate:

1. a raw-data manifest listing every InfoPave table, query/filter receipt,
   acquisition timestamp, row count, unit, and file SHA-256;
2. an 11-feature, 31-row table with transition ID, source cutoff, provenance
   dates, quality fields, and SHA-256;
3. a coverage report proving every confirmatory value existed by the source
   cutoff and every M3 value passed the exact rules above;
4. byte-identical LOSO and future-time split receipts linked to the existing
   baseline manifest;
5. the ChatGPT Pro review saved locally with adopted, modified, and rejected
   recommendations recorded in the attempt ledger;
6. a final preregistration file with timestamp and SHA-256;
7. implementation commit SHA, Python/package lock, clean/dirty status, runner
   path, command, output root, and deterministic seeds;
8. a no-fit preflight that exits non-zero on any missing hash, coverage failure,
   source-after-cutoff timestamp, or split mismatch.
9. the prior-predictive check in Section 7, with its receipt and deterministic
   seed map, passes before any outcome fit.

Only after items 1--9 pass may the status change to
`PREREGISTERED__FIT_AUTHORIZED`. Until then the only valid status is
`DRAFT_OR_BLOCKED__NO_FIT`.

## 14. Questions for ChatGPT Pro review

The external reviewer should explicitly adopt, modify, or reject each item:

1. source-available primary task plus one non-confirmatory realized-exposure
   oracle diagnostic;
2. scalar `Delta L positive` endpoint and removal of spatial metrics;
3. the exact 11-feature sequence and source-time joins;
4. normalized `D0,566 + FWD age` and exclusion of backcalculated alternatives;
5. the fixed Bayesian Student-t hierarchical model and unseen-section random
   effect integration;
6. LOSO primary, frozen future-time secondary, and the four-part 10%/4-of-6/
   coverage/CRPS gate;
7. the fail-closed immutable evidence gate before any fit.

The reviewer should not choose a model after seeing outcomes. Any proposed
change must be incorporated and re-hashed before feature construction or
fitting.

## 15. ChatGPT Pro review disposition

The external review returned `REVISE_BEFORE_INPUT_FREEZE`, not rejection. Its
item-level disposition was:

- adopt source-only primary forecasting;
- modify the positive endpoint only by documenting its rationale;
- adopt removal of spatial metrics;
- adopt the exact 11-feature table;
- retain fixed `nu=4` but document its robustness rationale and add a locked
  prior-predictive check;
- adopt LOSO primary plus frozen future-time secondary;
- retain the success thresholds but document why 10%, four of six, and 5% CRPS
  are used;
- adopt the fail-closed missing-data rule and claim boundary;
- restate the small-sample contribution as information-value evaluation rather
  than model development.

All requested changes are documentation and pre-fit diagnostic constraints.
The external review is recorded in
`docs/reviews/ltpp_geoforecast_enriched_input_chatgpt_pro_review_20260806.md`.
This local revision is a candidate for input freeze, not authorization to fit.
