# S09-E017 final execution-control focused review request

Review only the control and identity diff after the already reviewed real
adapter commit `662005f1fde22cb9a6e8069f4e430b7190f21860`. Do not repeat the
scientific design or full adapter review. Bind the verdict to the exact current
commit and supplied immutable package.

Verify:

1. the authoritative card, disabled candidate and authority schema bind core
   `5ac6b795`, design `06bf5fef`, integration `3a5a2020` and adapter
   `662005f1`, the same data hashes, Run ID, paths, arms, 3x64 budget, beta
   0.25, exposed cycles and no-holdout boundary;
2. the tracked authority template cannot resolve or launch, and a later
   authority must bind the focused-reviewed HEAD, candidate hash, code archive
   hash, network recovery, one admission plus one complete run, and no retry or
   fallback;
3. resolver and runner validate authority/archive/candidate identities before
   scientific imports or asset reads, and CLI paths equal the frozen candidate;
4. the live control admission and adapter together enforce Linux/host/cwd,
   process identity, GPU, clean code, asset hashes, fresh paths, wall/VRAM/RSS,
   disk/output/temp/archive budgets and zero pre-operation counters;
5. first-stop and completion receipts preserve the first reason, exact failed
   artifact, process/resource state and last-complete counters without leaving
   contradictory completion evidence;
6. the known SSH exit-255/network state remains a blocking external
   prerequisite and no test or command in this package contacts a remote host,
   reads real scientific assets or constructs a scientific runtime.

Return one verdict: `E017_FINAL_EXECUTION_CONTROL_READY_PASS` or
`E017_FINAL_EXECUTION_CONTROL_REVISE`. For REVISE, give the smallest concrete
counterexample. This review cannot grant execution or establish a scientific
result.
