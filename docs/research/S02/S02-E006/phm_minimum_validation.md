# PHM optical-label minimum pilot — proposed, no training

2026-10-17, C1 selection plus an UNEXECUTED design. The metadata-selected MnROAD NWP list has only one varying group and its separate fatigue-area capacity check has none. Both are stopped as current changing-trajectory pilots. Do not change their indicators or choose positive-growth roads to erase those outcomes.

Preferred next qualification source: PHM2019 corrected-T6 PUBLIC TRAINING optical crack-length tables. They have six described physical specimens, labelled in mm independently of the PZT signals. This is a laboratory proxy, not road validation. Use optical labels only in this minimal plan: malformed/rounded PZT waveform time is not repaired or used. Physical lineage, optical definition/error and online measurement availability still need source clarification. T7/T8 remain untouched.

## Exact proposed observation-window target

The release is irregular and has no exact1000cycle four-state windows. Do not interpolate or use actual next-observation gap as if known at origin. The following is a different, explicitly retrospective **cycle-window published-label** diagnostic, not the old fixed1000cycle problem.

Freeze nominal query5000cycles and acceptance band4500–5500cycles BEFORE model scores. This is a coverage-motivated development proposal, not an engineering-optimal horizon, not measured uncertainty and not an exact5000cycle truth. At each observed origin N with at least2 earlier optical labels, use the two immediately preceding observed label times for history. If direct true optical labels exist in [N+4500,N+5500], pick the cycle closest to N+5000, tie earlier. Use only dates/cycles to select; keep target values hidden from selection. All such origins are retained, including zero growth. No synthetic target, monotonicity enforcement, missing-cycle fill or source typo repair.

The selected future cycle is evaluation metadata only, never a feature. The target is the actual published crack length at that selected observation inside the declared band. Target availability may depend on the experiment's observation policy; report the retrospective availability-conditioned cohort. A gain would not establish fixed5000cycle accuracy, known prospective acquisition schedules or unbiased deployment value. If this narrower question is not useful, do not fit: acquire fixed-horizon labels instead.

Quarantine T4 whole specimen in the first pilot because its source cycle7054/folder67054 inconsistency is unresolved; do not auto-repair it or use the other rows to hide the ambiguity. T2 may have too few observed labels for three past states plus a future target; report any zero coverage, do not borrow missing labels. Optical T3 cycle55391 has no label and remains absent. T6 cycle0 is an author-published label baseline, not a waveform record; its physical measurement definition remains a gap. No signal file is needed for this optical-history diagnostic.

## Fixed comparison if qualifications and later authorization permit

B0: current published crack length. B1: secant through the two latest past/current optical labels, extrapolated5000cycles to the nominal query, not the unknown actual target cycle.

M0: same B1 plus fixed ridge(alpha1) residual correction, inputs=current length, recent per-cycle secant, current cycle N, and latest observed past interval. M1 same plus exactly one older secant; no other lags, PZT features, hyperparameter searches or smoothing. Train-only mean/SD, zero-variance column drop and unpenalized intercept. All arms share identical legal origins and target rows. The input is measured crack length history, not a hidden state or DIC boundary-response reconstruction.

Whole physical specimen leave-one-out; repeats and all observations of that specimen are in the held-out group. Fit using the other completed training-specimen trajectories only. Report a simple curve and paired errors per held-out specimen; never split adjacent windows as independent samples. The dataset is already development-exposed. At least2 other distinct specimen groups with valid training origins are required for a computable fold; this is a feasibility rule, not a power guarantee. No p-values or confidence from window bootstraps.

Primary descriptive quantity: specimen-equal mean paired MAE(M1)−MAE(M0), mm. Also expose B0/B1 and every specimen. Beating M0 but not B1 does not demonstrate useful forecasting improvement. No calibrated physical improvement margin is currently available, so the pilot cannot confirm a physical-accuracy or general-road claim. A negative remains negative for this representation and target.

Budget if separately authorized later: at most four usable specimen folds after T4 quarantine and T2 coverage check, two fits per fold, maximum8ridgefits,10minutes singleCPU/noGPU/no search. Check actual coverage BEFORE launch; do not expand horizon bands, add specimens, change target selection or search models if the result is poor. Current user forbids training and this document authorizes none.

## Before fitting

Resolve original time/cycle anomalies, source physical grouping and optical label definition; check input availability using the past-only dependency audit; freeze the exact origin/target manifest, observed target-gap range, specimen eligibility and training counts. Record that sampling-window tolerance and actual observation policy limit interpretation. If physical qualification is unavailable but a published-label-only sandbox is considered, it needs explicit scope and new code/protocol review, never a claim that the metrology was repaired.

Next immediate work is the small metadata/measurement/provenance supplement and frozen manifest; not a model run. If the exact band has inadequate distinct varying groups or lawful folds, report no usable next pilot and stop rather than widen the band or substitute labels.
