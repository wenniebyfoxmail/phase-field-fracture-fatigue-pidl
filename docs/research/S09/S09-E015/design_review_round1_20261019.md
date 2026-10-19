# S09-E015 design review round 1

Verdict: `REVISE_AND_REREVIEW`

Reviewed design commit:
`1b1ea9f0d6dd0e2b890bed7470b0db29008eef82`.

Review channel: Haofan account, ChatGPT Pro, same S09 review conversation.

## Identity result

- ZIP: 211,484 bytes.
- SHA256:
  `62c93dd8d6525553b73fe2c7f545547612c79f903c60c279fe6346f2185514d8`.
- Ten regular files: manifest plus nine listed content files.
- All 9/9 content hashes and byte counts matched.
- No duplicate, unlisted, unsafe or corrupt ZIP members were found.

## Sole blocker

The design called the E014 vector archive's analytic next-AdamW displacement
the exact realised parameter displacement. E014 saved that analytic vector
before the optimiser step, then required only
`torch.allclose(actual, analytic, rtol=1e-6, atol=1e-12)`. The actual
`after-before` vector was not written back to the archive. Because E015 uses
strict zero and positive-node predicates, tolerance-level parameter differences
could in principle change collapse classification.

The review did not reopen E014's accepted implementation or result. It found
that E015 had assigned the archive a stronger identity than E014 established.

## Required repair selected

E015 now binds the finite paths to the actual B25 and E014 endpoint checkpoint
parameters. Interior states use the direct float64 checkpoint difference; the
lambda-0 and lambda-1 states use exact source and endpoint checkpoints. The
analytic archive remains a provenance and tolerance check and is not required
to have the same tensor hash.

Endpoint replay is now an execution-validity condition. Continuous evaluator
values use the inherited frozen tolerance; strict-zero status, positive-node
counts, collapse status, pair outcomes and integer counts must match the E014
evidence exactly. A mismatch produces `EXECUTION_INVALID` rather than a
trust-region interpretation.

## Items already accepted in round 1

The reviewer found no other design blocker in the fixed seven-point grid,
13-state accounting, no-chaining/no-adaptive-search rule, `NONCOLLAPSED`
definition, same-lambda Levels 4-5, undefined-ratio handling, evidence contract,
or 900-second/10-GiB boundaries.

This review produced no GPU execution, gradient, optimiser step, FEM solve or
new scientific result.
