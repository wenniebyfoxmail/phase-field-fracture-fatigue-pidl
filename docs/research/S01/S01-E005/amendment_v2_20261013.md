# S01-E005 v2 input-context amendment — 2026-10-13

Original frozen v1 remains recoverable unchanged at commit
`ddb8fa834e7759ab890f9c219081d5487ec2cc05`. Independent code review PASS,
29/29 source entries and 76 tests passed. Read-only training-geometry replay
found 11,852 matched proposals, 1,143/1,149 GT represented (6 unrepresented),
2,147 clamped regression targets and target-balanced containment fractions
0.3725728386 / 0.5889477290 / 0.8004249897 at padding 0.5/1/2.
Therefore v1 chooses no padding and stops before CNN extraction/fitting. No
actual producer Run, head, validation detection result or fresh access exists.
This is an input-observability finding; it does not test box-refinement efficacy.

V2 changes only the train-only context policy: append padding choices 4/8/16,
choose the smallest satisfying the same target-balanced >=0.90 containment.
This directly addresses the reference extent being outside small proposal crops.
Larger views may dilute local detail after Resize224; this risk is disclosed and
will be measured through the unchanged detection criterion, not assumed away.

The GT association, weights, targets/clamps, CNN/features, scaler, ridge .001,
NMS, E003 scores, data partitions, +0.05 recall criterion and fresh firewall
remain unchanged. This is no regularization/model sweep: select one input scale
with training geometry, then one fit and one validation. No threshold was
relaxed and no primary outcome was observed. v2 requires new exact-commit
independent review before producer Run S01-E005-R001.
