---
storyline_id: S03
experiment_id: S03-E004
protocol_revision: v1
status: closed
started_at: 2026-10-09
closed_at: 2026-10-09
primary_storyline: S03
claim_class: C1_evidence_validity
evidence_domain: controlled_experiment
scientific_verdict: negative
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

## Analysis execution

- Attempt: `S03-E004-A001`; read-only remote-archive and extracted-table audit.
- Code: `bb75162cc943b12ba670fc9c0a5edd70f1d56170`, clean tree at
  execution.
- The 3.0 GB archive was not downloaded. HTTP range requests read the ZIP
  directory and extracted all 33 `.txt`, `.xlsx` and `.pdf` members required
  for the audit; ZIP CRC checks passed and SHA-256 hashes were recorded.
- Evidence package:
  `$PROJECT/local_archive/experiments/S03-E004/analysis/`.
- Complete archive inventory: 415 entries, including 221 PNG, 157 JPEG, 26 TXT,
  four XLSX and three PDF files.

## Evidence result

- Three physical beams are explicit. Each beam has four fixed-camera regions
  and four moving-camera regions; moving-camera acquisition supplies three
  poses per region and load stop.
- The filtered force/displacement tables are finite, strictly time-ordered and
  sampled at 25 Hz. For all non-final fixed-camera load stops, the nearest
  nominal table match differs by at most `0.020 s`.
- The paper states that cameras and the data logger were not synchronized.
  Manual clock/start-time alignment is described, but no quantitative matching
  uncertainty is supplied.
- Beam 5 IA's final moving filenames contain `867, 870, 873 s`, while its
  workbook records `867, 890, 893 s`; neither source is presumed correct.
- Each beam's final fixed-camera time lies after the final filtered machine
  sample: Beam 4 `684 > 682.615 s`, Beam 5 `840 > 838.955 s`, and Beam 6
  `578 > 575.590 s`.
- No released per-state crack-width, crack-geometry or DIC target table was
  found in the complete archive inventory.

## Scientific verdict

`BLOCKED_D01_IDENTITY_READY`. The frozen primary criterion fails because the
camera-to-logger mapping uncertainty is unavailable, one filename/workbook
timestamp conflict is unresolved, the final states are not covered by the
filtered machine tables, and no per-state crack target is released.

This negative qualification is not a statement that D01 lacks scientific
value. D01 remains suitable for a separately preregistered current-state
measurement, registration, or fixed-versus-moving-camera repeatability study.
It is not currently admissible for transition prediction, future masks, RUL,
temporal-token validation, or road transfer.

## Review boundary

No external evidence-readiness review was requested for this conservative
qualification result. The protocol, complete remote inventory, source hashes,
table joins and decision are retained for independent review; no scientific
prediction claim is promoted from this audit.

## Next action

Ask the dataset authors for: (1) a quantitative camera/logger matching-error
bound, (2) resolution of the Beam 5 IA final timestamp discrepancy, and (3)
any per-state crack-width or DIC reference outputs. Until those answers exist,
stop the D01 prediction branch and use the release only under a new
measurement-only protocol.
