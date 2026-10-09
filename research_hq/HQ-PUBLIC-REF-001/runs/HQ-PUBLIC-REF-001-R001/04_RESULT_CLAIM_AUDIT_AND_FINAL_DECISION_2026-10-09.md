# HQ-PUBLIC-REF-001-R001 result claim audit and final decision

Date: 2026-10-09. Decision: `NO_GO_CURRENT_ENTROPY_SELECTIVE_INSPECTION_CANDIDATE` and `NO_GO_CURRENT_MODEL_FOR_BUILDCRACK_PUBLISHED_REFERENCE_TRANSFER`.

## Frozen question and observed result

The predeclared question was whether mean pixel entropy ranks published-reference segmentation error better than mean low confidence on the fixed 355-image BuildCrack nonempty-reference cohort. The primary estimand was `Delta=AURC(U_H)-AURC(U_LC)`, with `Delta<0` allowed to mean only a descriptive finite-cohort advantage.

| Cohort | n | AURC low confidence | AURC entropy | Delta |
|---|---:|---:|---:|---:|
| METU internal test | 80 | 0.1507637145 | 0.1555732639 | +0.0048095494 |
| BuildCrack nonempty reference | 355 | 0.9508191182 | 0.9497126948 | -0.0011064234 |
| BuildCrack all | 358 | 0.9346063487 | 0.9339815193 | -0.0006248294 |

The primary sign is negative, so the exact finite BuildCrack cohort has a descriptive entropy advantage. Its magnitude is only `0.0011064` AURC, about 0.116% of the low-confidence AURC. The two risk curves are visually nearly coincident. No inferential or independent-site claim was predeclared or earned.

## Claim audit

| Atomic claim | Evidence | Verdict | Allowed wording |
|---|---|---|---|
| The frozen run completed and the primary statistic is reproducible. | Successful receipt, exit code 0, 40 epochs, 438 final rows, 896/896 manifest match, independent AURC recomputation. | Supported. | The fixed run completed and reproduced `Delta=-0.0011064`. |
| Entropy beat low confidence on the fixed BuildCrack nonempty cohort. | AURC 0.9497127 versus 0.9508191. | Supported only as a descriptive finite-cohort statement. | Entropy had a very small lower AURC on this fixed cohort. |
| Entropy offers a meaningful or robust selective-inspection advantage. | Difference is 0.0011064; curves nearly overlap; no independent sampling or prespecified practical margin. | Not supported. | No reliable operational advantage was established. |
| Either uncertainty score safely ranks transferable predictions. | At both 10% and 25% accepted coverage, BuildCrack risk is 1.0 for both scores. | Contradicted for this run. | Both scores ranked completely failed cases among the lowest-uncertainty images. |
| The trained segmenter transfers adequately to BuildCrack published references. | Mean error 0.8704; median 0.9962; 164/355 nonempty cases have error exactly 1; 230/355 have error at least 0.9. Fixed highest-error examples include blank or grossly misplaced predictions. | Contradicted. | Severe published-label transfer failure was observed. |
| The model identifies physical cracks or generalises to independent sites. | BuildCrack and METU labels are published references with coarse and differing semantics; units are not verified independent sites. | Not assessed and blocked. | No physical-truth, fine-width, site-generalisation or field-safety claim is allowed. |
| The uncertainty ranking improves human review or reacquisition decisions. | No review actions, costs, human labels or prospective decision outcomes were observed. | Not assessed and blocked. | No decision-utility claim is allowed. |

## Why the candidate stops

The primary sign alone is insufficient to rescue the candidate. The practical task is selective acceptance under source shift. On BuildCrack, the lowest-uncertainty quartile has mean published-reference error 1.0 for both methods. The full nonempty cohort has median error 0.9962. Entropy therefore provides no usable protection against the dominant failure mode: highly confident external-source failure. The small negative AURC difference is a property of two nearly overlapping rankings inside an already failed transfer regime.

The internal/external contrast reinforces that interpretation. METU internal mean error is 0.1499 and neither ranking is clearly helpful; its entropy AURC is worse than low confidence by 0.00481. BuildCrack mean error rises to 0.8704. This is evidence of source-dependent published-label mismatch or model transfer failure, not evidence that entropy detects the shift.

## Final decision and next permitted action

1. Stop the current entropy-versus-low-confidence candidate for selective inspection. Do not tune its ranking threshold or present the negative primary delta as a trustworthy-inspection result.
2. Stop the current METU-trained model as a BuildCrack published-reference segmenter. Do not use its external predictions for physical or field claims.
3. Preserve BuildCrack's role for this completed experiment. Any future tuning on BuildCrack must explicitly retire it as an external diagnostic and must introduce a new untouched public external source before making another transfer claim.
4. If the broader public-data route continues, the next research object is a new, separately registered source-shift failure analysis: distinguish label-semantic mismatch, appearance shift and threshold/calibration failure using existing public data. That is a new experiment and is not authorized by this completion.
5. Field-site and expert-annotation work remains unnecessary for the present stopping decision. It becomes relevant only if a later public-data candidate first passes published-reference transfer and the thesis seeks physical-truth or decision-utility claims.

The completed run closes the currently authorized public-reference pilot. It does not close the broader thesis, but it removes this model-plus-entropy route from the qualified candidate set.
