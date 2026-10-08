# S04-E013 coverage decision

Status: amended contract frozen; c60 UV and paired-control assets retrieved and locally verified pending evidence review; training is blocked.

The FEM side is ready for the native-fidelity matrix: S04-E010 contains c20/c60/c82/c83 at s2/s4/s5 with qualified state identity and the correct accepted prior. The PIDL side is not ready. The current native-Q4 production compact package contains c76/c82/c83 peak fields and event-near states, but it has no early c20, middle c60, s2/s5 matrix, or nodal displacement export. Late-state success or failure cannot fill those missing rows.

The strict UV route now has a produced c60 result in addition to c20, c82, and c83. The c60 run passed its frozen UV gate but is not admitted until independent evidence review. The paired eta-zero control export remains missing, so Stage 0 is not closed.

The proposed algorithmic sequence is therefore:

1. close c60 strict-reference and paired control-export gaps;
2. run a supervised displacement capacity ceiling on the admitted fixed-damage states;
3. run the same architecture and evaluation under an unsupervised fixed-damage UV objective;
4. only then run a free trajectory against the 12-state native-fidelity matrix.

This order identifies the first failed capability and prevents large late-stage differences from obscuring early-state failure. It also preserves the S04-E012 boundary: the UV-derived reference is not a damage/history teacher and cannot support full FEM reproduction by itself.


## Independent design review disposition

The review bound to commit `4c9291031a26e2ec04d057c43e4c9f7498aff091` returned `NO-GO`. It accepted the two-axis structure and the c20/c60/c82/c83 x s2/s4/s5 scope, but required executable information-separation, null/support metrics, field-wise paired promotion, event/export semantics, and distinct Stage 0 readiness states. Those rules are now instantiated in the amended contract. Preparatory c60-reference and exporter implementation is allowed; Stage 0 closure and candidate training remain blocked pending independent re-review and actual asset closure.

## Stage 0 implementation update

The first c60 attempt (`S04-E013-R001-c60-uv`) failed in the PowerShell launcher before producing a summary. The launcher-only retry (`S04-E013-R002-c60-uv`, Condor `82.0`) completed with exit code 0. It reduced `rho_u` from `1.2857766593003994` to `4.816938699465251e-11`, with displacement mass RMS / `Us = 6.872576107117729e-4` and native-Q4 strain relative L2 `4.748005459472791e-3`. All retrieved arrays are finite; locked input identities, fixed-state invariants, zero training/damage/history updates, and weak-gradient agreement passed. Damage was not solved and its diagnostic did not improve, so this result supports only a conditional c60 UV reference and retains `full_teacher=NOT_QUALIFIED`.

The first combined Code Ready review found no c60-producer blocker but returned `NO-GO` for the paired exporter because accepted-state lineage and step-424 first-event/confirmation evidence were incomplete. Commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d` fail-closed binds the exact aaf13fd settings, mesh, source snapshot, log and save order; hashes model/current/prior files; and independently rechecks steps 423--427 against the production detector. The renewed exact-commit review returned `Code Ready PASS` with no blocking corrections. Taobo run `S04-E013-R003-paired-export` produced all 13 rows; remote and post-retrieval local verification agree on hashes, finite arrays, zero model/checkpoint damage mismatch and event metadata. Evidence review still must close before asset admission. Candidate training remains blocked until both c60 and paired-control evidence reviews close.
