# HQ-PUBLIC-REF-001 producer amendment

Date: 2026-10-09. Before any model result was produced, the user explicitly redirected the authorised producer from Taobo to `gpu-server` (`D-26-09`). This changes only the execution platform and output-root validation. It does not change the data lock, split, model, seed, loss, checkpoint selection, evaluation set, primary comparison, budget, or stopping rule.

- Storyline: `HQ-TRUST-CRACK`; Experiment: `HQ-PUBLIC-REF-001`, protocol revision `r1-gpu-server-amendment`.
- Run: `HQ-PUBLIC-REF-001-R001`.
- Claim class: C2 published-reference segmentation diagnostic.
- Evidence-domain registry bucket: `controlled-experiment`, with an explicit qualification that these are public real-surface images and are not verified as controlled specimens, real-road observations, physical truth, or independent sites. This bucket choice is administrative and adds no scientific entitlement.
- Producer: `gpu-server`, expected hostname `D-26-09`, Windows CUDA.
- Maximum: 40 epochs or 6 GPU hours for training plus validation, followed by at most 1 GPU hour for the complete final diagnostic.
- Primary comparison: BuildCrack's fixed 355 nonempty published-reference images, `AURC(U_H)-AURC(U_LC)`; negative is descriptive only.
- Stop: data/code/environment identity failure, nonfinite output, invalid reconstruction, budget exhaustion without a valid checkpoint, or incomplete final cohort.
- Blocked conclusions: physical crack truth, fine-width accuracy, independent-site generalisation, field safety, or decision utility.

The existing reviewed snapshot is invalidated by the runner edit. A new independent code review bound to the amended snapshot is required before launch.
