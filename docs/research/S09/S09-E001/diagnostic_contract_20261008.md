# Fixed P1 checkpoint diagnostic contract — 2026-10-08

Purpose: distinguish magnitude/location/projection/loss candidates behind P1 failure, with no optimization. C0/C1 synthetic processed archive diagnostic; not a revised P1 acceptance gate.

Freeze best step850 from R002 (f58df2d), exact config/statistics, same16 training windows, one-step target. Reuse load_data/inventory/model; no development evaluation, no optimizer or gradients, no alternate checkpoint. Runner diagnose_s09_p1.py. Taobo only, fresh R003, GPU0 if healthy/free capacity with .33 fraction.

Validity: exact checkpoint step/config/base commit; locked dataset; identical windows and checkpoint statistics; reproduce original ratio within1e-6 floating reduction tolerance; parameter tensors unchanged. Stop after16 forwards or on first validity error. Existing P1<=.8 FAIL remains unchanged regardless of diagnostic metrics.

Outputs: per-window area-weighted true/predicted growth,error,pre-projection sign areas/positive-negative masses; continuous growth overlap=min(pred,true), excess=max(pred-true,0),missed=max(true-pred,0); three raw/state channel losses before /3; summary and receipt. Local active-area threshold1e-7 is descriptive only, not a new vote. Pool growth masses by sum across16 windows; report other quantities as equal-window means. Loss magnitudes do not establish gradient dominance or a causal explanation. No re-training or P2/PINO in this diagnostic.
