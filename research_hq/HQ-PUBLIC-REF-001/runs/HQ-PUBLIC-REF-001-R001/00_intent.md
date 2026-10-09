# HQ-PUBLIC-REF-001-R001 intent

- Storyline: `HQ-TRUST-CRACK`
- Experiment: `HQ-PUBLIC-REF-001`
- Run: `HQ-PUBLIC-REF-001-R001`
- Protocol: `r1-gpu-server-amendment`
- Producer: `gpu-server`, exact hostname `D-26-09`
- Requested device: physical GPU 0, subject to a fresh pre-launch process check
- User authorization: 2026-10-09, `授权 请执行`; producer direction: `你可以直接使用ssh gpu-server`
- Branch: `codex/hq-public-reference-launch-20261009`
- Reviewed commit: `ea44c1b4a07b7626d7f22a80943ca39d45177395`
- Reviewed runner snapshot: `e17179cba87cf2ae134b7e99d82614c6eacd49bd5c54ef17f000468e03a1347e`
- Data lock: `19f0e55ba20c8758a06f72f3b3300bd25b6821d241b01f690a75777ff3c794d8`

Purpose: execute the single frozen public-reference crack-segmentation uncertainty diagnostic. Training may use only METU train images; METU validation selects the checkpoint. METU internal test and BuildCrack remain unseen until checkpoint freeze. The primary finite-cohort comparison is `AURC(U_H)-AURC(U_LC)` on the fixed 355 BuildCrack images with nonempty published references.

Budget: at most 40 epochs or 6 GPU hours for training plus validation, followed by at most 1 GPU hour for the complete final diagnostic. Stop at the first identity, nonfinite-state, reconstruction, cohort-completeness or budget failure specified in the frozen protocol.

Expected remote output root: `C:\Users\xw436\jobs\HQ-PUBLIC-REF-001-R001`, which must not exist before launch. Required evidence includes the approval, environment, data-lock and code-identity receipt, process identity, logs, checkpoint-selection table, frozen checkpoint, exact per-image scores and risk curves, empty-reference report, group diagnostics and fixed error examples.

The admissible claim remains agreement with each dataset's published segmentation references. This run cannot establish physical crack truth, fine-width accuracy, independent-site generalisation, field safety or human-review/reacquisition utility.
