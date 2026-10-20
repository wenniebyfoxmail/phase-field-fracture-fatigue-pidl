---
experiment_id: S09-E017
review_scope: chunked deployment candidate
reviewed_commit: 6a7f5bed3cc4cefdb865b214da3367a5666d0aaf
verdict: E017_CHUNKED_DEPLOYMENT_REVISE
date: 2026-10-20
---

# Independent review round 1

The exact-commit review found four blocking control gaps:

1. A stopped assembly printed a stop result but the CLI still exited zero.
2. An I/O error after publishing the archive link could leave the archive
   visible without a truthful receipt; ordinary `OSError` was not contained.
3. An `import-legacy --report` conflict was detected after chunk-store mutation.
4. The one-connection, one-transfer and 1,800-second limits existed only in
   prose; an unavailable SSH control socket could silently open a new
   connection.

The verdict applies only to commit `6a7f5bed...`; it did not authorise a remote
action. The repair adds non-zero stop exits, prepared/attempt/fallback journals,
pre-mutation path reservation, a process-group wall guard and an exact shell
plan whose multiplexed SSH commands set `ProxyCommand=/usr/bin/false`.
Fault-injection tests bind each repair. A new exact-commit review is required.
