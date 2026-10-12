# Next solution proposal: correct the candidate box

## What it should change

Increase actual crack-box recall by moving/resizing available proposals so that
they satisfy IoU>=0.50. Preserve the tiled proposer and E003 score rule. A new
Experiment, protocol and independent review are required; this is a concrete
proposal, not a launched run or guaranteed solution.

## Smallest producer intervention

1. Reuse hash-bound tiled train proposals. Associate a train candidate with the
   maximum-IoU crack GT only when IoU>=0.05. Include partial-overlap examples,
   with deterministic GT-index ties; never use validation/test GT for fitting.
2. Before training, audit whether a 50% padded context crop contains the
   associated GT; report containment by proposal/target size. This tests whether
   the intended correction is observable in the input. If context misses most
   of the reference crack, repair the input contract before fitting a head.
3. Extract frozen E003 CNN features from that context plus normalized proposal
   geometry. Fit one regularized four-output linear bbox head on the producer:
   center offsets divided by proposal width/height and log GT/proposal
   width/height ratios. No CNN/proposer retraining or architecture sweep.
4. Freeze coordinate clipping, offset/scale bounds and duplicate handling before
   any validation comparison. Keep original E003 scores so the experiment
   isolates localisation correction. Apply the same frozen NMS rule to corrected
   boxes; preserve original candidate IDs and provenance in the paired output.
5. Compare original and corrected boxes on development validation at 1 FP/image;
   only a reviewed, preregistered improvement gate permits fresh confirmation.

## Result definition to freeze before execution

One primary operating-recall difference against E003. A +0.05 practical margin
can be retained if review agrees with the final input/correction contract.
Report paired IoU changes, location recall, FP types, rejected/clipped
corrections and a deterministic before/after overlay. Partial improvements remain
visible; invalid associations or missing reference coverage are admissibility
failures. Stop after one fit and one permitted confirmation; preserve unused
reserve locations until model/validation freeze passes.
