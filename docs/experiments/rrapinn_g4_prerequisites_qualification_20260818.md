# RRaPINN G4 prerequisites — offline qualification

Status: **OFFLINE FRAMEWORK AND BOUNDED PRODUCER SMOKE QUALIFIED; G4 LAUNCH STILL BLOCKED**.

Independent review v4 verdict: `APPROVE_OFFLINE_PREREQUISITES_ONLY`; no P0/P1.
The approval explicitly excludes Taobo smoke and training authorization.

This gate implemented and tested the work that can be completed without a
producer run or a new FEM export. It did not enter a training loop and did not
access U0.11 or U0.13.

## Outcome by frozen blocker

| Frozen prerequisite | Current result | Evidence boundary |
|---|---|---|
| c60 restart materializer | `PASS_OFFLINE` | Future-free 301-row bundle; atomic staging; manifest SHA `df581bb...03e9` |
| true mechanical residual export | `PASS_BOUNDED_PRODUCER_SMOKE` | Real Taobo optimizer-post/pre-history-refresh c61 peak export passed exact schema/hash/tail recomputation |
| exact c76/c82/c83 FEM bundle | `EXTERNAL_BLOCKED` | c82/c83 exact native-Q4 assets absent; Request 27 issued to Windows-FEM |
| boundary-only first-detect receipt | `PASS_BOUNDED_PRODUCER_TRACE` | Real A trace contains exactly steps301--305, correct Hard5 mapping and no c61 trigger |
| c60-to-c61 A replay sentinel | `PASS_EXACT_DECODED_REPLAY` | Taobo A endpoint and six frozen histories exactly match the reference prefix through step305 |
| c60/c76/c82 lambda audit | `PASS_OFFLINE` | fixed lambda contributions 0.795%, 0.972%, 1.000%; no retuning |
| contained-domain projector | `PASS_OFFLINE` | 85,113 contained rows; 1,295 fallback rows excluded; constant error 0 |
| producer/blind/runtime evidence | `PARTIAL_PRODUCER_PASS` | External A runtime exit0/wall/RSS and smoke receipts pass; B runtime, full-pilot receipts and blind metrics remain unavailable |

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

## Bounded Taobo producer-smoke result

Commit `fb9538553557dcde29ff50ff14973af2921570bc` added a fail-closed opt-in
guard and passed 84 targeted tests plus an independent P0/P1 review. Taobo run
`pf_rrapinn_g4_prereq_fb95385_20260818T215547Z` staged A/B from the same v2
manifest, executed only risk-absent A, and naturally exhausted after raw steps
301--305. It produced a valid step304 c61-peak residual pair, an untriggered
five-row boundary trace, seven 306-row histories, endpoint305 model/checkpoint,
and `PASS_EXACT_DECODED_REPLAY`. External wall time was 2:55.02, maximum RSS
1,588,324 KiB and exit status zero.

Independent packet review returned `APPROVE_PRODUCER_SMOKE_PACKET_ONLY` with
P0=0, P1=0 and two P2 caveats: the archive redirect resolved inside the fresh
`/mnt/data2` checkout rather than the declared archive root, and the downloaded
packet cannot provide host-level proof of every path access. Neither caveat
authorizes broadening the run.

## Decision

The bounded producer smoke is qualified for tooling only. It cannot replace
the missing c82/c83 FEM exact-peak export, prove a residual-tail improvement,
or authorize the full c61--event A/B pilot. Repair/verify archive routing and
obtain the missing FEM truth before presenting a new launch gate. A separate
explicit user `go` remains mandatory.
