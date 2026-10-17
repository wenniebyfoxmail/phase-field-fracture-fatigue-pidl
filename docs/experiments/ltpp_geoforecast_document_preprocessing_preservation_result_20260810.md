# LTPP document-preprocessing crack-preservation result

Status: `PREPROCESSING_PRESERVATION_FAIL__NO_TRAINING`  
Date: 2026-08-10  
Fit performed: `false`

## Decision question

Can the existing deterministic B0 `static_line_mask` be used as hard-removal
preprocessing before training a new recognizer, without erasing frozen
adjudicated crack targets?

## Predeclared gate

- pooled adjudicated crack-target retention at least `0.98`;
- every map with nonzero adjudicated crack target retains at least `0.95`;
- zero-crack maps are specificity controls and do not enter the retention
  denominator.

The gate is deliberately recall-protective: preprocessing is not allowed to
create contradictory examples in which the frozen target says “crack” after
the corresponding input stroke has been removed.

## Result

The proposed hard-removal preprocessing failed decisively:

- pooled retention: `0.690586` (`778,817 / 1,127,763` target pixels retained);
- pooled target pixels erased: `348,946` (`30.94%`);
- maps below the per-map floor: `28`;
- `P020`: `5.91%` retained;
- `P008`: `40.99%` retained;
- `P009`: `45.23%` retained;
- `P002`: zero-crack control; the rule removes `87.64%` of observed ink, but
  this does not rescue the crack-retention failure on positive maps.

The visual audit shows why: long horizontal or vertical cracks share the same
low-level geometry as the printed grid and traced boundaries. A rule that
deletes line-like structure cannot reliably distinguish those objects before
recognition.

## Decision

Do not use hard white removal from `static_line_mask` as training
preprocessing. Do not train the amendment challenger with this input. The
adjudicated crack target remains valid; the failed object is the proposed
input transformation.

The next safe candidate is a non-destructive document cue: preserve the raw
grayscale scan and, if retained after amendment review, provide the fixed
static-document mask as an additional input channel or attention cue. It must
never delete pixels. That architecture and the zero-crack specificity
sentinel must be frozen before one challenger fit.

## Reproducibility

- script: `scripts/ltpp_audit_document_preprocessing_preservation.py`
- script SHA-256: `2415a942bd15aaa9644263dc7d4b8a838c28fe8e4d6dfa7efc026065be919c15`
- receipt: `local_archive/real_road_acquisition/ltpp_geoforecast_document_preprocessing_audit_v1_20260810/preprocessing_preservation_receipt.json`
- receipt SHA-256: `7bf4ef74e9d9c6fc7bc60a5b2f1c0700c9d722c7b380faa77171fec7801f9682`
- figure: `local_archive/real_road_acquisition/ltpp_geoforecast_document_preprocessing_audit_v1_20260810/document_preprocessing_preservation_audit.png`
- figure SHA-256: `b0e34f4366717e0bceacfccf0861964be7856a20e8ed0f0e2074ea6fca72ee65`

Claim boundary: this is a no-fit audit of current-map input preprocessing. It
does not evaluate a recognizer, registration method, or future crack forecast.
