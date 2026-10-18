# Request 31 U0.1175 launcher v6 review request

## Requested verdict

Return one read-only verdict for this exact immutable candidate:

- `PASS_REQUEST31_U01175_LAUNCHER_V6`
- `MODIFY_AND_REREVIEW`
- `FAIL_HOLD`

This review cannot create approval/preflight or start production.

## Why v6 exists

The v5b reviewer returned `MODIFY_AND_REREVIEW`. It required three bounded
launcher-evidence repairs:

1. attribute MATLAB to a worker-owned, post-worker-start descendant and record
   its PID, parent PID and creation time;
2. guarantee a terminal worker receipt after `WORKER_STARTED`, including a real
   missing-MATLAB-executable failure;
3. make native stdout/stderr single-encoding and prove they decode cleanly.

Confirmed root-cause boundary remains deliberately broad: v4 direct
`Start-Process matlab.exe` did not produce an observable persistent production
launch, while call-operator validate-only succeeds. Existing evidence still
does not isolate quoting, MATLAB launcher/stub behaviour or process lifetime as
the unique v4 sub-cause.

## Candidate identity

- Windows root:
  `C:\q4runs\request31_u01175_derived_snapshot_20261009_v6`
- review root:
  `C:\q4runs\request31_u01175_launcher_review_20261009_v6`
- files: 18, excluding manifest
- manifest SHA256:
  `61725acf0a07caa9c7b0e622c81f30d496f0f2d184cf0abaad419a5bba6e0d53`
- diff-contract SHA256:
  `e13557d4bb57190dc94e27c6f0ee8b7617201d93286b198e9018f09c9a2004fd`
- parent commit:
  `862992a60edc7f59335365beacb5c71fc8592a7a`
- parent snapshot manifest SHA256:
  `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c`
- run ID:
  `hard5_u01175_stage0b_43d36a6de8a9431a803a17ad019a5bb9`

## Windows R2025b process ownership

The real harmless probe established that R2025b creates a worker-owned
two-level MATLAB chain:

```text
PowerShell worker -> bin\matlab.exe launcher -> bin\win64\MATLAB.exe engine
```

The selector therefore rejects global, pre-existing and unconnected MATLAB
processes, traverses only descendants of the exact worker, requires creation at
or after `worker_started_at_utc`, and returns the unique MATLAB leaf in that
owned chain. The authoritative probe captured:

- worker PID: `27552`;
- engine PID: `49732`;
- engine parent/launcher PID: `25640`;
- engine creation time: `2026-10-09T01:56:26.4540870+00:00`;
- handshake: `PASS_LIVE_OWNED_WORKER_MATLAB_HANDSHAKE`.

Handshake failure cleanup enumerates and stops only the exact worker-rooted
descendant tree, then confirms the stopped PIDs have exited.

## Terminal receipts and log encoding

After `WORKER_STARTED`, worker execution is enclosed in `try/catch/finally` and
always writes a terminal receipt distinguishing:

- `matlab_exit_code` for a launched MATLAB process;
- `powershell_exception` for launcher/PowerShell failure.

The real nonexistent-executable probe passed and produced:

- `missing_matlab_probe_worker_started.json`;
- `missing_matlab_probe_worker_exit.json`, SHA256
  `89e795cbc56a77aaba292cd8bf8b4302061219cd8627c64c1fa1255ea89e1581`;
- empty native stdout/stderr files and a terminal heartbeat.

Native stdout/stderr are written only by native redirection and declared
`utf-16le`; PowerShell never prepends text to them. The test decodes both files
as UTF-16LE, rejects NUL/replacement characters, and requires the readable
`REQUEST31_UTF16LE_OK` marker.

## Exact no-solve results

- MATLAB implementation regression: **11/11 PASS**
  - receipt SHA256:
    `4c87cc10f00791689d11caa6d25cdf9946d02efa7a300697055fa046c9b5e26a`
  - stdout SHA256:
    `8a29b5b25c0bb44b9343f8a728c0f13def4141279fd0dfe8cc8590d70fc42347`
- authorization regression: **10/10 PASS**
  - receipt SHA256:
    `4f39a6fefe79fa90a06e7b6fde04b1891954e8457229866705171dc912326333`
  - stdout SHA256:
    `9c8315316039946d67c38ff4d7f73ddc4be10259c967333298982566183aa0bd`
- spawn-contract regression: **12/12 PASS**
  - receipt SHA256:
    `234c412430461d660f6f8931fe49ad8b363b9b5d49583cbd7f5cf1d76166b65e`
  - stdout SHA256:
    `01920104adc34b5631ca3535ae6238b7ed310701e0b7154124e9e9da0d3b6f71`
- authoritative launcher validate-only exit: `0`;
- all authoritative stderr logs are empty, SHA256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The spawn suite covers the real owned two-level MATLAB chain, unrelated MATLAB
rejection, wrong-parent rejection, real missing executable terminal receipt,
worker-not-started, missing sentinel, nonzero MATLAB exit, timeout, v6
review-root equality and final clean environment.

## Final safety state

- MATLAB process count: `0`;
- production output root: absent;
- scientific payload created: `false`;
- approval: absent;
- production preflight: absent;
- production retry: `false`.

The harmless probe calls neither Request 31 nor the solver. A review PASS would
establish launcher code readiness only; it would not authorise production.

## Raw evidence

`local_archive/experiments/S04-E016/request31_u01175_launcher_review_20261009_v6/`

Bind any verdict to manifest
`61725acf0a07caa9c7b0e622c81f30d496f0f2d184cf0abaad419a5bba6e0d53`
and the frozen run ID above.
