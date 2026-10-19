# FN776 self-contained deployment procedure — future approval only

CardID: `S04-E011-UVH-C1-FN776-CARD-r1`.
New RunID: `pf_s04e011_uvh_c1_fn776_r1_20261019`.
No root, claim, producer access or scientific run is created by this document.

## Source integrity

Mac creates one parentless code-only snapshot from an exact committed Dev SHA,
with SOURCE_PROVENANCE.json listing every path/blob/size, original mechanics
blobs and the full local-module catalogue. Export a full bundle with NO base
prerequisites. On Mac, initialise an empty repository, fetch that bundle, check
out the exact snapshot and run the standard-library verifier. Run git fsck,
check clean/no-extra/no-symlink/full-object state, AST-parse Python and verify
local import closure (including SENS_tensile/field_computation.py). A negative
omitted-module test must reject an incomplete snapshot. No runtime module import.

Final card binds Dev SHA, producer snapshot SHA, bundle ref/bytes/SHA256 and
its own Git revision. A normal history-dependent patch/bundle is prohibited;
the previous missing-object checkout is immutable and never repaired or reused.

## After exact final human approval

1. Read-only local chat/process review: list current chats, inspect possible
   duplicate c1s4 UVH/FN776 activity; never send another chat a prompt. If ownership
   is ambiguous stop. SSH alias gpu-taobo must resolve to the intended Taobo host.
2. Read-only SSH checks: host identity, command ps, GPU7 ordinal/UUID mapping,
   GPU applications and service identities, utilisation/free memory; df of /,
   /mnt/data2 and /mnt/data3; host RAM. Confirm both new paths and old attempt
   identity ledger do not indicate an existing/unknown attempt. No input reads.
3. If any duplicate, unknown process, identity change, resource shortfall,
   path collision or SSH error occurs, record a terminal preparation/admission
   stop; do not try again or choose another GPU. Frozen GPU7 policies are in
   inputs_fn776.json. Existing service IDs are historical, not present evidence.
4. Only after prechecks create the fresh root
   /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019.
   Transfer only the reviewed code.bundle, verify its bytes and SHA256. Initialise
   root/code as a new empty Git repo, fetch the exact bundle ref and detach at
   the card's producer snapshot. No prior checkout, alternates, partial clone or
   network object retrieval. Run its standard-library verifier with -B and the
   exact SHA. Save verification output/identity receipt in the new root.
5. Check current chat/process duplication again immediately before launching.
   Launch exactly once via detached setsid/nohup, CUDA_VISIBLE_DEVICES fixed to
   GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81. The guard has no configurable budget,
   input, solver or device override. Its exclusive attempt_claim.json consumes
   this card before its own repeated three-sample resource admission.
6. Guard permits either EMPTY GPU7 or the exact two frozen services, and pins
   that mode for the attempt. Any unknown/subset/changed service or mode change
   stops only the owned worker group; no relabelling or process manipulation.
   It checks code and dependencies before any of the five scientific files.
   Worker hashes exact files once, then decodes permitted keys and performs one
   FN776 solve with the frozen budget. All task caches/logs live under data2.
7. Retrieve results/read receipts and terminal state once, generate a transfer
   manifest and compare retrieved hashes. Retrieve partial evidence after a
   failure; no rerun. SSH visibility loss requires read-only state reconciliation,
   never blind resubmission. If unknown, report unknown rather than success.

Root: `/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019`.
Output: `/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r1_20261019`.
GPU: Taobo physical7, UUID above, worker logicalcuda:0. The card will give the
exact snapshot-bound command. No deployment or live resource validation occurs
during this preparation. No reset or purchase of usage allowance is authorised.
