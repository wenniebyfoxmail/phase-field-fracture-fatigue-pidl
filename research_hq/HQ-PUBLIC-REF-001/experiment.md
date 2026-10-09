# HQ-PUBLIC-REF-001 — Public-reference crack segmentation uncertainty diagnostic

- Storyline: HQ-TRUST-CRACK, trustworthy crack identification
- Protocol: r1-gpu-server-amendment
- State: ready for one authorised producer Run after exact code/data/environment preflight
- Claim class: C2 current-state segmentation against published references
- Evidence domain: controlled-experiment registry bucket; actual inputs are public real-surface images, not verified controlled specimens or real-road observations
- Unit: one original published image; candidate groups are leakage constraints, not independent sites
- Allowed inputs: METU train images only for fitting; METU validation only for checkpoint choice; METU internal test and all BuildCrack only after checkpoint freeze
- Target: each source's unchanged published segmentation reference
- Question: on the fixed BuildCrack nonempty-reference cohort, does mean pixel entropy rank published-reference segmentation error better than mean low confidence?
- Primary estimand: `Delta=AURC(U_H)-AURC(U_LC)` on 355 BuildCrack nonempty-reference images
- Comparator: mean low confidence on the same probabilities and pixels
- Interpretation: `Delta>=0` is negative for the entropy-ranking claim; `Delta<0` is a descriptive finite-cohort advantage only
- Validity gates: exact reviewed code snapshot, verified 816-row data lock, complete cohort, finite original-resolution reconstructions, no external-source fitting or selection
- Stop rule: first validity failure, nonfinite state, no fully validated checkpoint by 40 epochs/6 GPU hours, or incomplete final evaluation within 1 further GPU hour
- Minimum evidence: receipt, checkpoint-selection table, exact score/curve tables, same-unit risk curves, empty-reference report, group diagnostics, fixed highest-error examples
- Blocked conclusions: physical crack truth, fine width, independent-site generalisation, field safety, human-review/reacquisition utility
- Producer: gpu-server / D-26-09
- Run: HQ-PUBLIC-REF-001-R001

The underlying references have known semantic coarseness. This is part of the declared estimand and must not be used after results to discard a negative result.
