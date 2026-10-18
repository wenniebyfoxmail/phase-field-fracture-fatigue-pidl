# S09-E010 result-evidence review

## Final verdict

`RESULT_EVIDENCE_READY_PASS`

The verdict applies to the original result-evidence package together with the
raw-log supplement for the same frozen run:

- run: `S09-E010-R001-support-amplitude-three-arm`
- reviewed producer commit: `010281be8045301f7e56b938de82969982c89bc9`
- original ZIP: 694,077 bytes, SHA256
  `b632f57b2f7730564165460cbec6b33ef408da29da0e1c1126e12083ee416fa4`
- raw-log supplement: 928,997 bytes, SHA256
  `48c956e301bcc9bc46e44fc8311e70ce9b9ecff3311d90c3ed5dfbb9ab9879ea`

## Review sequence

The first review independently verified the original ZIP, 15/15 manifest
hashes, execution/config identities, all 336 per-cycle metric rows, the integer
AUC classifier, protected ratios, and the supplied decision/field figures.  It
confirmed that the numerical evidence supports `NO_TARGETED_RANKING_SIGNAL`,
but returned `REVISE_AND_REREVIEW` because the compact package did not include
the A25 update-500 per-cycle projection counts needed to recompute the final
exact-replay clause.

The focused supplement supplied the already archived raw files without a
rerun.  The reviewer verified 17/17 manifest hashes and byte counts, 15/15 arm
files against the remote run manifest, 12 non-termination artifact hashes
against the completion receipt, and all three canonical termination receipts.
The requested A25 `diagnostic_metrics.jsonl` was 127,970 bytes with SHA256
`c5df66ddd0c9415ff36516509dccc1d0451a113cf0024c4584d3574556adb237`.

At update 500, the reviewer extracted three projection counts for each of 16
cycles.  All 48 integers exactly matched the frozen E009 reference, with
maximum difference zero.  The original replay comparison therefore passed
33/33 clauses, and the reconstructed trace matched the producer trace.

## Independently supported conclusion

- A25, B25, and B0 each have 17 wins, 0 ties, and 8 losses; AUC is 0.68.
- B25 minus A25 pair-score gain is 0, below the frozen requirement of 4.
- All four B25/A25 protected ratios pass, but cannot replace the failed primary
  ranking criterion.
- Beta 0.25 reduces `L_P` from approximately 2194.5184 in B0 to 0.7224 in B25
  without changing AUC or pair score, while `L_judge` increases.

The accepted wording is therefore: beta 0.25 provides conditional equilibrium
control in this matched balanced comparison.  It does not establish ranking
improvement, full fracture-evolution PINO, rollout validity, or generalisation.

## Scope

The independent review performed file-identity checks, raw-count extraction,
offline arithmetic, validator replay, and visual inspection.  It did not rerun
the neural model, optimizer, producer, or holdout.  The raw-log supplement did
not change any executed result.
