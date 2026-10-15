# Independent code and evidence review — 2026-10-15

Reviewer `/root/halfdepth_code_review`, read-only. No real aggregate runner,
image sampler, fit, training, forecast or file changes by reviewer. Protocol
`short-support-v1`; reviewed clean commit7dab07258cc2192ebbda1b089500dccd66f54097.

## Design and code readiness

Before execution, fixed9width median, endpoint sensitivity, matched primary
original-H subset out48, secondary aligned arm, strict complete-window missing
rules and36signed stage increments per arm reviewed. Event tag clarified:
both adjacent endpoints inside cached width-centre[-4,+4], never an exclusion.
Raw footprint at c0±4 and across jitter±6 explicitly separated from centre span.
Odd symmetric median's monotone/affine identity and spike-suppression boundary
predeclared; no parameter sweep or physical tolerance invented.

Reviewer independently reran11 synthetic tests, all passed0.108s, before real
aggregate execution. Cache successful-clean E020 identity,3936/3840/96/96keys,
grids,finitevalidwidths,adjacentdelta/union,curvecounts/ranges andt0 replay
checks reviewed. Main paired median(D), not median differences, implemented;
primary endpoints unchanged by interior curve extrema. Renderer comparison
metrics and all-case/fixedT6 selection correct. No remaining execution blocker.

## Actual numerical and visual evidence

Reviewer independently recomputed all864 centre values directly from E020 CSV
using the fifth sorted width for each9point median. All point/median/support
values match; all96 endpointS/D and72 signed stage increments, absolute
distortions and ratios match row by row. Independently recomputed every
primary/byarm/byload/bytag/bytransition summary field, all match.

Coverage864/864 for both methods, each arm48matched sensitivities and36matched
stage pairs. Five input file paths/sizes agree with receipt, E020 successful
clean84c34422 identity, E021 successful clean7dab072. Threads1, wall.071103250s/
CPU.046416s within60s budget. Retrieval verified local, no new image sampling.

Original primary medianD0; separate medianS1.441718594 unchanged;14improve,
30equal,4worse. Aligned medianD0;15improve,27equal,6worse. Its tiny separate
median fall is not primary paired improvement. Both arms36/36nonzero point
increment signs agree, median absolute distortion0; maxima original
.35142048626055455/aligned.2680470948796838px. Sign retention does not certify
unchanged amplitude. Frozen event tags exactlyT1/10kN andT11/40kN per arm;
n2 subgroup exploratory only, no exclusion or physical-branch conclusion.

All4 actual PNGs independently viewed, no clipping/blank/axis reversal/label
overlap. Shared sensitivity/signed stage axes correct. FixedT6 four original
cached strips and width/load/jitter tables agree; support and nonphysical-edge
boundaries clear. Main-agent sidecar check8formats/4notes passed.

## Scientific boundary

Evidence complete for the bounded C1 support diagnostic, not physical accuracy
or forecasting. Fixed median preserves local benefits and observed stage signs,
but typical paired sensitivity does not decrease. Results compatible with the
analytic monotone-median boundary; no universal stability or optimal length.
Keep old point target/scores. Next address position correspondence/spatial
gradient, not a result-driven length/arm sweep. Final wording check follows.

## Final wording and auxiliary table checks

README_analysis, compact evidence summary and Run receipt read by reviewer;
all auxiliary figures/numbers match raw evidence. Each arm22/36 arithmetic-
unchanged increments; original3/aligned1 negative increments retained. Maximum
distortion bothT4/40→50kN: original.582298552031→.230878065771 (39.6494%),
aligned.487872377307→.219825282428 (45.0579%). Best original sensitivity
T11/40kN5.246382811→2.060874529; worstT4/10kN.051138529→.228803029.
Reviewer requested replacing "smaller localisation error" with "smaller width
change induced by position perturbations", since actual coordinate accuracy
was not tested; main agent applied that wording-only correction. No numerical,
visual or interpretation blocker; Experiment/S03 closure entries added after
owning evidence records. No new calculation or method change needed.
