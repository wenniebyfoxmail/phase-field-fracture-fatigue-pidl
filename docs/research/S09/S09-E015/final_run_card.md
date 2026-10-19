# S09-E015 final run card

- Run: `S09-E015-R001-output-trust-region-assay`
- Producer: `gpu-taobo` / `GPUServer8`
- Device: GPU index 5, UUID
  `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`
- Budget: 900 seconds, 10 GiB process-reserved VRAM
- Computation: 13 forward-only states, zero optimizer steps, zero autograd or
  gradient collections
- Inputs: frozen B25 update-500 checkpoint, two actual E014 endpoint
  checkpoints, E014 vector archive and endpoint evidence, same exposed
  16-cycle packet
- Grid: `0, 1/1024, 1/256, 1/64, 1/16, 1/4, 1`
- Fresh holdout/FEM/training: none
- Attempts: one; no retry and no alternate GPU
- Launch condition: exact implementation review PASS on the execution commit
- Stop conditions: identity/replay mismatch, incomplete state/evidence,
  nonfinite or hard-constraint result, wall cap, or VRAM cap
- Allowed conclusion: finite-displacement trust-region evidence on this
  exposed trajectory only
