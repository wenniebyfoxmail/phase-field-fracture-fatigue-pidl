# S04-E013 coverage decision

Status: asset audit complete; proposed contract awaits independent design review; training is blocked.

The FEM side is ready for the native-fidelity matrix: S04-E010 contains c20/c60/c82/c83 at s2/s4/s5 with qualified state identity and the correct accepted prior. The PIDL side is not ready. The current native-Q4 production compact package contains c76/c82/c83 peak fields and event-near states, but it has no early c20, middle c60, s2/s5 matrix, or nodal displacement export. Late-state success or failure cannot fill those missing rows.

The strict UV route is also incomplete for the newly required early–middle–late set. Qualified conditional UV-derived fields exist for c20, c82, and c83, while c60 is missing. This must be closed before comparing supervised and unsupervised recovery across time.

The proposed algorithmic sequence is therefore:

1. close c60 strict-reference and paired control-export gaps;
2. run a supervised displacement capacity ceiling on the admitted fixed-damage states;
3. run the same architecture and evaluation under an unsupervised fixed-damage UV objective;
4. only then run a free trajectory against the 12-state native-fidelity matrix.

This order identifies the first failed capability and prevents large late-stage differences from obscuring early-state failure. It also preserves the S04-E012 boundary: the UV-derived reference is not a damage/history teacher and cannot support full FEM reproduction by itself.


## Independent design review disposition

The review bound to commit `4c9291031a26e2ec04d057c43e4c9f7498aff091` returned `NO-GO`. It accepted the two-axis structure and the c20/c60/c82/c83 x s2/s4/s5 scope, but required executable information-separation, null/support metrics, field-wise paired promotion, event/export semantics, and distinct Stage 0 readiness states. Those rules are now instantiated in the amended contract. Preparatory c60-reference and exporter implementation is allowed; Stage 0 closure and candidate training remain blocked pending independent re-review and actual asset closure.
