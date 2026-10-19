# Saved-output mechanism diagnostic: stopped, no new mechanism result

The intended single-pass diagnostic has NOT been completed. The first local derivative-arithmetic attempt stopped at0.254 seconds in the CSV admission loop with ValueError("normalised metric semantics"). It did not reach an NPZ loader, input-distance calculation, decomposition table or figure generation. Original stderr/stdout/intent/bounded_receipt are preserved. No alternate source, threshold relaxation, native data, fitting, coefficient forward, SSH or retry was used.

## Established source-level defect

The new diagnostic imposed Gmean≤E_native≤Gmean+Smean at1e−11 and proposed Gmean/E_native as a Jensen lower-bound ratio. This was an unjustified premise: native error uses prediction64−target32, whereas the stored G/S diagnostic is based on separately computed increments, including target32−current32 rounded BEFORE casting to64. They need not be the same floating residual. Independent source-only review and a hand-written scalar counterexample confirm that finite correctly constructed quantities can fail the new guard. See [source-only review](</Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003/mechanism_diagnostic_20261019/source-only_semantics_review.md>) and handwritten_precision_examples.json.

This does not establish the cause of the actual failing row. The prototype failed to persist its case identity, E/G/S and margins before raising; these values are unavailable. No partial quantitative decomposition was saved, and no data read was repeated to recover them. The traceback alone cannot certify damaged data, identify actual material precision error, explain C30 failures or support either scientific mechanism. R003's original native scores and separately defined increment diagnostics are not invalidated by this new erroneous admission assertion. The original R003 warning-stop breach and local control repairfbdfb0a7 remain unchanged.

## Requested deliverables and current status

- Quantitative decomposition table: not generated.
-2–3 mechanism/failure figures: not generated.
- E1 input support/identifiability versus E2 global/spatial estimation: neither resolved by this attempt.
- A new evidence-selected scientific intervention: not selected; there is no new cohort diagnostic evidence on which to base it.

## Necessary prospective correction, not execution permission

Remove the invalid CROSS-REPRESENTATION inequality and its guaranteed-lower-bound label rather than increasing its tolerance, clamping ratios or deleting rows. Retain G/S as separately defined, non-additive increment diagnostics and native MAE as its existing metric. Keep valid independent identity/finite/count/zero-support checks. Document subtraction/casting provenance. A same-representation bound would require quantities not recoverable from these saved G/S summaries under current access; do not rebuild native inputs. Persist bounded failure context BEFORE every future failed assertion.

The original pre-arithmetic plan/source2b449871 is retained unchanged as the stopped version. This document is not a replacement run card. A corrected contract and the HQ's decision about any continuation are still needed; no continuation is implied. This is a local arithmetic/provenance issue, not a failed scientific rerun or new physical finding. Do not substitute an easier dataset or invent a new RunID to continue.
