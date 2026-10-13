# E015 review handoff — 2026-10-13

Execution is NOT_READY. No new-cycle raw displacement preparation, FEM/q solve,
or stage12response conversion/scoring has occurred. High response remains reserved.

Frozen protocol firstcommitf187965, current exact implementation snapshot
636790eead60f39b0be4358520db0acaa47fb9b5, branch
codex/s03-e015-boundary-basis-20261013; parent2d8398e. Protocol unchanged between
the two commits, SHA256207a81cca8c6f35dcc9c7befc6471667297a8f5686b29aea89ff77c00b183743.

## Local checks — not independent approval

9new tests pass: synthetic source preparation with nonnumeric heldbody never
parsed; nested grid/damage bounds; equal-spacing affine interpolation; exact
contrast; mocked254solvercalls/fullfields/minimum selection; failed source-bound
completion stops before target access; profile/dependency tamper; common support
and planar z/w-only missingness invariance. Mockedfit is NOT actual FEM execution.
Reusedkernel5/projector5/inspector13 also pass:32total. Expected duplicateZIP
warning in the adversarial inspector test. New scripts/test compile; diff check
clean. Actual asset/field visual QA can only follow qualified preparation/run.

## Plan review request

Channel: existing ordinary ChatGPT conversation
https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb .
Material: protocol file only, displayed attachmentexperiment(20261013-111039).md.
Firstsubmission received Unknown error while models could not load; no verdict.
Same channel retry/reload restored visibly selectedPro, then sameplan re-sent.
Response is in progress; exact attachment accessibility and completed verdict
NOT yet verified. NoPASS, no CodeReady or actual-asset permission inferred.
Review scope: design/inputs/interventions/contrast/missingdata/budget only.
Requested reviewer not to solve/fit/access high data or waive downstream gates.

## Code Ready packet awaiting channel choice

Local immutable Git archive prepared, NOT transmitted as a CodeReady review:
local_archive/experiments/S03-E015/review/E015_636790e_code_review.zip
SHA256f5b430095ef00906397352d5363f704a8caebb5d4f136086aa57ee5efca39e87.
Contains protocol, newrunner/plotter/test and unchanged parser/kernel/projector
with their tests; no real new-cycle field or held target included.
Userasked asynchronously to choose independent read-onlyCodex (recommended,
repository/test access, Codexusage) orChatGPTWork (cloud snapshot/recompute,
sharedCodexusage), or defer code review. No answer yet; no reviewer spawned,
no new cloud task or alternative-channel dispatch. Transport failure alone
does not authorize switching channels. This follows the project-local
research-review-channels guidance, read in the current governance checkout.

Next: retrieve completePlanreview, apply exact bounded changes if needed and
freeze a new snapshot; after userchannelchoice perform independent exactcode
review; then light actualprep and independent both-boundary assetadmission;
only then the already conditionally authorized254-solve Taobo execution,
predictionfreeze and separate stage12validation. Never tune on viewed high data.
ObsidianAA2024tasknote/oneRoadmaplink synchronized with prospective status.

## Subsequent review history — 2026-10-13

The entries above are historical, not the current channel choice. The user
explicitly selected independent read-only Codex code review and authorized
conditional Taobo execution after plan, code and actual-asset gates.

Pro returned REVISE_PLAN for v1, bound to the 7,553-byte attachment SHA256
207a81cca8c6f35dcc9c7befc6471667297a8f5686b29aea89ff77c00b183743.
Blocking repairs: separate combined gain from interaction; replace undefined
“all poor” with the exact four-selected-arm/secant comparison; clarify the
soft 600-second completion budget and failed/incomplete status.

Prospective v2 at cc5bff302f27b0da171e8dbb30226d8cca8b43e8 incorporates
those repairs plus exact weighted secant-SVD and finite-source-mask semantics.
Protocol SHA256 is 46e439810dab56ff149c39e2368b1906604592f51b3a051f716b86ac84878cd6.
The uniquely named attachment E015_cc5bff3_protocol_v2.md was fully uploaded
and sent to the same visibly selected Pro conversation. Re-review is pending;
no approval inferred from submission or thinking status.

Independent Codex review of 636790e returned MODIFY_AND_REREVIEW: final
budget enforcement and figure/provenance guards were incomplete. Review of
cc5bff3 confirmed repaired source/artifact binding and weighted sensitivity
arithmetic, but reproduced one final-receipt overrun being marked succeeded.
Commit bf319f4d4f493609e7c25e0855ae0d72e02b1762 repairs this last issue:
artifact hashing precedes the final elapsed check; observed >=600 seconds
downgrades a fit to failed and raises TimeoutError. Protocol v2 is unchanged.
Independent read-only re-review of this exact commit is pending.

Local checks: 37 tests pass (14 new runner/view tests plus 23 reused tests),
including final clock [0,599.999,600] failure. Synthetic/mocked tests are not
actual asset admission or mechanics execution. No actual new-cycle preparation,
FEM/q solve or held-response conversion/scoring has occurred at this entry.

## Plan and Code Ready accepted; actual-asset review pending

Pro v2 returned PASS_PLAN after reading 156 lines / 9,895 bytes and independently
matching SHA256 46e439810dab56ff149c39e2368b1906604592f51b3a051f716b86ac84878cd6.
It closed both original blockers and checked the classification identity on
625 synthetic scalar quadruples. Scope: prospective design only; original v1
verdict and E014 outcome retained. Screenshot proof is archived at
local_archive/experiments/S03-E015/review/plan_v2_pass_proof.png.

Independent read-only Codex returned PASS_CODE for exact commit
bf319f4d4f493609e7c25e0855ae0d72e02b1762: 37 related tests passed; original
final-clock counterexample and independent hashing-to-601s counterexample both
correctly fail. No real data or FEM was used in code approval.

Producer adopted these bounded approvals and ran lightweight Mac preparation
S03-E015-R001 using the exact approved runner/dependencies. Receipt succeeded.
Cycle 225211.5 / reference 1, forces 4500.454902648926 / 9754.968643188477 /
14998.638153076172 N; 646 common training observations, source-weight area
424.4008210164802 mm2. B0/B1 fourth-neighbour maxima 1.3114835985769373 /
1.0249339794152215 mm. These are producer observations, pending independent
actual-asset recomputation, not a solve permission by themselves. Stage12 body
was read only as bytes for hash binding, not converted to response arrays.

Raw package and exact-source asset figure are under
local_archive/experiments/S03-E015/runs/S03-E015-R001/prepare and asset_QA.
Independent Codex actual-asset review is dispatched with training-only access.
No real mechanics solve, q fit or held scoring has occurred at this entry.

## Actual assets accepted after figure-only repair

Independent Codex rebuilt actual training assets from the locked ZIP without
opening stage12. Numeric assets passed: 41,603 source facets / 39,991 jointly
finite; 662 padding connections, 78,336 identity-valid triangles / 78,028
finite-retained; positive absolute source areas; identical ROI/weights; both
artificial meshes CCW and 0.9 mm spacing; all BC affine ranks 3; independently
recomputed BC difference <=7.81e-18 mm; priors and basis arrays match.

First actual figure review correctly withheld approval: 53 B1 arrowheads
clipped by fixed limits and legend overlaid the boundary. Figure-only commit
b8edbcfa0ffc40fba67e9baf363de51f1f82cd77 expands all panels to x +/-24 / y +/-16
mm and moves legends outside axes. Original figure retained as forensic history.
Independent re-review returned PASS_CODE + PASS_ASSETS for b8edbcf, with all
37 tests passing and no clipping/occlusion. Numeric runner, three dependencies
and protocol remain byte-identical to approved bf319f4.

Asset identities SHA256:
- prepared.npz: 26e93436210e9c2dbaa8e8e4e55480efe9ded6e5b5e0de5936152a05df1f6019
- preparation.json: 791f5e00f552d90a57b66791f44eccec7024f13c1a29cacf2c92bfa57dd81d26
- prepare receipt: 62ab2a0a9241fe683338d84209d030072f01f6961a307c1e1945d2870db28137
- corrected spatial PNG: 8a2a4fafc812bccc42e0731fc05a0840d215c93d85c1a38eecd4990e9964346a

These gates admit the frozen conditional diagnostic, not true damage,
original exporter compensation semantics, or physical validity. Producer
adopted approval and begins sync to fresh GPUServer8 root
/mnt/data2/drtao/wennie/S03-E015-R002. Only code and prepare assets transmitted;
no stage12 response body is in the remote fit input. Single-thread CPU mechanics,
no GPU allocation. Preflight: /mnt/data2 666G free; Python3.10.12,
NumPy1.24.4, SciPy1.15.3, OpenBLAS num_threads=1. Other users' jobs untouched.
Mac Git archive b8edbcf SHA256:
aac5458df13fdd5743e8588c009b723cf519a189fa892083f68dd909dab7e0c2.

## Independent evidence closure

R002 completed all254 solves in37.614s, froze nine predictions and was retrieved
with matching hashes before separateR003 held conversion/scoring. Independent
Codex reconstructed all252 training profiles, selection, q states, finite
secant-SVD and isolated spans using scalar fsum/hypot projection and analytic
2x2Gram singular values, avoiding matmul/lstsq/SVD. Maximum differences:
trainMAE4.34e-19mm, heldresidual5.64e-18mm, SVD5.42e-20mm/q. The disclosed
Mac NumPy RuntimeWarnings caused no detectable discrepancy. Allnine held
metrics/contrasts,643common observations,3missingIDs,coverage and provenance
bindings matched. No numerical solve or retune was repeated by reviewer.

First evidence review withheld approval only for figure delivery: profile
legend obscured training cells and three sidecars lacked explicit required
reading/provenance/limitation sections. Analysis-only79fd926 repaired these;
raw numeric packages and original figures remain untouched. Six formats/three
sidecars pass checker, profile legend is outsideaxes, allgridcellsvisible;
the two other PNGs are byte-identical to prior version. Independent re-review
returned PASS_CODE + PASS_EVIDENCE, producer adopted bounded verdict.

Exact delivery commit:79fd9266322c447fcc9d364a2d14c436e84f52f1.
- R002 fit receipt SHA256:13a32fdee52e94560f4bfd0d6ee1796624e760bc32661b59d08ec92e22616fa2
- R003 validation receipt SHA256:5bec2a18f6bbcf4ea69a268a34779fde8b094e3bd1c3c8d36ccc014e3877a065
- corrected profile PNG SHA256:8f893c998e5f016c59ca0829fe8a9832ee75bf46bfb5e6dc190a43a02412e4c9

Scope accepted: descriptive intervention-procedure diagnostic. Both selected
K1 states collapse toK0; exteriorBC/domain procedure worsens held response;
allmechanicsarms are worse thansecant. Component benefits versusfixedprior
andintact remain. This does not identifytruecause, truephasefield/material,
fatigue/future/road validity. Receipt chronology supportsfreezebeforevalidation
as recorded evidence, not independentlyauthenticated execution history.
No newcycle access, additionalfit or post-heldparametertuning authorized here.
