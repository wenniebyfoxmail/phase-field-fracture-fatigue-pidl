# S09-E010 focused producer rereview round 2

- Reviewer: ChatGPT Pro, Haofan account
- Conversation: <https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>
- Base producer commit: `ded694d665000ed8db248f2dc96110e062ef07d8`
- Reviewed repaired candidate: `7548a97aa4268fa89586a660e597e58dbe539a0c`
- ZIP: `S09-E010-producer-rereview-7548a97aa426.zip`
- ZIP bytes: `32678`
- ZIP SHA256: `8839537e51ffc6707564fb2c66f2dfb624028d1005f9d25191197c1dbb30e11c`
- Verdict: `REVISE_AND_REREVIEW`

## Independent scope

The reviewer verified the ZIP identity, CRC, path safety, both full commit
identities, all four manifest file hashes and byte counts, and application of
the supplied base-to-candidate patch. The reviewer independently exercised
isolated config projection, checkpoint-read failure, arm-control, receipt and
dirty-file branches. It did not rerun the reported PyTorch or pytest suites and
did not execute an optimiser or producer.

## Closed findings

1. The unresolved projection preserves the frozen packet SHA while upstream
   source, packet and resolution-receipt mismatches remain rejected.
2. The atomic checkpoint write caches the actual write-time hash; a persistent
   later read failure preserves the file and writes a 500/500/500
   `EXECUTION_FAILED` arm receipt.
3. `source/s09_e009_four_arm.py` is included in the producer dirty-file
   binding.

## Residual blockers

1. `_verify_arm_evidence_integrity()` parsed the disk receipt but compared it
   with Python dictionary equality. This accepted schema-invalid numeric type
   substitutions such as `500.0 == 500` or `1 == True`.
2. A valid `METHOD_INAPPLICABLE` result in A25 still failed the exact-replay
   gate and stopped B25/B0. The final decision also checked replay eligibility
   before method-inapplicability, producing `EXECUTION_INVALID` rather than the
   frozen arm-local method result.
3. If `termination_receipt.json` itself could not be written, the assignment
   into the outer `arm_results` mapping never completed. The top failure
   receipt therefore omitted the current arm's already-known completed and
   logged update counts.

## Adopted repair

- Validate the parsed disk receipt with the original schema and require its
  bytes to equal the canonical in-memory receipt before shared evidence can
  close.
- Stop for a replay mismatch only when A25 completed; preserve a legitimate
  method-inapplicable A25 as arm-local, run the later frozen arms, and give
  method-inapplicability priority over ineligible performance comparison.
- Raise a typed arm-close exception carrying the prepared failed arm result;
  the outer loop records it before writing the top failure receipt.

The frozen numerical method, three arms, 500-update budgets, evaluation points,
data, thresholds and E009 conclusion remain unchanged. The reviewed commit did
not receive producer-package PASS and was not eligible for execution.
