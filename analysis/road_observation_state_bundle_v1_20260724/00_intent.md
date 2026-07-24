# Intent: road observation-state bundle v1

Mechanism question: can the frozen Agent1 observation/state interface be consumed byte-identically by Agent2 and Agent3 without relabelling FEM latent fields as road sensors?

Cheapest test: schema adaptation and offline validation only. No training, no FEM solve, and no Taobo job.

Success: locked source hashes, one canonical state bundle, missing-aware consumer skeletons, and failure tests for provenance/uncertainty/masks/maintenance.

Failure: any missing road value is fabricated, any oracle field enters operational innovations, or interface pass is reported as real-road inversion.
