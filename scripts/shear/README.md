# Static shear execution entry points

The current FEM/PIDL route has no wall-time, CPU/GPU-hour, epoch or solver-iteration budget. It retains the original numerical acceptance criteria and process ownership/resource checks.

- Supervisor: `supervise_manav_unlimited.ps1`. Remote payloads call their byte-verified copy `supervise.ps1`; that deployment filename is not a reference to a retired source.
- Qualified FEM continuation: `execute_manav_static_fem_progress.py` (R024).
- PIDL after the qualified FEM reference: `execute_manav_static_pidl_after_fem.py` (R028).
- Retrieval and comparison: `continue_manav_static_after_fem.py`. Run identifiers and existing launch claims are fixed; these are not invitations to launch duplicate runs.

On 2026-10-23 the user requested removal of obsolete time-limited monitoring scripts. All 10 such PowerShell sources and their 18 expired launch entry points were deleted. No obsolete launcher was redirected to the unlimited supervisor. Removal paths and original SHA256 hashes are recorded in `docs/research/S04/S04-E035/retired_time_monitors_20261023.json`. Historical source remains in Git commit `aa634414f69677d9b9299680ed365ec9c441152a`; executed payloads, terminal logs and scientific results remain in the experiment archive. Those historical copies are provenance, not current execution entry points.
