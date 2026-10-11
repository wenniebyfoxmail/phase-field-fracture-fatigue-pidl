---
storyline_id: S03
experiment_id: S03-E009
protocol_revision: acquisition-v1
status: dataset_audit
started_at: 2026-10-11
primary_storyline: S03
---

# Moving IB ruler reference characterization and selective-measurement design

## Question before code

What camera geometry and explicitly numbered mm references are present in the
released moving IB ruler images, and which simple measurement protocol can they
support? This first stage is data acquisition/characterization, not a method
validation or formal accuracy result.

S03-E008 identified a repair for a fixed-camera crop failure. The fixed six
images are development data. The fixed detector assumes a horizontal ruler,
15--19 px observed spacing and a near-bottom image location; these assumptions
must be checked against moving images before designing a transfer algorithm.

Independent units: three beams, not four independent moving photographs.
Domain: controlled experiment. No future prediction origin/horizon applies.

## Locked acquisition selection

Before new pixel access, select exactly:

- Beam 4/G4-IB-Free/1-G4-IB_ref.png
- Beam 5/G5-IB-Free/1-G5-IB_ref.png
- Beam 6/G6-IB-Free/1-G6-IB_ref.png

Use the existing S03-E004 released-v4 remote ZIP manifest and reuse its range
extractor. Verify uncompressed size, manifest CRC, successful decoding and
dimensions. Record provenance and retrieval. No image-dependent exclusion.
Budget: three files, approximately 29 MB uncompressed, once; no full ZIP.

Reserve Beam 6/G6-IB-Free/1-G6-IB_ref2.png without retrieval or pixel access.
This is only a fresh observation of one known beam. It can support a bounded
camera/observation test, not independent-specimen generalisation.

## Dataset-first decisions

Inspect all three selected references for ruler orientation, metric spacing,
legible numbered marks, occlusion and camera differences. Document native image
coordinates. Design an annotation protocol in which physical mark identity
is assigned independently of the detector and checked in a separate pass.

A selective-measurement contract must report error and positive coverage
together: accepting no samples must not pass a safety criterion. Set the
threshold only after reference repeatability and attainable precision are known.
An observed zero-error count on one reserved photograph is not a population
safety-rate guarantee. Avoid using detector-derived LOMO as external ground truth.

Outcomes: reference visible -> prepare explicit mark-reference measurement;
reference ambiguous -> human review/alternative band; absent -> no metric report.
Stop after acquisition and characterization, before detector fitting or new
pixel-based tuning. A claim-bearing runner requires an independently reviewed
protocol and exact code.

## Records

Owner: S03-E009; clean S03 task branch codex/crackmnist-tokenizer-mvp,
base ecbeb64. Scope: acquisition script, this record, reference design and compact
receipts. S03-E007 and S03-E008 are inputs, not modified designs.
Run: S03-E009-R001, acquisition only on Mac-PIDL.
Archive: local_archive/experiments/S03-E009/runs/S03-E009-R001/.
Minimum evidence: provenance, sizes/CRC/decode, all-three contact sheet,
data-characteristics report and next-protocol draft. No formal scientific PASS.
