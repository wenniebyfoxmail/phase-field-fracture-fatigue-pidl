# Launch attempt 1

- Method: PowerShell `Start-Process` from an OpenSSH session
- Reported child PID: `39108`
- Outcome: orchestration failure before runner preparation
- Evidence after 12 seconds: process absent; GPU 0 remained at approximately 310 MiB and 0% utilisation; formal output directory absent; `receipt.json` absent; redirected stdout and stderr empty
- Scientific work performed: none evidenced; no training output, checkpoint or evaluation artifact was created

The detached child did not survive closure of the Windows OpenSSH session. This method is retired for this run. The next attempt uses a named Windows scheduled task and the same frozen approval, roots, code snapshot, data lock and output path. Because the formal output directory remains absent, the runner's fail-closed `exist_ok=False` condition is still intact.
