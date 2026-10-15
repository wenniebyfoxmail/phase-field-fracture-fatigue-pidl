# Independent review — E025 conditional-interface-v1

2026-10-15; reviewer `/root/conditional_interface_review`, separate agent,
read-only. User explicitly requested independent interface/evidence review.
This is independent software review, not independent physical annotation or
unseen-data evaluation. No new pixels, sealed sources or actual replay by reviewer.

## Code review before replay

- First implementation77361f6:14 synthetic tests independently rerun, plus
  a36-row synthetic arm-failure/reference-missing accounting check. No blocker
  for fixed main/reader; identified that the standalone evaluation seam trusted
  loader stage/load metadata. Main already connected exact stage/condition.
- Improvement b3126c42ccbce7809e259afc55eb1ecf6cf4bd25: added stage+nominal
  condition assertion at evaluation seam and negative tests. Independently
  reran all15 tests, clean source/diff check. Final Code Ready authorised only
  this commit, existing eight-case ledger, fixed reader and protocol.
- Verified E/Q/numerical prediction only receive immutable history packet;
  all96 inputs and two-arm outputs exclusively create/close the JSON snapshot
  before reference callback; evaluation uses the serialized snapshot.
- Missing/invalid history, query, reference, nonfinite outputs and per-arm
  failures are explicit. Common support shared by both methods. Mutually
  exclusive terminal counts sum to N. Missing entire beam gives null overall,
  not an unnoticed two-beam reweighting. Duplicate keys/source/load mismatch stop.
- History transform provenance independently checked: E012 each stage is
  registered against first frame only; E015 converts its stage H, not future
  refitting. Full-sequence CSV byte scan acknowledged; semantic/API isolation
  does not imply process/filesystem blind isolation or physical-online availability.

## Independent evidence review after R001

Reviewer did NOT call new runner, forecast or summarize. Directly read E015
CSV rows, hand-implemented both formulas including unequal loads and clipping,
and checked96 query-transect /192 method rows: prediction, reference and error
maximum absolute difference0. Independently compared old individual_forecasts:
maximum0. Case counts, terminal totals and case->beam->equal-beam aggregation
all agree. Snapshot has no target/reference/R/C fields, historical inputs match
source values. All96 E/Q/R/C true,96 success/0 failures per method.

P MAE0.9234534818541653, secant0.4394862658468068px;
delta-0.48396721600735854px;7/8 cases lower secant, relative reduction52.4084023%.
Result supports bounded software/cached-development replay integrity only.

## Renderer review and QA

Pure renderer repair516cf9b2fe103f119196c9cd844be7a9efa0afe1 reviewed before
R003: title separation,300dpi PNG, attributable Run ID/README; no prediction,
metric or support change. R002 retained, superseded for display due F03 title
overlap. Final figures must cite R003, numeric source remains R001.

Owner opened all four R003 colour PNGs plus MAE grayscale: no missing panels,
unit/state mismatch, clipping or title overlap; redundant square/triangle
markers distinguish methods in grayscale. Programmatic layout checks all empty;
four colour PNGs pass strict300dpi check. PDF checker warns about Type0 font
embedding; `pdffonts` verifies the MAE PDF's CID TrueType font emb/sub/uni=yes.
This is not a journal submission or a claim of universal typography compliance.

Independent final visual review completed: reviewer actually opened all four
colour PNGs and F03 grayscale, then reopened full F02. Confirmed all8 cases /
T1–12, shared scales, categorical locations, reference/units and denominators;
F03 title fixed,唯一略差B4-K2-Q50 retained (+0.003 rounded), F02 T1 about-6px
error not clipped. README precisely links numericR001/renderR003 and same-operator
reference, no physical/holdout claim. R003 receipt checked, no blocker.
