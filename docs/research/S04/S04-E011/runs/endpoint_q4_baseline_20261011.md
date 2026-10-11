# Q4 endpoint baseline run receipt — 2026-10-11

Run: `pf_s04e011_endpoint_q4_460adc9_20261011T2240Z_wmi`.
Status: `SOLVER_STARTED__BASELINE_REPRODUCTION_PENDING`.
Producer: CITPC12 / citpc12-ssh, Windows MATLAB R2025b CPU single computation thread.
Code: `460adc93d5f2a8e310d228bb086e8066c16477b3`, branch
`codex/hard5-q4-t3-2x2-20261005`, clean at staging, independent review PASS.

WMI service isolated process creation at 2026-10-11T22:40:30Z.
Wrapper PID20892; MATLAB launcher14400; actual MATLAB worker47768.

Remote root: `C:\Users\xw436\jobs\E011_EP_460adc9_20261011T2240Z_WMI`.
Command: MATLAB `-singleCompThread -batch "run('<root>\entry.m')" -logfile '<root>\matlab.log'`,
with stdout/stderr captured separately by the wrapper.
Runner SHA256 `e2cc8dc8f15292ce8808f2eea36cb822c4365d4fa71891c282c70b9d53bc7e72`.
The generated runner restores the accepted s3 tangent and copies the exact
frozen source block. Immutable source file hashes and input identities are
verified before Newton execution.

The earlier 22:38 Start-Process attempt exited before solver execution and is
recorded separately, with zero logs and no output folder. This launch is a
fresh Run, not a restarted numerical trajectory.

The first two UV Newton residuals printed 1.62302e-5 and 6.74571e-8; the first
phase residual was0.00734856. They match the archived production prefix.
Only a single peak substep is solved; history commits0. No modified arm starts
automatically. Protocol and final gate: `../endpoint_baseline_protocol_20261011.md`.

Evidence root:
`local_archive/experiments/S04-E011/runs/pf_s04e011_endpoint_q4_460adc9_20261011T2240Z_wmi/`.

Final output retrieval is pending. Launch and prefix agreement do not establish
full baseline reproduction, stationarity, or field-mechanism agreement.

## 22:44 UTC update: instrumentation failure fixed; fresh solve running

The 22:40 WMI run stopped after its first outer iteration with MATLAB
`Subscripted assignment between dissimilar structures` while initializing the
trace. No history commit or accepted endpoint occurred. The numerical prefix
matched the original; this is an instrumentation failure, not a physics verdict.

Fresh run: `pf_s04e011_endpoint_q4_d1daba3_20261011T2243Z_wmi`.
Code `d1daba34249e602bcfb0ffa9fbecbd307e6432c2`, independent review PASS;
only empty trace field-schema initialization changed. Startup at22:43:29UTC.
Wrapper32328; MATLAB launcher21868; actual worker34936.
Remote `C:\Users\xw436\jobs\E011_EP_d1daba3_20261011T2243Z_WMI`.
Runner SHA256 `549f8b496195e33d75b288be635103b2a5965e32cdce3c67ca381be56c6fd894`.
Trace schema sanity passed; full outer1 completed and progress.mat was written;
outer2 started. Status `SOLVER_RUNNING__BASELINE_REPRODUCTION_PENDING`.

The original solver parameters, immutable predecessor and final reproduction
gate remain unchanged. Final retrieval and gate evaluation are pending.
