# S09-E005 independent evidence review

## Final verdict

**EVIDENCE_READY PASS** after a two-round review by ChatGPT Pro on the
user-authorised Haofan Pro account.

- Conversation: `https://chatgpt.com/c/6acc0624-67ac-832a-a518-fc1202d4e97b`
- Execution commit reviewed:
  `79f238e0cd2ddd7a31d994f79c6d05410fd8151a`
- Round-2 evidence archive:
  `local_archive/experiments/S09-E005/review/S09-E005-evidence-round2.zip`
- Archive SHA-256:
  `e4c187346e720e80aa4c1034de7c88b5eb4484bb29d4e1491d0bbefc1522d977`

## Round 1 and correction

Round 1 returned `EVIDENCE_READY FAIL` for two evidence-integrity defects,
not because the diagnostic hypothesis was false:

1. the inline PNG attachment had been re-encoded by the web client, so its
   uploaded byte hash did not equal the declared source PNG hash;
2. the aggregate packet omitted the 16-state `gradient_audit.json` and the
   producer `receipt.json`, preventing independent recomputation.

The correction supplied a ZIP whose manifest identifies the authoritative
original PNG/PDF and includes the raw per-state JSON, CSV, receipt, summary
tables and run log.  The reviewer verified all eight manifest hashes, including
the original PNG SHA-256
`c880fb22b107c1d44292eeb9ec910ecd87319e099f5f89ca71554972c1519352`.

## Independent recomputation

The reviewer recomputed all 16 state records and found no numerical
discrepancy.  The reproduced checks included:

- extrema, medians and negative-cosine counts for global, encoder, local,
  coarse and decoder parameter groups;
- both E004 weighted physics/data norm-ratio ranges;
- FEM-target and checkpoint-prediction residual statistics;
- all 128 first-order loss changes (16 states x 4 directions x 2 losses), all
  of which were strictly negative;
- the global squared-norm and dot-product decomposition into the four declared
  blocks;
- zero-update, before/after model-state identity, checkpoint identity, finite
  output and completeness fields in the receipt.

The original E004 packet and checkpoint bytes were not included in this compact
review archive.  Their hashes and the GPU execution therefore remain
producer/retrieval provenance rather than an independent replay.  The reviewer
did not treat this as a blocker for the bounded supplied-evidence review.

## Allowed conclusion

At the frozen E004 step-300 checkpoint, the supplied 16 states show severe
global gradient-scale dominance, positive global cosine, localized decoder
conflict on 6/16 states, and a relatively small observed residual in the FEM
exports.  This supports opening a fresh, separately reviewed S09-E006 test of
gradient balancing and a data-anchored projection guard.

It does not prove the full causal explanation of E004's later degradation,
finite-step Pareto improvement, exact equilibrium, crack evolution,
generalisation or real-road validity.  E004 remains FAIL; E005 is diagnostic
evidence rather than a successful training experiment.
