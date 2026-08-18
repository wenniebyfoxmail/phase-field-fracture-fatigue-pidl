# RRaPINN G4 prerequisites — offline qualification

Status: **OFFLINE FRAMEWORK QUALIFIED; G4 LAUNCH STILL BLOCKED**.

Independent review v4 verdict: `APPROVE_OFFLINE_PREREQUISITES_ONLY`; no P0/P1.
The approval explicitly excludes Taobo smoke and training authorization.

This gate implemented and tested the work that can be completed without a
producer run or a new FEM export. It did not enter a training loop and did not
access U0.11 or U0.13.

## Outcome by frozen blocker

| Frozen prerequisite | Current result | Evidence boundary |
|---|---|---|
| c60 restart materializer | `PASS_OFFLINE` | Future-free 301-row bundle; atomic staging; manifest SHA `df581bb...03e9` |
| true mechanical residual export | `PASS_OFFLINE_CORE_AND_HOOK` | Shared autograd residual definition; optimizer-post/pre-history-refresh hook; Taobo code-path smoke still required |
| exact c76/c82/c83 FEM bundle | `EXTERNAL_BLOCKED` | c82/c83 exact native-Q4 assets absent; Request 27 issued to Windows-FEM |
| boundary-only first-detect receipt | `PASS_OFFLINE_LOGIC` | Hard5 raw-step mapping and immutable receipt tested; real arm receipts still require producer execution |
| c60-to-c61 A replay sentinel | `FRAMEWORK_READY_EXTERNAL_BLOCKED` | decoded exact comparator ready; step301--305 replay must run on Taobo |
| c60/c76/c82 lambda audit | `PASS_OFFLINE` | fixed lambda contributions 0.795%, 0.972%, 1.000%; no retuning |
| contained-domain projector | `PASS_OFFLINE` | 85,113 contained rows; 1,295 fallback rows excluded; constant error 0 |
| producer/blind/runtime evidence | `PASS_OFFLINE_CONTRACTS` | validator, seal and unblind fixtures pass; real external receipts and blind metrics remain unavailable |

The contained operator is deliberately a `centroid_containment_assignment`.
It is not a conservative area-overlap projector. Headline metrics may use only
the 85,113 contained rows; the 1,295 fallback rows remain sensitivity-only.

## Frozen local artifacts

- c60 bundle v2 manifest SHA256:
  `df581bb790e91660a5a4be735fc0f3e11c699f329b0f4ce05af36b31fa2c03e9`;
- contained projector content hash:
  `a69f4cb2df0a42e8b514b87a53289a8edc919d4d8f1cd9853948b764e5ea729d`;
- contained projector NPZ SHA256:
  `a6068a3d718f1343c761cb772e31aed45ce348c72066cb3af646678703998cff`;
- lambda audit manifest SHA256:
  `63731e96d167725c19638a88c0ffee0cbb6ee43693cb6bee2dd8e74748c31353`.

The earlier `c60_restart_bundle` without explicit semantic/non-finite records
is superseded by `c60_restart_bundle_v2` and must not be staged.

The targeted G4/G3-adjacent suite passed 80 tests, and selected modules passed
`py_compile` plus `git diff --check`. A full-repository `pytest` collection was
not available in the current Mac environment because two unrelated LTPP tests
import the absent optional dependency `arviz`; no G4 test failed before that
collection stop.

## Decision

The implementation gate passes only for offline capability. G4 training is not
authorized. The smallest next gate is a Taobo producer prerequisite smoke:

1. stage both arms from the same v2 manifest;
2. replay the risk-absent arm only through step305 and pass decoded exactness;
3. exercise one true-residual export and boundary trace on the real code path;
4. collect runtime externally;
5. stop and return evidence for independent review.

This smoke still cannot replace the missing c82/c83 FEM exact-peak export and
cannot authorize the full c61--event A/B pilot. A separate explicit user `go`
is required after independent review of the producer-smoke packet.
