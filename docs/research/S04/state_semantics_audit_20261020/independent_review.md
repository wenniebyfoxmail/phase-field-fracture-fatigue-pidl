# Independent read-only audit review

Date: 2026-10-20. Channel: collaboration sub-agent `/root/audit_review`, separate context; reviewer did not edit files, execute audit.py, deserialize models, solve PDEs, train, or use SSH.

Reviewed audit code: a12784f4. Reviewed tables and final report: 394fc20751595f816d410402b6500d51091d6095.

Initial review required corrections: compare actual NPZ steps to JSON and physical mapping, preserve Umax/trajectory identity and `export_field` schema, distinguish committed predecessor from zero conditional commits, include c1 pre/proof/proposed/post and history idempotence checks, and distinguish saved network d from external mechanical d while including readouts. These were corrected before the single audit execution. Final report review required canonical owner/D10–D12/current-card links; corrected in394fc207. No scientific threshold or old verdict was changed.

Final reviewer finding: no remaining blocking defect for this bounded saved-state audit. Independently checked table counts143/1353/263, unique state/field keys, 260 verified checks plus two already documented semantic defects and one conditional reference. c1-related160 checks passed;20 trial-history/commit-idempotence comparisons have zero difference and finite channels2:4. Opaque H identity was not promoted to constitutive validity.

The reviewer verified source/s04_e027.py's use of target trial f, tight-coupling's distinct NN/mechanical d roles, current E011 versus historical Hard5 event families, and source owner HEAD829508617534c6c5febc813899498a31053684df with preparation cardexecution_enabled=false/run_id=null.

Allowed conclusion: listed retained indices, locked c20 sources and c1 commit chain show no newly found index or update-timing mismatch. Not covered: unretained complete histories, closed holdouts, complete training labels, physical teacher qualification, generalisation, training benefit or new solver performance.

Figure: parent inspected the rendered state_audit_decision.png. It displays saved index and commit metadata, not a new method-performance comparison. Raw source and figure reading instructions are in README_analysis.md.
