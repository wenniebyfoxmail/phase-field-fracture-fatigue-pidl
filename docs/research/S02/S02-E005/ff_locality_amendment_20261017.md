# S02-E005-A002 v1: FF sensitivity localisation

Date: 2026-10-17. Post-result, descriptive amendment to the frozen-label diagnostic. Prior R001 and R002 outcomes have already been seen. This is not preregistered confirmation, a fresh test set, or a revision of the original negative result.

## Bounded question and evidence

Which of the 33 FF evaluation windows contribute to the two existing alternating-error reversals, and how do those contributions co-occur with hole geometry and growth? Controlled-experiment C1/C2 label-sensitivity diagnostic, not a new physical-accuracy or prediction claim. Unit: same FF origin -> origin+1000 cycles windows as R001. Frozen predictions B0/B1/M0/M1, labels, features, time keys and weights remain unchanged. No model loading, forward, fitting, retraining, smoothing, time repair, extra error paths, radii, exclusions or new validation criterion.

Inputs: original ten-file external data lock; R001 predictions/prepared/summary; R002 scores/summary/receipt. Direct cycle-key joins to FF-cracktip.csv provide origin x,y and target x,y. Check both x endpoints against frozen rows. Shared errors use sorted unique union of actual endpoint cycles; do not assume adjacent row indices are adjacent cycles. Validate every FF aggregate for both phases at all seven already used radii against R002, and preserve source bytes.

## Fixed definitions before new calculation

Let d0_i=|q1_i-y_i|-|q0_i-y_i|, d_i(e)=|q1_i-y_i-e_t+e_o|-|q0_i-y_i-e_t+e_o|. Signed shift s_i=d_i(e)-d0_i. Sum(s_i)/33 must reproduce the aggregate D shift. Lowering mass l_i=max(-s_i,0), offsetting mass u_i=max(s_i,0). Report both masses and net; lowering shares use sum(l_i), never a signed net denominator. No leave-out rescoring.

Primary localisation uses epsilon=0.06848 mm and BOTH existing alternating phases, because these are the two witnessed FF reversals. Ranking score v_i=(l_i,+ + l_i,-)/2; descending with origin-cycle tie break. Display all 33 windows, list top five and report their share of each phase's gross lowering mass. Also export all rows for all seven existing radii; the smaller radii are context, not a searched threshold. Tolerance=1e-10 mm.

Public 2018 benchmark Fig1: hole centre (25,0) mm and diameter5 mm; public CSV coordinates, not thesis coordinates. Primary spatial groups by ORIGIN x: before x<22.5; over projected hole 22.5<=x<=27.5; after x>27.5. Projection overlap does not mean tip lies inside/next to hole. Report Euclidean ORIGIN tip-to-hole-edge distance sqrt((x-25)^2+y^2)-2.5 continuously, without a tuned near-distance threshold. Also show target points descriptively; target geometry never becomes origin information. A window can cross a group boundary; classify only its origin and retain both endpoints in the table.

Low growth is explicitly RELATIVE TO THIS EVALUATION TAIL: the 11/33 smallest frozen B1 increments (past secant), breaking ties by origin cycle. This is an origin-available context variable, not a prefix-defined physical stage. Separately mark the lowest11 realised target increments as retrospective only. Use both fixed sets even if little agreement. Report group counts, gross-lowering shares, per-window means and share/window-share ratios, no p values, confidence intervals, fitted trend, causal attribution or independent-unit generalisation. One FF specimen and temporally dependent windows cannot separate position, time and growth. Membership uses exposed evaluation data and is descriptive, not predictive validation.

Explain the score mechanism: for a given window d(y) is constant when labels remain on one side of BOTH frozen predictions; changes occur when a perturbed label crosses/begins inside their interval. Export distance from original y to the closed interval spanned by q0,q1. This is algebraic scoring sensitivity, not evidence of actual error or a physical cause.

## Execution and review

Use a fresh R003 archive, local deterministic CPU arithmetic only, 60s alarm and observed peak RSS<=1024MB (not an OS memory cap). Synthetic tests and independent exact-commit protocol/code review before real localisation; evidence review after. Execution requires review receipt and clean reviewed HEAD; any material change requires rereview. Failure of schema, lineage, reproduction or invariant checks stops without changing older results.

Minimum evidence: all-window/all-radius CSV, group table, summary with exact contribution sums and top5, source-byte receipt, one figure showing all33 growth/prediction windows incl B1, both signed shifts, spatial coordinates/hole, and sensitivity vs past growth. README states reading order, limits and storyline impact. No outcome is a new success/failure gate. Stop after this fixed analysis and record the strongest supported descriptive conclusion; await author repeatability and timing/processing information before physical inference or further modelling.
