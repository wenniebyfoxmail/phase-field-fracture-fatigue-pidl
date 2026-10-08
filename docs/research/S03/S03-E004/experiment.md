---
storyline_id: S03
experiment_id: S03-E004
protocol_revision: v1
status: prepared
started_at: 2026-10-09
primary_storyline: S03
claim_class: C1_evidence_validity
evidence_domain: controlled_experiment
---

# D01 trajectory-data qualification audit

## Road-Fracture Experiment Gate

- **Question:** does D01 provide an auditable specimen-time/load-observation
  identity chain that can support a later no-training future-signal diagnostic?
- **Claim class / domain:** C1 evidence-validity / controlled experiment.
- **Independent unit:** reinforced-concrete beam (`Beam 4`, `Beam 5`, `Beam 6`).
  Camera sides and repeated images are views or states, not independent beams.
- **Allowed evidence:** Mendeley Data release `z3yc9z84tk`, its versioned remote
  archive, the accompanying Data in Brief paper, and file-internal metadata.
- **Forbidden inference:** no model training, no fabricated synchronization, no
  patch/frame random split, and no future/RUL/road-transfer claim.
- **Cheapest decisive test:** inspect the remote ZIP central directory without
  downloading the 3.0 GB archive, then range-extract only the small test tables,
  text records, readmes and reference PDFs needed to audit identity and timing.

## Frozen primary criterion

Return `PASS_D01_IDENTITY_READY` only if, for all three beams, the inspected
sources support a non-guessed record of:

```text
(beam ID, camera/view ID, ordered observation label,
 linked test time/load/displacement or a quantitative mapping-uncertainty bound)
```

and the mapping uncertainty is explicitly available for deciding whether later
crack change exceeds acquisition/matching uncertainty.

If any required element is absent or can be recovered only by assumption,
return `BLOCKED_D01_IDENTITY_READY`. A block for transition work may still leave
D01 usable for current-state measurement or registration research.

## Necessary validity checks

1. Record the exact current dataset version, DOI, licence, remote archive byte
   size, ETag/checksum evidence, and complete ZIP entry inventory.
2. Confirm the three physical beam identities and enumerate camera/view series
   and observation labels without treating views as independent specimens.
3. Inspect all provided test spreadsheets and text tables for headers, units,
   monotonicity, missing values, duplicates, and links to image labels.
4. Inspect the paper for acquisition timing, fixed/moving-camera protocol,
   synchronization method, spatial scale, references and stated limitations.
5. Preserve unknown fields as unknown. Do not infer a time/load join from
   similar numbers alone.

## Stop rule

Stop the transition-prediction qualification as soon as the camera-to-test-data
join lacks a documented key or quantitative uncertainty bound. Do not download
the full image archive or add modelling to repair missing identity semantics.

## Minimum evidence

- versioned source receipt and full remote entry manifest;
- extracted-small-file hashes and workbook/text schema audit;
- beam/view/observation inventory;
- paper-based acquisition and synchronization evidence;
- `decision.md` with one bounded verdict and next action.

## Blocked conclusions

Passing this audit would only permit a later no-training test of whether future
change exceeds repeatability and simple persistence/recent-growth baselines.
It would not establish prediction skill, lifetime prediction, field validity,
multimodal-token sufficiency, or road transfer.

## Decision before inspection

`READY_FOR_READ_ONLY_AUDIT`. No producer run or training is authorized.
