# S04-E014 R001 figure set

## Scientific question

Which controllable lever should be tested first after the S04-E013 fixed
supervised procedure failed: sampling/optimisation, representation, or a
mechanics-aware objective?

## Evidence source and generation

Both figures use all twelve S04-E013 Attempt B final predictions and loss logs,
plus the four exact admitted reference files. The tracked script is
`SENS_tensile/analyze_s04_e014_stage1_repair.py`; the raw assets remain under
`local_archive/experiments/S04-E014/runs/S04-E014-R001-stage1-posthoc/`.

`repair_diagnostic.png/pdf` shows all twelve logged loss traces, final sampled
versus exact full-field loss, seed bias/variance decomposition, and error mass
on original active-p99 nodes. `c20_spatial_error.png/pdf` shows all nodes for
the median-error c20 seed 7 case; this selection rule was fixed by the scalar
metric and is stated in the title.

## Intended reading

Panel A shows continuing but highly variable minibatch loss. Panel B shows
that the final minibatch can substantially over- or under-estimate the exact
full objective. Panel C shows that shared bias, rather than seed variance,
dominates. Panel D shows that a very small active region contains most of the
remaining error. The spatial figure confirms that the network reconstructs
the broad correction but misses a narrow damaged/process-zone band.

## Allowed conclusion

The smallest evidence-backed next intervention is an unbiased sampler that
guarantees coverage of the fixed damaged region while preserving the exact
mass-weighted objective.

## Blocked conclusion

The figures do not measure gradient variance, prove architectural
representability, authorize producer training, or show that stratification
will pass displacement, strain or residual gates. The proposed screen must test
that repair directly.

---

# S04-E014 R002 figure reading guide

## Question and evidence

Does unbiased damage-stratified sampling recover the frozen supervised
displacement gate at c20 and c83? The figure reads the two exact R002 monitoring
traces and the final metrics admitted by the fail-closed aggregator.

## Reading order

1. Left: fixed full-field displacement RMS at steps 0, 1000, ..., 10000.
   These points diagnose convergence; only step 10000 votes.
2. Right: final result against the exact S04-E013 seed-7 comparator. The dashed
   line is the absolute `1e-3` gate.

## Interpretation

Both final errors improve by about one third, so damage-aware sampling is a
useful ingredient. Both remain more than three times the absolute gate and fail
the preregistered 50% improvement trigger. The nonmonotonic traces, including a
c83 background-error excursion, show that sampling frequency alone does not
resolve the localized-versus-smooth representation conflict.

Allowed conclusion: reject sampling-only repair and move to one bounded
local/multiscale representation screen that retains the unbiased full-field
objective.

Blocked conclusions: architecture non-representability, four-state/cross-seed
validity, Stage 2 authorization, FEM reproduction, or FEM-teacher qualification.
