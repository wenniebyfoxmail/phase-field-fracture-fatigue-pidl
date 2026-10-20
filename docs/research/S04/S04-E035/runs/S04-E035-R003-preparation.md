# R003 — authorised diagnostic envelope, not launched

Authority source: human-delegated original research HQ,
`01a14bb9-6cd1-7ee2-9647-5190d786f7ba`, new message approving the exact
`a5d65d21` one-state diagnostic after R001. This was not a reuse of R001 or
a direct new human message in this chat. It authorized only CITPC12, U=.03,
unchanged AT1/AMOR/mesh/initial state and checks; no full trajectory or PIDL.

Envelope: 180 total wall seconds including this round's preparation, staging,
syntax/admission, at most90-second native child and retrieval; one mechanical
admission, ≤4CPU/0GPU, peak RSS monitored against16GiB, output≤10GiB. Old
R001 and preparation/unknown costs remain separate and are not reset.

The owner conservatively began counting local preparation/review at
2026-10-20T22:53:10Z (23:53:10 BST). During preparation the tighter CPU/RSS
limits were bound to the reviewed supervisor: 4-core affinity, four MATLAB
threads, 1-second waits and a separately sampled Process object. This local
preparation consumed148.921050 seconds before the launch guard ran, leaving
31.078950 seconds. The guard requires at least65 seconds for known first-state
work plus retrieval; it therefore exited **before subprocess/SSH**.

Original envelope ended22:56:10Z. No new envelope or clock reset was inferred.
This is a local orchestration/budget failure, not a numerical result. Scientific
attempt was not consumed: 0 SSH, 0 remote staging, 0 native calls, 0 workers,
0 scientific compute, 0 PIDL steps. No R003 remote process or state is claimed.
Local elapsed prep is wall time, not measured CPU integral. The exact original
packet and no-launch receipt remain under
`local_archive/experiments/S04-E035/runs/S04-E035-R003/`.

This was avoidable execution overhead. Corrective work prepares the entire
single-call deployment before a possible fresh execution decision, rather than
spending that future envelope constructing its controller. A separate local
packet lives under `preparation/R003_corrected_packet/`; the old packet and
failure history are intact. Account matching was also corrected before any
SSH: the old overescaped regex would have rejected a normal Windows account.

Prepared controller: `scripts/shear/execute_shear_diagnostic.py`. It defaults
to prepare-only; execute requires an explicit fresh authority start timestamp.
It binds native dirty-file hashes, local exclusive invocation claim, fresh
remote root, exact source/staged-byte hashes, resource constraints, one native
attempt and finite retrieval. Partial/unknown SSH outcomes are retained with no
automatic repeat. A previous ZIP cannot masquerade as this invocation's
retrieval. The prepared native numerical source is still `a5d65d21`.

No further remote execution is authorized by this record. A fresh decision can
instantiate the prepared package; it must preserve the previous consumed
preparation time and R00131.222s stop, and must not expand to30 states or PIDL.
R001's specific offending invariant is still unknown. D2 remains at diagnosis.
