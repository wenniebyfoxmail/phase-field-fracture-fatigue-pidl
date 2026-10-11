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
