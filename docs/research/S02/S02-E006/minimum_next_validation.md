# Minimum next validation proposal — unexecuted

2026-10-17, design-v1. Primary candidate: MnROAD scalar survey labels. This changes the available-history question from old boundary-response history (FATACRACK) to older crack-survey history. Neither material/mechanism transfer nor structural-response information is tested. S02-E005's original negative remains unchanged. No model fitting, feature extraction, split scoring or training is authorized/executed by this proposal.

## First make a small dataset that can answer the question

From the existing source inventory, restrict to Driving lane to avoid mixing the differently loaded Inside/Outside LVR lanes. Group all lanes, reconstructions and studies under the same physical CELL for holdout. Cell codes are provisional grouping keys, not proof of independence; confirm roadway, station ranges and lineage/non-overlap. Exclude old cell22 and metadata-conflicting/duplicate-date IDs. Rank candidates by usable date coverage, never crack growth values or prediction errors.

Source screen extension: one section per CELL, largest four-spring-slot coverage, section-ID tie break. Fetch official timeline for every selected Driving CELL (14 from current inventory). Conservatively end at the first dated non-bookkeeping Construction Event after section start, including seals, test-pit patches and unknown physical works; do not restart afterwards in this minimum pilot. For undated unknown events or unavailable/possibly truncated timelines, keep zero eligible coverage. A window's target slot cutoff must precede that action and stay within section end. This is a screen against RECORDED actions, not certification that no unrecorded work occurred. Next qualification budget: top6 distinct CELLs with retained coverage; six is a small work budget, not a power/sample-size success threshold. If fewer remain, report the resulting limitation rather than relax timing or maintenance rules.

For those candidates, close: physical lineage/station/lane and section length; target units/definition including sealed/unsealed NWP and survey changes; timeline completeness/applicable works; same-time processing/provenance and historical revisions; exact usable origins and grouping. Original measurement repeatability remains a physical-accuracy gap. Its absence alone need not prohibit an explicitly labelled published-survey-label pilot, but it prohibits claiming a calibrated physical growth gain or choosing a numerical physical success margin.

## Freeze the forecast object

Origin: May31 of yearY. Current observation: last actual survey within March1–May31 of yearY. The older observations are the same slots in Y−1 and Y−2. Target: published NWP longitudinal-cracking total at the last actual survey in March1–May31 of Y+1. Use the three finite fields LONG_NWP_L_L/M/H only after their units/definitions are verified. No interpolation, missing-year fill, zero coercion or enforced monotonicity.

This is an annual spring-survey-window prediction, NOT exact365day physical crack length. The latest actual survey date in Y+1 is used only to locate/describe the label, never as a prediction input. All feature choices and candidate selection use information available by the May31 origin. Future traffic, weather and maintenance cannot enter inputs unless independently scheduled/forecast at origin (none in this minimum design). Future labels may select evaluation coverage, but no exclusion may depend on their value or growth direction.

The archive has updated historical records. Unless original release timestamps/versions are available, describe this as a retrospective simulation using survey dates, not proof of actual historical real-time deployment. A same-year May survey released after May31 is unavailable at that origin; obtain an applicable delay assumption or source release evidence before finalizing the origin. If spring timing lacks enough support, stop this proposed cadence and draft a separately reviewed alternative; do not silently widen windows after scores.

## Smallest information-matched comparison

B0: current reported length unchanged.

B1: secant rate from the two most recent actual observations, extrapolated to the known May31 of Y+1. It does not use the unknown future observation date. This baseline predicts the declared survey-window label with an explicit cutoff approximation; the difference between observation date and slot cutoff is not secretly corrected using future data.

M0: B1 plus fixed ridge(alpha1) correction trained on other cells. Inputs: current reported length; most recent per-day secant; age since section start; current observation's age at the May31 origin; and elapsed days in the previous observed interval. Train target is actual target increment minus the B1 increment. Train-only mean/SD standardization, fixed intercept policy and no clipping/smoothing.

M1: same learner, target, preprocessing, origin and M0 inputs, adding ONE earlier per-day secant from the Y−2 and Y−1 observations. No longer lag, hyperparameter/model search, author predictions or response channels. This tests whether older observed crack growth adds information beyond current state and recent rate. A negative result pertains to this representation and learner, not all possible history.

At most6 qualified cells in the first pilot: leave one CELL out, with all its lanes/reconstructions kept out of fitting. For a held-out origin May31Y, training from other cells may include only windows whose target label/slot and release are available by that origin. This also avoids learning later weather-era patterns to predict earlier test years. Standardization uses only that eligible training set. If a fold/origin has too few or degenerate training rows for the frozen model, report it unavailable with coverage; do not borrow future years, fit on test-cell labels, or silently pool all calendar years. Final counts and one fixed operational training-row policy must be frozen before fitting; this proposal is not Run Ready yet.

All selected cells share one facility/climate; whole-cell holdout tests within-facility transfer, not independent-region or global-road generalisation. Metadata/availability has been examined: treat the existing archive as development exposure, not an untouched confirmatory test. No random frame/window split, window bootstrap or nominal p-value from overlapping observations.

## Criterion, evidence and stopping

Primary descriptive metric: equal-CELL mean of paired MAE(M1)−MAE(M0) on identical eligible origins. Report all cell-level values and B0/B1 on the same origins. M1 beating M0 while losing to B1 is only a component finding, not a useful forecast advance. Without a justified decision margin/noise calibration, report the sign and effect size as exploratory; do not manufacture a formal scientific PASS threshold or claim statistical confirmation.

Minimum evidence if separately authorized later: frozen origin/target/group manifest, input-dependency audit, complete per-origin predictions of all4 arms, per-cell MAEs/paired difference, coverage and all trajectories with simple controls, failure/censor list, exact code/config/source identity and independent code/evidence review. Budget: up to6 fold-specific model pairs per eligible origin-year; no hyperparameter search; a concrete CPU/time/fits cap must be calculated from final qualified origins and explicitly authorized before launch. No execution follows from this draft.

Stop if qualified physical grouping/target semantics cannot be resolved, no meaningful multi-cell coverage survives maintenance and calendar-time separation, or input availability cannot be established. Preserve any negative, do not tune old held-out data or reframe conditional sampling as fixed-horizon success. Additional raw/sensor histories would be a different question and require a new protocol.
