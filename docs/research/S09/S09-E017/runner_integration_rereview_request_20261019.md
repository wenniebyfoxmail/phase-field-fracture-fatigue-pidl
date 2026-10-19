# S09-E017 runner integration focused rereview

Review the manifest-bound revised exact commit only for closure of the four
round-1 findings.  The reviewed numerical core and scientific design remain
closed.

Please verify:

1. pairwise cosine is `None` exactly when the raw or scaled norm product is
   at most `1e-12`; finite defined cosines are bounded and consistent with
   the recorded vectors and dots;
2. the flattened projection log contains every active target/reference pair
   once, ordered by target then recorded permutation, with exact identities,
   Boolean skip/apply flags and finite `dot_before`; `F_AMP` never projects
   with S;
3. scaled and projected vectors plus pre/post-clip norms pass the deterministic
   standard-library replay;
4. a first stop bounds progress in the failed arm, prevents later-arm progress,
   gives pre-run stops update zero, and a second event preserves the first
   receipt verbatim; and
5. Boolean substitutions cannot impersonate frozen integer identifiers,
   counters, updates or flags.

The source may write only the canonical write-once failure-metadata receipt.
It must retain no scientific reader, model forward, autograd, optimiser
construction/mutation, subprocess/network, SSH/GPU or producer route.

Return first line exactly one of:

- `E017_RUNNER_INTEGRATION_CODE_READY_PASS`
- `E017_RUNNER_INTEGRATION_REVISE`

A PASS authorises only preparation of a separately reviewed final run package.
It does not authorise scientific-asset reads, model forward, optimiser
construction, training, SSH/GPU work, producer launch, holdout, rollout or a
scientific claim.
