# Next proposed test: score the repaired crop while preserving originals

Proposal only;no additional fit,rescoring run,operating threshold or policy was
executed underE007. E003 remains the working detector.

The existing corrections contain177 pair-level geometry gains in the4 training
qualification locations. Only12 have original E003 scores above the baseline
operating prefix. The4 gain pairs accepted by the most permissive frozen policy
are all below that prefix. They cannot become actual detections while assigned
the old crop's score. The linear selector also rejects the12 score-eligible gains.
This identifies both a recognition gap and an inherited-score bottleneck; it does
not establish that rescoring will be sufficient or safe.

The smallest next intervention is to score each corrected crop using the
unchanged E003 classifier,with its original padding.1 and RGB normalization,
then compare that score against the original parent's score. No new encoder or
broad model fit is needed for this capability check. Freeze it as a separate
train-only diagnostic before any new development comparison:

1. Use the existing location-excluded correction bank and checkpoint. Compute
   corrected-crop classifier scores without GT input. Record how many genuine
   geometry-gain pairs can enter a fixed original operating prefix,and how many
   invalid/duplicate alternatives would also enter. Keep train diagnostic and
   actual deployment labels separate; do not describe this as holdout success.
2. Preserve original coordinates,identities and scores in an immutable emitted
   branch. Any later deployable proposal adds selective repaired candidates;
   it never replaces or suppresses originals. Recompute the actual FP-budget
   prefix:added FPs can still remove old targets from the admitted set,so proposal
   preservation does not guarantee operating retention.
3. If corrected-crop scores provide useful qualification separation,freeze one
   train-qualified candidate admission rule and a single development comparison
   with the same .95 retention and+.05 recall objective. Reject duplicate exposure
   explicitly. A new source/protocol review and human approval precede execution.
4. If scores still cannot expose valid gains at tolerable FP cost,stop reworking
   frozen-feature selectors and redirect to an informative localisation model
   or reference data. Do not loosen the failed E007 thresholds or rerun E007.

The first test therefore answers a concrete controllable question:can the
unchanged classifier recognize useful repaired crops at the operating budget?
It is not permission for a fifth qualification policy,an oracle-assisted output,
a fifth ridge head,fresh access,or retrospective rescue of E007.
