# Next proposal: preserve originals and qualify local correction selection

Proposal only, not a frozen Experiment or an executed extra E005 arm.

## Target behavior

Increase actual valid detections at the same false-positive budget while
retaining the useful E003 candidate coverage. E005 provides 19 GT targets coverable only by corrected candidates relative to
originals, but loses 121 by replacing originals; those gains cannot justify
mandatory replacement. Preserve the original candidate list as an immutable
protected branch. A correction is an additional alternative, not a deletion.

## Smallest decisive route

1. Freeze a candidate-preserving merge: original IDs/coordinates/E003 scores
   stay intact; overlap between a correction and protected originals may reject
   the correction but cannot suppress originals. Deterministic IDs/ties are
   fixed. This protects proposal coverage by construction; it does not protect
   operating recall, which must still be measured.
2. Reuse E005 corrections only as candidates to test whether useful new local
   geometry exists; report added coverage and extra FP exposure separately.
   The observed union oracle .723149 is development-only feasibility evidence.
3. Qualify an original-versus-corrected validity selector using local **spatial**
   visual information and geometry. Keep reference GT out of inference. Do not
   train its labels on in-sample predictions of a corrector trained on the same
   targets without disclosing/repairing that leakage in qualification: freeze
   a train-location split or cross-fit correction generation before any selector
   fit. Decide the cheapest option and exact feature representation before code.
4. Compare one selected candidate policy against unchanged E003 at 1 FP/image,
   IoU>=.5 macro-location recall. Freeze meaningful improvement, budget and stop
   rule before results; secondary IoU/duplicate/oracle changes cannot rescue
   a failed detection criterion. Keep unused confirmation locations sealed until
   independent development-evidence review and full authorization.

This proposal requires new design/code review, one explicit experiment budget
and a new Run. It does not authorize head reuse, selector training, scalar
shrinkage sweeps, conditional GT-based correction or a relaxed E005 gate.
