# LTPP 06-1253 Pilot Scope Decision

## Frozen decision

Continue the current `0-50 ft` panel pilot. Do not expand human vectorization to
the remaining nine panels per survey date in this phase.

## Primary temporal scope

The following seven dates are eligible for the main within-monitoring-history
exploratory analysis:

- 1991-06-10
- 1995-10-24
- 1997-02-28
- 1998-04-07
- 2001-09-13
- 2003-05-14
- 2007-11-06

The following dates occurred after the official 2011-06-01 Out-of-Study event
and are auxiliary geometry only:

- 2012-04-17
- 2015-03-02

They cannot authorize a claim of continuous monitored deterioration through
2015.

## Official-data boundary

The official `MON_DIS_AC_CRACK_INDEX` quantities summarize the full 500-ft LTPP
section, while the pilot vectors cover only the 0-50 ft panel. Therefore:

- official quantities may be used for date coverage, direction-of-trend, and
  order-of-magnitude plausibility checks;
- they are not quantitative labels or ground truth for the pilot panel;
- equality, calibration, pixel accuracy, length accuracy, and area accuracy
  against the full-section totals are prohibited claims.

## Annotation boundary

- Current primary labels remain single-annotator exploratory observations.
- No second-annotator agreement or adjudication claim is authorized.
- No additional manual labeling is required by this pilot decision.

## Authorized next operation

Build and qualify a structured continuous field adapter on the frozen 0-50 ft
observations. Apply temporal consistency only to the seven primary dates. Keep
the downstream climate-free A/B split and decision rule unchanged so that any
change in temporal generalization can be attributed to the field representation.
