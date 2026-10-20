# D013 v2 deployment review r3

Verdict: **CHANGES_REQUIRED**. Focused review of added machine-rule checks; previous reviews remain preserved. Scientific18d0e7cb/tree is unchanged.

## D3 [P2] Continue supervising the owned group after scientific parent exit

Location: remote_entry.py:88.

terminate_owned returns immediately when the tracked Popen parent has exited. supervise_child exits its loop when that same parent exits, then calls terminate_owned on nonzero return, so an abrupt parent exit can leave an active same-group scientific worker unsupervised. A successful parent exit with an unexpected remaining worker is also never checked. The previous unconditional owned-group cleanup handled this leader-exit path; the new attribution guard removes it. Parent death does not imply process-group death.

Required: Retain enough attributable identity for the owned session/group to inspect and clean surviving task workers even after the leader exits. Before any member/group signal verify cmdline, elapsed/create_time and cwd plus the owned session/group; never signal a reused/ambiguous group by username or numeric PGID alone. Do not mark supervision complete while attributable owned workers remain. Add a pure synthetic case with a parent that exits while its child remains alive, and verify cleanup and stopped/failure accounting without touching other work.

## Checks and boundary

The exact three-path df check and live-leader process attribution are present. Independently reran37 pure deployment fixtures successfully; these do not cover the parent-exit/surviving-worker path. Cumulative check-wrapper wall is2.9766400436637923s, with prior failed fixture logs retained. No Torch import, real-data deserialization, scientific solve, SSH/SCP, remote probe or source edit occurred. This receipt does not review the upcoming regenerated final package and creates no execution authority.
