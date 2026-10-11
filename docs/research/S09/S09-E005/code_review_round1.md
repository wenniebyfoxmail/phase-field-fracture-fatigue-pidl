# S09-E005 independent Code Ready review — round 1

- Reviewer: ChatGPT Pro through OpenCLI, authenticated account `haofan Pro`
- Conversation: <https://chatgpt.com/c/6acc0078-2d18-832c-96c8-ace47a0e9cdf>
- Reviewed commit: `71048248ae3381c36ff09cb3c8bc6fdc61320bc1`
- Decision: `CODE_READY FAIL`

The reviewer found no optimizer update and judged the ordinary nondegenerate
gradient algebra and first-order signs correct.  Four blocking repairs were
required before producer execution:

1. fail closed on zero/non-finite gradients and define the exactly
   antiparallel projected-gradient fallback;
2. enforce complete encoder/local/coarse/decoder parameter coverage and reject
   tuple length, shape or unknown-prefix mismatches;
3. bind the audit to E004's exact objective semantics, step-300 optimizer state
   and assessment weight rather than relying only on the checkpoint file hash;
4. replace string-prefix output validation with path containment and require
   explicit finite/completeness flags before a successful receipt.

The review also required the FEM-export residual to be called an observed
target residual rather than a proven irreducible floor.  It allowed E005 to
inform a new S09-E006 only after these blockers close, while preserving E004's
original failure verdict.

