# Independent E014 review — round1, 2026-10-12

Reviewer: external ChatGPT, conversation
https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb . Submitted snapshot:
9629f31e6ac7d12cd9ce5f9d51194dda34f672a1. Four attachment SHA256 values independently matched:
runner8006848ce9a675873b098c542660514fb858abc77ec8da60a5cdd6630ae97236;
tests bda82d9ec0fdbf3749d4aea515238ca16312179a4f39e4ddb9057138eb4cb5ed;
protocol66e98f7fc749e31ac6d4205b77a78c40bf141afa8fda9742b4967d45f9aff7c2;
inspection67ec2bff475fefae1093068d840dec009e336eecf2c212f2ba30a721d9d3cf46.

Final verdict: `REVISE_CODE` for structural inspection; `NOT_READY` for physics.
This is a faithful summary, not the full verbatim review. Git membership, raw
archive contents, actual execution and exploratory measurements are attested.
Reviewer independently tested six unittest cases and synthetic integration;
no real archive, fit or held response was accessed.

## Concrete blockers and software repairs awaiting new review

1. A2869-byte wrong.partial ZIP and a duplicate selected stage7 member returned
   reports without enforcing the locked identity. Repair: enforce size/MD5
   before member access, exactly one selected name, explicit identity result;
   add identity/digest/duplicate full-inspection regressions.
2. Reference timestamp29.10.2021 14:22 became22. Repair: preserve full payload,
   strip only exact supported value_element tag; tagged/ordinary timestamp tests.

Additional improvements: finite fit support must include necessary training
displacement components; verify current/reference IDs, cycle equality and
finite ordered loads. Our separate primary-source discovery corrects
connection indexing to c+1 (node0 is valid). Changed code needs re-review.

## Physics repair direction, not launch authorization

A fixed global weighted2D rigid projector can define increments modulo
translation/infinitesimal in-plane rotation without recovering the exporter
convention. This changes the raw estimand and needs a prospective amendment.
Use identical operator/support/area weights for candidate, intact and secant;
no separate crack-side projections. Freeze geometry, weights, missingness and
rank failure. Independent stage-wise synthetic rigid additions must leave
the objective profile/held quotient error invariant; non-rigid perturbations
remain detectable. Finite3D rotation, affine scale/shear, plasticity and changing
frames are NOT removed.

Fixed-state linear response at high load is a scaled training-increment solve:
the diagnostic tests proportional-boundary extrapolation and spatial
reconstruction, not a new load direction or unique true damage. q profile and
sensitivity remain necessary; a unique grid minimum is not physical recovery.

Fix nu0.30 before fitting; no target selection between0.30/0.33. Keep E1. The
reviewer retrieved the main paper but not original supplement bytes, so
72GPa/0.30/unloaded-reference statements were then producer source attestations.
Provide original supplement/page attribution for independent verification.

Remaining gates: frozen reviewed mesh/ROI/closed BC/d0/b/width/interpolation;
fit/scoring support, area-weighted vector error, target missingness and q
selection/ties; actual mechanics runner and synthetic patch, uniform-E, load
homogeneity, rigid invariance, localized-q, missingness and leakage tests.
q0 means d=d0, NOT intact when d0 is nonzero; define d identically0 comparator
separately on the same domain. No mechanics code or spatial assets were supplied
or cleared in round1. Research disposition: repair; holdout remains unscored.
