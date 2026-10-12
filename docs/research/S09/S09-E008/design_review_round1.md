# Independent design review round 1

- reviewer: ChatGPT Pro through OpenCLI, authorised Haofan account
- conversation: https://chatgpt.com/c/6acd025d-ab18-832e-966f-13cf21712bab
- reviewed draft SHA-256: `ce8eb2d766c54920926ea392bc05c33cbf3f209472bf190d0dbcacc87bef8650`
- decision: `REVISE_AND_REREVIEW`

## Blocking findings and disposition

1. Stage 0B allowed peak-to-post damage/history reversal. The revision now
   states the required within-cycle ordering, while deferring Stage 0B/P2 to a
   separately reviewed amendment.
2. P1 selection, normalisation, export-resolution convention and false-growth
   statistic were not reproducible. The revision freezes formulas, the exact
   deterministic 16-cycle selection rule, minimum group counts and a fixed
   judgement loss independent of adaptive training weights.
3. P0/P1 scope versus Stage 0B/P2 was ambiguous. The revision authorises only
   Stage 0A/P0/P1 and makes P2 non-executable here.
4. The source audit lacked an explicit state-sufficiency test. The revision
   requires every needed producer variable to be carried, prescribed/frozen or
   causally reconstructible.

The reviewer otherwise accepted the causal indexing, mixed nodal/GP support,
physics ladder, multi-objective direction, relaxed development scale and
complete-trajectory split. This review did not authorise opening arrays or
training.
