---
experiment_id: S09-E017
review_scope: finite chunked deployment repair
reviewed_commit: 6cf0b9b4c3f1aff3858ef073364f00618109289f
verdict: E017_CHUNKED_DEPLOYMENT_REVISE
date: 2026-10-20
---

# Independent review round 2

The second exact-commit review confirmed the four round-1 control gaps were
substantially repaired, then reproduced three new blockers:

1. `git get-tar-commit-id` legitimately stopped reading after the tar header,
   causing the piped `gzip` process to receive `SIGPIPE`; the plan incorrectly
   treated that as an invalid archive.
2. The guard did not consume the authority locally before starting the plan, so
   the same authority with a different receipt path could start twice before a
   remote attempt-path conflict was observed.
3. A slow prepared-journal write could cross the wall deadline and still be
   followed by archive publication.

The repair fully consumes the gzip stream before passing its bytes to Git,
publishes a fixed write-once authority-consumption record before `Popen`, and
rechecks the same wall clock after the prepared journal and before the link.
Local regression tests reproduce all three previous failures. A third exact-
commit review is required; this review performed no remote action.
