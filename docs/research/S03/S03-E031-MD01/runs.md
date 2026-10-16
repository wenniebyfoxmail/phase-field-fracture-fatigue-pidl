# S03-E031-MD01 runs

All runs are Mac lightweight CPU image analysis or rendering, no training/GPU.
Archive root:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E031-MD01/`.
Every payload folder below has its own run_receipt.json with host/PID/runtime/
command/start/end/code identity. R001 andR002 launched with Python
subprocess.run(...,timeout=120,check=True); neither timed out.

| Run | Purpose | Code | Outcome |
|---|---|---|---|
| R001 |403/406history, once-refined geometry, two predictions saved before409 acquisition |b4a1c7a, clean; admitted numeric86e1fa5 unchanged|succeeded, locally verified,0.3737s|
| R002 |409background correspondence and one fixed target measurement/score |88ee144, clean; admitted numeric68fbc24 unchanged|succeeded, locally verified,0.3739s|
| R003 |first saved-output figure render |88ee144|succeeded; older display lacks complete embedded RunIDs, retained not final|
| R004 |same saved numeric outputs; final figure identity/ordinal caption |158f33a, clean|succeeded, locally verified,5.2483s; no new measurement|

Source images under`source/`, numeric outputs under`runs/S03-E031-MD01-R001/`
and`runs/S03-E031-MD01-R002/`; final figures and guide under
`runs/S03-E031-MD01-R004/analysis/`. Separate source membership and prediction
save chronology are explained in the protocol and independent review.
Compact exact receipt copies and unchanged source summary are in`evidence/`.
