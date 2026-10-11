# S09-E007 exact-commit Code Ready review request

Review the exact commit named in the submission against the frozen
`v2-frozen-beta025-u0125-holdout` protocol and `data_lock.json`.

Return exactly `CODE_READY`, `MODIFY_AND_REREVIEW`, or `REJECT_REDIRECT`.

Check that:

1. the builder rejects any source other than the exact c1..c73 substep-4
   `post_history_commit` set and verifies every frozen payload hash before decode;
2. the two checkpoints load strictly with the frozen SHA-256 identities and no
   optimizer step, adaptation, target leakage, or U0.125-derived normalization;
3. `Q_u` and `Q_f` implement the protocol exactly, with strict positive finite
   denominators and no epsilon, clipping, omitted cycle, or fallback metric;
4. the outcome table, thirds, quantiles, deterministic field selection, boundary
   check, receipt, and failure handling are exhaustive and deterministic;
5. producer guards require clean exact-commit Taobo execution and fresh `/mnt/data2` output;
6. fixture tests and audit-only execution do not decode U0.125 scientific arrays.

A pass authorises one permanent unsealing/build followed by one Taobo inference.
It does not establish scientific success or Evidence Ready.
