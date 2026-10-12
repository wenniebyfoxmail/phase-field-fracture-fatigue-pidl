# E014 actual spatial asset admission — 2026-10-12

Verdict: ADMIT_SPATIAL_ASSETS. Independent ChatGPT review in
https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb .
This closes the actual pre-fit asset gate for prospective v2, not historical v1.

Exact bundle R002/E014_R002_spatial_with_training.zip SHA256
81aa50f0cbac409d8b2d46c0d18a35c7a84557bbea6f8b7c3222656fdd2ad89c.
Prepared NPZ aade7fd91785b777ca90492e164799f0528389ddaf9641323cd70723388af005;
metadata fac85f54ea2c3860d427052692fb5dc4016d960e5abffb08e8d2cbeb743d05c4.
Includes original stages7/8 nodemaps and stage7 connections; no held response.

Reviewer independently rebuilt IDs, xy, weights, increments and u7 exactly.
39891 common finite facets, 77840 source triangles on common training support,
646 interior observations. Source triangles clockwise; absolute source areas
are intentionally distinct from the artificial CCW FEM mesh. Mesh861/1600,
648mm2, one closed120-node contour, no holes/topology defects. Rebuilt priors
agree to floating precision. Brute-force-neighbour/QR boundary reconstruction
agrees within3.47e-18mm; fourth-neighbour max1.3114836mm, all rank3, no neighbour
selection ties. Alpha2.000455053872258 matches the stored force-gap ratio.
Actual PNG and rendered PDF inspected independently; priors and exaggeration
explicit, point counts/positions correct. Receipt binds approved source hashes.

Explicit permission: exact admitted inputs, exact source55cf55596058f5dbc97294b354a5004510a6b2a4,
GPUServer8, thread limits verified1;21q+intact; numerical checks/profile retained;
freeze predictions and receipts before separate high-response validation.
No new arms/refinement/basis changes/target-informed masks or tuning.

Limits: archive extraction/original archive identity and runtime chronology are
producer attestations; unseen held bytes not independently verified here.
Exporter compensation remains unresolved; observable is one global planar rigid
quotient, not recovery of the original transformation. Priors/artificial boundary
are conditional choices, not actual grips or measured true damage. No practical
identifiability, material/fatigue/forecast/road claim follows from admission.

Launch preflight: live GPUServer8, Python3.10.12/NumPy1.24.4/SciPy1.15.3;
OpenBLAS threadpool reported num_threads1 with all three thread env vars1.
Remote reviewed code hashes and prepared NPZ hash matched admitted bytes.
Fresh R003 root /mnt/data2/drtao/wennie/S03-E014-R003; no raw/held field input.
No real-data mechanics solve occurred on Mac. No GPU training or broad process
intervention. Computational source remains the exact reviewed Git archive.
