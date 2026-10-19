# Exact final candidate — awaiting HQ one-shot admission and execution decision

This packet implements only the new question `L(selected simple C27)-L(selected separate A25)`: output-correction controllability in the accepted fixed-alpha family. It is not a repair run, exact R003 replay, old diagnostic retry or missing-figure rerender. Full scientific design/evidence remain in PROTOCOL.md and accepted source fe54ab36.

- Sole intended new RunID: `IU-OUTPUT-CALIBRATION-C27A25-20261020-R001`.
- Existing intended route: `gpu-taobo`, expected hostname `GPUServer8`, CPU only, `/usr/bin/python3`.
- Exact root: `/mnt/data2/drtao/wennie/IU-OUTPUT-CALIBRATION-C27A25-20261020-R001`; immutable code in its `code/` child.
- Future authority path: same root `/execution_authority.json`. **No such receipt is created in preparation.** `execution_authority.schema.json` is only a schema; resource_decision.json approves resources only, honestly human_approved=false/HQ_DELEGATED.
- Formal entry/argv: launch_command.json. `launch.py` is the independent outer watchdog; direct worker/controller use is rejected by parent/session identity. The command uses Python -W error from process startup; child environments preserve PYTHONWARNINGS=error.

After a separate exact HQ decision ONLY, deployment could place the reviewed source archive's code plus the authentic one-shot authority in the fresh root, with no prior run claims/outputs/log/cache/tmp/archive. Source deployment copies count within storage. The1200-second formal admission/execution clock starts on launch.py main entry, before source/config/authority verification, and covers all subsequent scientific/admission/controller work; prior network/source transfer is not scientific runtime and is not represented as inside that clock. No SSH/deployment/preflight is authorized in this preparation step.

The exact later producer command is:

```sh
/usr/bin/python3 -W error /mnt/data2/drtao/wennie/IU-OUTPUT-CALIBRATION-C27A25-20261020-R001/code/launch.py --config /mnt/data2/drtao/wennie/IU-OUTPUT-CALIBRATION-C27A25-20261020-R001/code/config.json --approval-receipt /mnt/data2/drtao/wennie/IU-OUTPUT-CALIBRATION-C27A25-20261020-R001/execution_authority.json
```

For the existing SSH route, the same command must be detached with the exact root's launch.stdout/launch.stderr (full shell form in launch_command.json); those files count as logs. No command has been submitted. The returned watchdog PID, controller/worker PIDs, code/config/package identities, actual admission environment and final lifecycle records must be saved. Do not infer completion from a dropped SSH connection, a tar file, or the controller's provisional receipt.

HQ-approved finite envelope:1200wall seconds,one allowed logical CPU for watchdog/controller/worker/helpers, combined sampled2GiB RSS,0GPU; total1536MiB, uncompressed archive700MiB, all existing category caps.0.25second combined HWM sampling and8GiB per-process AS backstops are not a hard2GiB RSS guarantee. POSIX alarm and independent parent monitor cover controller final I/O/exit; no hidden copies or budget extension. Termination/forensic latency must be disclosed if a deadline triggers.

Admission ordered first-stop checks, all still UNEXECUTED:

1. Exact new source/config/authority plus independent watchdog/session/fresh-root identity. Resource-only authority is rejected.
2. Current GPUServer8/Linux, expected historical Python3.10.12, NumPy1.24.4, Torch2.7.0, Matplotlib3.10.3; one CPU affinity, mount, RAM/disk/load. No dependency installation, fallback host or version relaxation.
3. All180 old input hashes/bytes and frozen1144case/19group/exclusion identity; R002 source/features hash. Then finite native float32 current/future2×128×128 representations for ALL required frames, before the first fit. No new data/holdout.
4. Only if admission is clean:1444predictor+722m=2166solves;1853280inner native candidate scores;16016outer seven-arm scores; all19groups/H10,H40/two channels/allC30. Same alpha10, tie rules, normalizers, native metric and full self-contained fields.
5. Figures+sidecars, uncompressed tar and all source/output hash manifests; worker actual exit then controller final hash/receipt/actual exit; outer watchdog validation, final receipt and distinct exit seal. Any identity/schema/library/warning/stderr/numerical/resource/exit error stops this attempt, preserves artifacts and forbids automatic retry.

Required retrieval: results.tar plus delivery_manifest.json, archive_receipt.json, controller_receipt.json, watchdog_receipt.json/watchdog_first_stop if any, watchdog_claim/run_claim, admission_environment/native_schema_admission/cpu_affinity, all logs including worker/controller/watchdog exit seals and fatal events, launch.stdout/stderr, last_context and first_failure. Live outer streams are deliberately not trusted as stable hashes inside the controller manifest; still retrieve/count them after watchdog process exit. Verify final PID seals, stderr/fatal absence and archive digest before treating evidence as complete.

Remaining HQ decision: exact permission for ONE formal admission+complete comparison using the final independently reviewed source/config/lock/archive. Acceptance of resources already exists, but data access, SSH/live admission and execution have NOT been authorized. Actual availability, target schema, host dependency versions and fit/time/RSS feasibility remain unknown until that single authorized admission; artificial tests are not a substitute. Keep the unknown-specimen/release-step/current-anchor/exposed-development and original R003 warning-contract limitations.

Interrupted-monitor cleanup retains every last observed PID/start-time/PGID/SID identity before later monitor I/O. An exited controller does not establish descendant cleanup: retained live group identities allow signalling only the owned group, and cleanup verifies that all known identities and active group members have terminated (zombies are inactive). Unverified reused groups are never signalled; unresolved live members produce cleanup_error. Start, deadline/failure trigger, cleanup completion and final callback seal include monotonic and Unix clocks. The final watchdog_exit seal is later than the candidate receipt and permits separate calculation of stop/cleanup/callback latency; it still requires actual process exit verification. Stopped attempts also receive this seal without changing STOPPED status.

Primary stop reason, trigger clocks and observed member identities are fsynced in exclusive watchdog_first_stop.json BEFORE cleanup starts. This record stays immutable; watchdog_receipt.json separately records cleanup-end clocks and any secondary cleanup error. Failure to persist the primary record never skips teardown: cleanup is still attempted, and the stopped receipt separately reports primary_persistence_error if that final write succeeds. No completion is accepted, and unavailable evidence is not claimed to exist.
