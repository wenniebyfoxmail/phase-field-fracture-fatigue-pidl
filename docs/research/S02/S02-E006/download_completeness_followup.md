# Mendeley / PHM2019 download completeness follow-up

2026-10-17. Owner S02-E006, C1 source inventory only. New user request authorizes searching for additional existing optical labels and checking download scope, with an English email draft only. No training, fitting, model execution, performance scoring or outgoing communication. Reuse clean branch codex/history-information-audit-20261013 at base 7a91636cb18faa2aab87f90ae10601ebc22be82d; edits confined to this Experiment and its existing Obsidian note. Earlier E005 negative results remain unchanged.

## Correction to the preceding audit

The previous four-ID/five-window PHM result covered the corrected T1–T6 training ZIP and its specified sampling-window rule. It did not cover all public PHM2019 optical measurements. We omitted the post-competition T7/T8 measured labels. That source-completeness conclusion was too broad and is superseded here; the original training-package arithmetic is retained.

The user's “Manning 雷” is interpreted as Mendeley from context; MnROAD's earlier zero-target explanation remains limited to the fixed six-CELL shortlist, not all road data.

## What was and is downloaded

| Source | Previous acquisition | Current state / limits |
|---|---|---|
| Mendeley dywwnjv22h v1, file 1 | CRC-checked RAR Quick Open member headers (17,925 CSV / 19 folder groups) plus six selected, CRC-checked CSV payloads | Full 5,814,691,113-byte CSV RAR is not present in the task archive or Downloads; its full payloads have not been audited |
| Mendeley file 2 | Published file metadata only | 1,484,643,198-byte interpolated PT archive not acquired or deserialized |
| Mendeley file 3 | Published file metadata only | 1,303,694,078-byte trained-model ZIP not acquired or executed; it is not additional measured labels |
| Mendeley file 4 | Complete 43,064-byte Cycles vs Crack Length.xlsx, published identity checked | Four sheets / 156 published ground-truth rows / two label codes; sheet-to-physical-specimen relation unresolved. No missing workbook pages were inferred |
| Mendeley file 5 | Complete 633-byte README previously read and retained in earlier raw archive | Naming/index explanation, not more labels |
| PHM2019 corrected-T6 training v2 | Complete 1,005,994-byte ZIP, 142 members, CRC pass | Six Description tables / 38 optical rows. Remains the previous training source |
| PHM official NASA mirror, newly acquired | Not previously acquired | Complete 1,800,625-byte outer ZIP / 2 entries; nested PHMDC2019_Data.zip 1,887,795 bytes / 419 entries; both ZIP CRC passes. Contains T1–T8, loading files, waveforms and ReadMe.docx. This is a complete copy of this public archive, not proof that every existing laboratory record/version is public |

Mendeley metadata `status: COMPLETED` describes the publisher's file record, not the state of our local downloads. A header manifest is not a full CSV dataset. Extra displacement/PT bytes cannot be counted as additional independent measured crack-length labels. Official wording still says 19 DIC specimens and four labelled specimens; the actual four sheets repeat two codes, awaiting the author's explanation.

No bulk Mendeley download was necessary to answer whether the released crack-length workbook was complete. Full displacement acquisition may support a later, separately specified measurement/annotation task, but cannot silently create labelled ground truth.

## Additional PHM optical measurements actually found

Official moderator kjd02002 posted measured T7/T8 lengths on 17 August 2019, post 770. Its eight T7 and ten T8 values exactly match the newly downloaded NASA mirror Description tables. Page 2 of the thread was checked and contains no revised label table. The mirror has **56 optical rows across eight described specimens**. This is 18 more public rows than the previous training-only inventory, not 18 extra independent specimens.

T1–T6 optical cycle/length values in the mirror exactly match the prior corrected training ZIP. It does not add denser T1–T6 optical labels or resolve T4's 7054 versus waveform-folder 67054 discrepancy, or T3's missing optical label at 55391. T4 remains quarantined; no number is repaired. T1–T7 are described as constant-amplitude, T8 as variable-amplitude; loading regimes must remain separate. Repeated waveform acquisition does not establish repeated optical measurement uncertainty.

The ReadMe's illustrative T1 table uses a 0-cycle/0-length first row, whereas the actual Description_T1 table starts at 50000/0. Preserve that discrepancy as a baseline/index-definition question; do not add the illustrative zero as an extra measured optical observation.

Complete published optical inventory and direct crosschecks:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/phm_mendeley_completeness_20261017/optical_records_T1_T8.csv`

The same directory contains raw official HTML, both mirror ZIP layers, NASA_description_inventory.json, optical_crosscheck.json, NASA_inner_members.json, NASA_Read_Me_extracted.txt and retrieval_receipt.json. The latter preserves failed NASA legacy and stage-5 routes, followed by successful retrieval through the official mirror. AppleDouble `__MACOSX/._*` entries are metadata, not additional workbooks/specimens.

## Does this supplement the proposed validation?

Yes, it adds two described physical specimens with direct optical labels. It does not automatically establish an adequate forecasting study. The original five-window manifest and unexecuted design remain unchanged. For a separately identified coverage check using the same rule (two preceding optical measurements; origin plus a direct target 4,500–5,500 cycles later, closest to +5,000, tie earlier), the new source appears to add:

| Specimen | Earlier measurements | Origin → target | Gap | Interpretation |
|---|---|---|---:|---|
| T7 | 36001, 40167 | 44054 → 49026 | 4972 | One additional constant-load candidate window |
| T8 | 40000, 50000 | 70000 → 74883 | 4883 | One variable-load candidate window; not pooled as constant-load replication |

Independently verified source-capacity totals: constant-load five eligible IDs / six windows, with T4 quarantined and T2 lacking a window. T8 contributes a separate one-window variable-load candidate. Neither implies six or seven independent test windows; windows within a specimen remain dependent. Exact 1,000-cycle four-state coverage remains absent. No horizon expansion, label interpolation or prediction scoring is conducted.

The raw record shortage is partly a previous acquisition omission and partly genuinely sparse labels in the released files. After adding T7/T8, substantial uncertainty remains about physical lineage, optical measurement definition/repeatability, sampling policy and a useful forecast target with enough direct observations. These publicly inspected labels are development-exposed now; T7/T8 cannot be called untouched confirmation holdouts for this project. No training authorization follows.

Next smallest action: request any additional already-measured optical cycle–length tables, existing sampling/metrology notes, and clarification of the two index/label gaps. If none exist, redesign acquisition or declare a different scientifically useful target with new review; do not loosen the old band to obtain more windows.

## Official sources

- Mendeley dataset version 1: https://data.mendeley.com/datasets/dywwnjv22h/1
- PHM challenge and corrected training download: https://data.phmsociety.org/2019datachallenge/
- T7/T8 measured labels, moderator post 770: https://data.phmsociety.org/phmdata-forums/topic/ground-truth-crack-lengths-of-validation-specimens/#post-770
- Subsequent thread page: https://data.phmsociety.org/phmdata-forums/topic/ground-truth-crack-lengths-of-validation-specimens/page/2/
- PHM official NASA mirror, dataset 18: https://data.phmsociety.org/nasa/
- Archive linked by that mirror: https://phm-datasets.s3.amazonaws.com/NASA/18.+Fatigue+Crack+Growth+in+Aluminum+Lap+Joint.zip
- Original T6 release correction: https://data.phmsociety.org/phmdata-forums/topic/question-on-validation-data/
- Data authors and publication provenance: https://data.nasa.gov/dataset/fatigue-crack-growth-in-aluminum-lap-joint
- Current author contact: https://labs.engineering.asu.edu/paralab/people/ (Yongming.Liu@asu.edu)

## Draft communication

See phm_author_email_draft.md. No email client draft, send, form submission, attachment or new experimental commitment was made. No suitable user-authored email references were available through the connected sources used here; the draft was reviewed for plain professional wording without claiming an exact style match.

Independent Codex reviewer /root/sensitivity_protocol_review returned C1_SOURCE_COMPLETENESS_REVIEW_PASS after directly checking both ZIP layers, all eight optical tables, the full exported56-row CSV, moderator post770, both added windows and the Mendeley local acquisition scope. This confirms source reconciliation, not training readiness, measurement qualification or prediction benefit.
