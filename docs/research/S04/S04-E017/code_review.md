# Code Ready review

7292eb6b3fe3820a398ad45be0c419938f27c941: NO-GO.
B1 required primary displacement and final regional metrics to be independently
recomputed from saved prediction.npz, exact admitted reference and native-Q4 mass.
Correction adds required --reference-root; validates four exact references before
aggregation, recomputes full/damage/background errors and contributions from
saved arrays, and rejects disagreement with metrics/step10000 monitor at atol1e-14.
Synthetic regression proves a hash-consistent contradictory prediction cannot pass.
48 related local tests passed; corrected exact-commit re-review pending.
