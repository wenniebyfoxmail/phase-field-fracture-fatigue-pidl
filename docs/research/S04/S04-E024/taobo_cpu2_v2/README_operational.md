# D013 Taobo CPU2 v2 — preparation only

Owner Winnie/xw436. This Linux deployment wraps unchanged scientific commit
18d0e7cb1153dc969c1ee0c21c77ada1297b2d89, tree
14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23.
Mac v1 stays on hold and must not be executed. No human execution approval has
been recorded for this v2. Default CLI and false template are closed.

## Exact proposed action

From Mac user wenxiaofang, one approved local client performs exactly two SSH
connections and one SCP, all to drtao@172.16.100.2, using -F /dev/null,
BatchMode=yes, ConnectTimeout=15. First SSH uses /usr/bin/python3 -c with the
exact remote_entry.py bytes: same-connection anchor/deadline handshake, then
metadata/resource admission and fresh root claim. No numerical imports occur.
SCP uploads ONLY the action-manifest-bound payload.tar to:
/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/payload.tar
Second SSH uses the SAME exact entry source and --bootstrap-start, verifies
wire/entry and conditionally starts the owned detached dispatcher --run.
Full source, inputs and receipt checks precede scientific spawn. SSH disconnect
means unknown remote state, never proof of cancellation; no repeat connection,
retry, alternate machine or replacement RunID is authorised by this package.

The executable commands are constructed as argv arrays in transfer_and_start.py;
no shell wildcard, remotely downloaded code, rsync or old remote archive read.
The final local invocation requires an approval receipt that does not yet exist:
/Users/wenxiaofang/miniconda3/bin/python3 <control>/transfer_and_start.py \
  --authorization <package-root>/authorization.approved.json
All source/local/destination identities are in inputs_manifest.json and its TSV.
D012 uses three saved final.npz heads plus original ARCHIVE_MANIFEST.json; no refit.

## Producer admission (current state UNKNOWN, not probed)

Linux x86_64 GPUServer8, shared drtao; CPython3.10..3.12 at /usr/bin/python3.
Exact metadata requirements: NumPy1.24.4, Torch2.7.0+cu126, SciPy1.14.1,
Matplotlib3.9.2, psutil6.0.0, threadpoolctl3.5.0. Torch/NumPy are historical
producer observations; remaining versions are proposed requirements, not current
Taobo observations. Any mismatch stops without install, fallback or science.
/mnt/data2 must be mounted, affinity>=2 CPUs, MemAvailable>=4GiB and mount free
space>=2GiB. Record df -h / /mnt/data2 /mnt/data3 and affinity/load/memory/disk, not a reservation. CPU2 means library
thread ceiling; no GPU queries/usage. CUDA_VISIBLE_DEVICES is empty; all numerical
thread environment variables are2. Caches/temp/output under the new data2 root.

## Scientific invariants and order

Own E023 joint10000 seed7 c20s4, c60s4, c83s4, serial. 568 scaled-head coordinates;
D/leak/features/backbone/coordinate map/BC/physical window/damage/history/fatigue
frozen. Per state strict eta .1,.3,1 then diagnostic old-seven eta .3:12 profiles,
9 primary. Three profiles are historical comparison diagnostics, not relaxed
primary protection. No NN optimisation or original checkpoint writes.

13 primary actual protections: UV full/damage/background/inside-background;
strain same four regions; instantaneous elastic damage-driver same four regions;
actual native weak-force norm squared. No actual protection slack. True fields
are rebuilt from quantized original-dtype head through original raw encoder/Q4;
linear proxy consistency is not actual acceptance.

Cumulative Q is max of UV, engineering-strain and instantaneous driver field
change normalized by ORIGINAL own E023 FEM errors, and native mass-dual free-force
VECTOR change normalized by original own E023 force norm. Centre and scales stay
original E023 after relinearization, never last accepted head. Original zero UV
error stops solve; other zero scales demand exact zero change. No2% parameter cap.

Max3 linearizations/profile, SLSQP maxiter200/ftol1e-10;9 ordered halvings, first
actually acceptable candidate. No proxy-feasible returned step, solver exception
or all9 rejects stops that profile at last accepted head. Identity/hash/nonfinite/
map/resource failure stops remaining run; no alternate solver/multistart/retry.
Incomplete rows stay incomplete, not zero gain. Science source has final authority.

## Budget and temporary-copy policy

Original 300 nontraining/preflight +1800 numerical +900 independent replay/
aggregate +120 render <=3120 seconds remain unchanged. Prior71.93754945798841s
is NOT reset; conservative10s v2 package/check reserve gives base81.93754945798841s.
All transfer/hash/admission is inside remaining nontraining balance. The first SSH
emits producer monotonic anchor BEFORE metadata; client ACK receive elapsed
produces producer deadline anchor+(300-base-ACKelapsed), conservatively early.
This SAME absolute deadline follows final SSH/dispatcher. Scientific handoff books
one producer-local5s envelope inside300. No clock sync assumption or fresh budget.
Same anchor gives global3120 deadline. Client timeout is not remote cancellation.

Per process RSS3GiB; original legacy-loader2GiB remains. One combined1GiB bound
covers frozen charge for retained local D013 archives plus entire fresh remote
root. Before SCP, local+wire AND predicted extraction peak must fit. Only after
complete member/input/source verification delete EXACT task-owned payload.tar
and package/science.tar.gz on producer; originals and immutable local wire stay.
No other deletion, GPU intervention or other user's PID action is authorised.
Supervisor only owns this newly created process/session group; recheck exact cmdline, elapsed/create time and cwd immediately before termination.

## Evidence and limits

Scientific Code Ready and prior70 synthetic /10 semantic checks are reused by
exact source/tree; real Torch is not imported during local v2 preparation.
Deployment synthetic checks and separate review do not prove Linux numerical
admission. Producer actual fields, all visited candidates, scalar decisions,
independent replay and complete three-state aggregation are required after an
approved execution. Preserve existing Mac native-LR/mass/D/rho portability
exceptions and numerical warnings; never relax strict checks to manufacture PASS.
Report full/damage/background/inside-background UV, strain, weak residual,
instantaneous driver and cost separately. .001 is historical, not a universal
physical tolerance. This fixed-history diagnostic cannot qualify coupled damage,
crack propagation or fatigue decisions; application tolerances remain undefined.
