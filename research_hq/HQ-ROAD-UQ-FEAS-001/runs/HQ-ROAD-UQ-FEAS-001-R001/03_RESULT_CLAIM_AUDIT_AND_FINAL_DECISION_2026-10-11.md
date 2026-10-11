# HQ-ROAD-UQ-FEAS-001-R001 result claim audit and final decision

## Frozen result

| Quantity | Observed | Frozen requirement | Decision |
|---|---:|---:|---|
| CFD images with Dice > 0 | 71/118 (60.2%) | at least 89/118 | fail |
| Empty or full-foreground predictions | 47/118 | fewer than 59 | pass |
| F1 backbone gate | — | both conditions | **fail** |
| Full CFD mean error | 0.832505 | descriptive | — |
| `U_LC` risk at first 29 | 1.000000 | at least 0.05 below full risk | fail |
| `U_H` risk at first 29 | 1.000000 | at least 0.05 below full risk | fail |
| `U_Z` risk at first 29 | 0.740696 | at least 0.05 below full risk | pass by 0.091809 |
| F2 selective-ranking gate | — | any frozen score passes | **pass** |

There are 50/118 catastrophic rows with error at least 0.9. A validation mean Dice is 0.745312 at the independently selected epoch 29, while CFD mean Dice is only 0.167495. This is strong evidence of source-transfer failure for this frozen crop-trained U-Net. It is not evidence that CFD labels are physical truth or that every compatible public-data model must fail.

`U_Z` is directionally better than `U_LC`: its risk@29 is lower by 0.259304 and its AURC is 0.761430 versus 0.936788. This is a useful candidate signal, but its accepted-set error remains 0.740696 and the backbone gate failed. The result therefore cannot qualify a selective inspection system or justify opening Road420.

## Decision

Final verdict: **`FEASIBILITY_NO_GO_CURRENT_CRACK500_TO_CFD_BACKBONE`**. The registered D1 requires F1 and F2; only F2 passed. Road420 remains sealed as the future C source and was not transferred, enumerated or read. No retry, alternate seed, threshold adjustment, new model or D2 evaluation is authorised by this run.

This decision stops only the tested combination: released CRACK500 positive-rich crops, the frozen random-initialised U-Net and CFD published boundaries. It does not reject trustworthy crack identification or source-distance ranking as a research direction.

## Constructive next gate

CFD has now been consumed as a development/diagnostic source. A new experiment would be required, with no claim of confirmation on CFD. The smallest constructive route is:

1. keep Road420 sealed;
2. qualify one additional official public road-crack source with compatible boundary semantics and group identity, with CrackTree200 or GAPs384 treated only as discovery candidates until package, licence, pairing and duplication audits pass;
3. use CFD only for development of one pre-registered backbone-transfer repair, then require the same F1 non-degeneracy gate on the new B source before comparing uncertainty rankings;
4. retain `U_Z` as the sole complex candidate because it showed the frozen directional signal; do not carry entropy forward merely because it is conventional;
5. open Road420 once only after a new B passes the backbone and selective-risk gates with the checkpoint, threshold, score definitions and minimum useful difference frozen beforehand.

No scientific or operational claim extends beyond these finite public published-label queues. The run provides no physical crack truth, natural prevalence, independent road/site generalisation, crack-width accuracy, field safety or human-review benefit.
