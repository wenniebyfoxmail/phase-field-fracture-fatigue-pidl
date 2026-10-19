# Constrained variational FEM–neural hybrid design

Owner goal: improve PIDL/FEM field agreement through a coherent method redesign. User2026-10-19 explicitly selected constrained incremental variational + FEM–neural hybrid, with design/review only.

- `design_v1.md`: frozen full specification supplied to independent read-only Codex review; includes explicit stronger nodal feasible set, model/state semantics, NN and numerical roles, full-step algorithm, fresh coupled acceptance, transaction, labels, same-problem baselines and complete cost accounting.
- `review_request.json`: exact artifact hash and permitted review scope. Review does not grant Code Ready or execution.
- `review_v1.json` / `review_v1.md`: independent design review passed, no decisive blocker or v2 required; bound to the exact v1 SHA256. This does not establish Code Ready, numerical quality or acceleration. Any revised design will preserve v1 and carry a focused follow-up receipt.

No production source modified; no model/closed array access, SSH, training, GPU or FEM work performed for this design. The full implementation and subsequent decision-scale comparison remain future work; no speedup, numerical improvement or teacher qualification is claimed.

Decision: the complete framework is ready to guide future implementation preparation. The current user-authorized design/review task is complete; no runner or execution is delivered. [Implementation checklist and scope](decision.md).
