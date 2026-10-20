# Linux validation entry review v1

MODIFY_AND_REREVIEW — static entry/card review only; no Linux execution.

Commit `f7874240a8c1eb70cf0ca3b6cbbf4604b54aedfb`; artifact `cf5dcb6fec677f4a319693df4f70900b07c5d0bd3175d7498699ed05e0fbc724`; actual validation-card SHA `b5db767b2afa66bf9039972a344f5b8779a5c73e843a05d5a7ac11dfb1a133a2`. All41 frozen file hashes/canonical artifact verified; previous39 preparation files are byte-identical to reviewed5bb17214. Old61 artificial regressions reused, not rerun for unchanged code.

1. **V1/P1 owned test cleanup:** parent_death49–78 only handles parent in finally; worker/guardian survivors after failed death safeguards are reported but left running. Pure fake-process probe returned passedfalse with both survivors and only kill(parent999) action. Bind owned identities before kill and independently clean/reap all on every exit, retaining testFAIL even if fallback cleanup succeeds. Cover startup and driver interruption.
2. **V2/P1 total deadline:** driver109–160 relies on Python SIGALRM while full-mesh NumPy/SciPy/IO execute in the same process; handling can be delayed in native/blocked operations. Imports/setup precede alarm. Add independent outer owned-driver guardian/wrapper, with cleanup reserve inside1800s and full actual costs. Keep alarm secondary.
3. **V3/P2 identity/allowance binding:** supplied card SHA is recorded rather than enforced against manifest's frozen validation card; permission/execution flag, exact root and5load allowance are not validated. Cost step cap is checked after execution. Reject altered card/root/loads/allowance before mutation or calculation; keep cost artifacts separate from prospective production root.
4. **V4/P2 CPU environment:** NumPy/SciPy import precedes affinity, and cost/helper environment omits formal CPU thread/GPU/temp policy. Set shared16core affinity and OMP/BLAS16/emptyCUDA/runlocal paths in pure-stdlib startup before pools/imports; propagate and record settings. Existing BLAS threads cannot be assumed confined by changing main-thread affinity later.

The numerical parity definitions, retained1e-10, exact cost worker, original5loads*.8, own history/cache, separate labelsIO and no-fit/retry structure are appropriate. These positives do not close the four entry constraints. Parent has acknowledged fixes and will provide a new exact wrapper/package.

No actual controller, SSH, profile, preflight, scientific arrays, state solve, training or retry occurred. Actual Linux capability/full-grid parity/cost remain unvalidated; preparationPASS cannot be inherited as runtimePASS. This review grants no validation or production launch for f787.
