# D013 v2 deployment review

Verdict: **CHANGES_REQUIRED**. Deployment scope only; scientific execution is not authorized.

The existing scientific Code Ready at exact `18d0e7cb1153dc969c1ee0c21c77ada1297b2d89` / tree `14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23` is reused unchanged. The final payload and action manifest have not been assembled or bound in this review. Current Taobo environment remains UNKNOWN.

## D1 [P2] Account the full final SSH and remote handoff interval

Location: `transfer_and_start.py:84`.

The client books elapsed+5 seconds and times out its own SSH after5 seconds. The remote bootstrap starts a separate5-second monotonic window only after the SSH command arrives. Killing/timing out local SSH does not prove termination of the remote bootstrap. With4 seconds of connection/delivery delay and4 seconds of remote bootstrap work, the dispatcher can start8 seconds after the client invocation while only5 seconds is charged. run_science then starts a new monotonic origin; its additional science-handoff reservation does not cover that omitted transport/bootstrap interval. This can undercharge the300s preflight phase and shift the3120s cumulative deadline.

Required: Use an enforceable end-to-end final dispatch envelope or explicitly charge separate bounded connection and remote bootstrap envelopes, entirely inside the unchanged300s. Keep unknown outcomes no-retry. Add a pure synthetic delayed-delivery/client-timeout case that proves no uncharged remote launch is admitted; update plan/prose consistently.

## D2 [P2] Admit the combined remote upload size before SCP

Location: `transfer_and_start.py:61`.

The pretransport check verifies only local_archive_roots<=fixed_local_archive_bytes. It never checks fixed_local_archive_bytes+payload_bytes plus initial remote metadata allowance against the single1GiB cap. bootstrap-create checks an almost-empty remote root; SCP can then create the entire payload.tar without a remote watcher. If the manifest parameters leave insufficient combined capacity, the first combined-size rejection is after the full over-cap tar has already been uploaded. Final payload bytes are not yet frozen, so this review cannot establish that the assembled package avoids the path.

Required: Before any transport, reject unless the frozen local charge plus the full planned remote wire bytes and bounded bootstrap/control overhead fit the one1GiB cap. Bind/check this admission in the final action manifest; do not rely on a post-upload guard. Add a pure fixture proving over-cap payloads never invoke SSH/SCP.

## Checks and limits

Independently ran the authorized pure deployment suite:28 tests passed; wrapper wall0.232891s. Cumulative v2 check ledger0.466946s stays inside the reserved10s; original71.937549s remains charged. No Torch import, real data/model deserialization, scientific solve, training, SSH/SCP, producer probe, upload or installation was performed. Source files remained read-only.

Static review found closed default/false-authority paths, explicit package/source/root/hash binding fields, one-shot local/remote claims, exact proposed dependency metadata checks, safe regular-file payload extraction with per-member hashes, unchanged per-state numerical admission, persistent supervision of the new scientific process group, and task-owned removal of only the two declared transport copies after source/input verification. These findings do not assert final package integrity or current producer compatibility.

Repair the deployment findings, re-review the changed code, then freeze/check the final action/payload manifests and all88 members. Human approval of that exact final account/target/version/source/payload/path/action remains required before transport. Code and metadata hashes, exact test command/log hash and explicit zero-execution fields are in deployment_review.json.
