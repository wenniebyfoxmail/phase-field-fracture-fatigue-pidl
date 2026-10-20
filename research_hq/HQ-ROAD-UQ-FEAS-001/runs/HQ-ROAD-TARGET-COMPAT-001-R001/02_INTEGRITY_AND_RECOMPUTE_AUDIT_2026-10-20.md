# Integrity and recomputation audit — HQ-ROAD-TARGET-COMPAT-001-R001

Input byte counts and SHA-256 values match the frozen data lock. The complete CSV contains 2,903 rows with exact source counts, two expected GAPS384 empty masks and finite decision metrics. Fit/evaluation splits are group-consistent.

`independent_recompute.py` uses only the Python standard library. It independently recomputed source and global radius selection, group-weighted held-out means, retention ratios and the formal decision. All decision-facing values match `source_summary.json` within `1e-12`.

The three fixed visual panels and summary figure are readable. `SHA256SUMS.txt` records every raw artifact and process log. The result is complete for the frozen D4 contract.

