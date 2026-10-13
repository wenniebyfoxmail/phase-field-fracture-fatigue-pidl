# S01-E005 independent evidence and posthoc diagnostic review

Separate read-only e003_independent_review, gpt-5.6-sol / Medium.
PASS at exact clean evidence commit `4db22d4622262f36941e1f42e5396333c832d8b2`.
No blocking findings. Runtime and preregistered analysis remain bound to reviewed
`8c45162b1d0ced61ce9c97887948c91d7383010a` and manifest
`bcf83836976a1144045f70ccee71535dd76edf4ba7b7d6c4c5cf444b8145cea0`.

## Verified evidence

ZIP63,107,698 bytes/18 members, SHA c27bd720dc5ec8bb7bc0bc4fdb9e2630f967810678d3fb94fd2b6c88d27f0781,
18/18 CRC PASS. Model b687635f6ebcd49e221765eea2eada6c2fed1c46ae0cdfb5b15c3b675eadd771,
evaluation31dd3a45ca7ddb037b339db581580a59cd0fd2dea166e6f118909e09551b855f
match records. 76 tests passed. Receipts and markers establish exactly one
actual Run/fit; the first shell policy error occurred before Run creation.
No test authorization, download, test manifest or confirmatory evaluation.

Train audit11,852 matches,1,143/1,149 represented GTs; padding4 target-balanced
containment .9326986044. NPZs train(11852,582),validation(14635,582),float32;
receipt hashes and six geometry columns match. Equal-GT weights sum to
0.9999999999999999. Means exact, standard deviations cross-platform difference
<=2.22e-16. Training target libm rounding difference<=1.11e-16.
Initial/final objective .8095395842620701 / .34158920209791854. Replayed gradient
infinity norm4.93e-16, stored4.34e-16, both below frozen1e-8.

Validation IDs/scores/NMS identities match. Coordinate rounding difference
<=6.82e-13 changes no matching. Macro .2895090596 -> .0761109424,
delta -.2133981172; TP115 ->36,FP302 ->302;suppressed3124. Oracle .683550 ->
.283587; FP partial190 ->210,duplicate20 ->1,no-small92 ->91. Flags bounded1787,
image-clipped1478,fallback2. Paired-IoU diagnostic and seed bootstrap
[-.367993,-.062472] reproduce. Figures readable; deterministic case receipts
match. All four montage image hashes match exact E002 validation images, ZIP
CRC/hash match. Repeated images across lost/FP roles are disclosed.

Posthoc diagnose_coverage.py performs no fit/operating-threshold selection and
reproduces JSON exactly: original218 covered, correction pre/post137/116,
retained97/lost121/new19;union237,macro oracle .7231494416. This is a
nondeployable development-only coverage upper bound, not detection gain and
not a rescue of the failed primary. Posthoc source is bound to evidence commit.

## Decision

Execution, retrieval and numerical admissibility PASS. Mandatory replacement
pooled-feature ridge head is development-negative; retain E003 and seal fresh
locations. New-location verdict is uncomputed/inconclusive. Successful context
visibility and19 newly coverable targets are partial findings; they do not
offset121 lost targets or change TP36/FP302. Candidate preservation and a local
spatial selector with out-of-sample train-location qualification is a reasonable
next hypothesis, untested. No additional arm, fitting or fresh access under E005.

Optional prose refinements were adopted in closure: describe19 targets as
coverable only by corrections relative to originals; identify8c45162 as runtime
and preregistered analysis, separately4db22d4 for the posthoc script.
