# LTPP 06-1253 MON_DIS Trend Diagnostic Contract

## Purpose and evidence boundary

Determine whether non-monotonicity is present only in the 0-50 ft pilot proxy or
also in official full-section distress indices. This is a descriptive,
post-pilot diagnostic, not quantitative validation.

The official `MON_DIS_AC_CRACK_INDEX` covers the full 500-ft section; the pilot
proxy covers 0-50 ft. Absolute values, slopes, calibration errors, and equality
are prohibited comparisons.

## Frozen dates

Use the seven dates shared by the within-monitoring-history pilot and official
crack-index table: 1991-06-10 through 2007-11-06.

## Frozen series

Pilot summaries:

- mean `line_damage`
- mean `area_damage`
- mean `combined_damage`

Official summaries:

- `HPMS16_CRACKING_PERCENT_AC`
- `MEPDG_CRACKING_PERCENT_AC`
- `MEPDG_TRANS_CRACK_LENGTH_AC`
- `MEPDG_LONG_CRACK_LENGTH_AC`
- sum of the two official normalized line-length fields

## Frozen diagnostics

- Count strictly negative adjacent-date changes for every series.
- Report Spearman rank correlation and six-transition direction agreement for:
  - combined proxy vs HPMS percentage;
  - area proxy vs MEPDG percentage;
  - line proxy vs summed official normalized line length.

## Frozen decision

- If any official series has a negative adjacent-date change, report
  `OFFICIAL_SECTION_TRENDS_ALSO_NONMONOTONE`.
- Otherwise, if any pilot series has a negative adjacent-date change, report
  `PILOT_ONLY_NONMONOTONICITY`.
- Otherwise report `BOTH_OBSERVATION_SUMMARIES_MONOTONE`.

A decrease means only that the observed survey metric is non-monotone. It does
not prove crack healing, repair, annotation error, or physical damage reversal.
