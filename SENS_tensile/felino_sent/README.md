# Locked Felino SENT PINN reproduction

This package implements a small-strain PIDL reproduction of the locked
MOOSE/Felino cyclic SENT numerical trajectory. It is a numerical benchmark,
not an experimental validation, physical truth claim, teacher qualification,
or strict solver-equivalence claim.

The frozen reference is the completed 38,000-cycle `FatigueICLA` run at MOOSE
commit `e0fc4af...` and Felino commit `ebef620...`. The contract fixes hashes
for both input decks, the mesh, and the 381-state scalar CSV.

Implemented correspondences:

- official 1 mm square notched mesh;
- bottom `u=v=0`, top prescribed `v`, free top `u`;
- AT2 crack density, spectral strain-energy split, and Felino residual stiffness;
- `FatigueICLA` mean-load driving energy with `R=0.5`, `n=0.5`, and a 100-cycle jump;
- asymptotic fatigue degradation with `alpha_critical=62.5 MPa`;
- scalar exports for damage integral, maximum damage, accumulated history,
  reaction force, and top stress; selected full-field checkpoints.

Known non-equivalence: Felino uses incremental finite strain, while this PIDL
runner currently uses small-strain plane strain. Consequently the first run is
diagnostic and cannot pass a strict solver-equivalence gate.

Mac preflight only:

```bash
python SENS_tensile/run_felino_sent_reproduction.py
pytest -q tests/test_felino_sent_reproduction.py
```

Production execution is guarded by `--execute`, rejects macOS, and requires an
explicit `CUDA_VISIBLE_DEVICES` on the authorised Taobo producer.
