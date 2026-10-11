# S03-E012-R001 independent evidence review

- Date: 2026-10-12 (Europe/London); surface: ChatGPT Pro.
- Conversation: https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb
- Verdict: `PASS_EVIDENCE_REVIEW`; concrete blockers: none.
- Closure: completed minimal scalar pipeline plus descriptive lower archived
  holdout MAE/RMSE for secant under the frozen retrospective recorded-gap design.

## Exact reviewed files

| Artifact | SHA-256 |
| --- | --- |
| stages.csv | afef3f65bbdc836153ab462f7a0a4a39386f736799749f3bd2f9d35b09656e97 |
| groups.json | 1b99af9267ca62a07907faf7465c09517920f1cac05dcbca295b3c7829283e8c |
| split_manifest.json | 87ad2c6040ba60cd15583adad849e7d910b0daa2e708abc3b65d5e8ad882681f |
| preparation_lock.json | 0679f0ec5501bd2e8500d1e9b8f0bb57b78a64b8936ffd4cac93d4792e2fcdf8 |
| predictions.csv | c6a2c02b01579e82a4d3c0c8c2e3b1a7437ff531bdebe2abb63a50f46eb45554 |
| metrics.json | 8c967773e3a2a7cd1d930cf838d79352f58fd44578b6297dff47c803000dc432 |
| prepare_receipt.json | 1132c7dcfc05a3a53a6a68d010f7283800511e3c6044d375c758c3cda40962cb |
| evaluation_receipt.json | 27b7d005af40c48ed6294061805d00913a5df3b2ff07f86a90800d52fd99680e |
| README_analysis.md | 228e58479a9e478a43d6c6759060671121190eda1d7dcfc651e5d7b5c1a2dfb3 |
| holdout_baselines.png | e17d03ff12bd7b85e1095817d1b638ba3dab6b954798f86263e204911f0308a7 |

The renamed receipts in review/ are byte-identical copies of the original mode
receipts. The reviewer independently verified all ten hashes, reconstructed
342 stages into 114 triplets with equal tied labels, reproduced the 66/23/23
eligible-target split and all 112 prediction/metric rows. The PNG agrees with
all 23 holdout rows, including unfavorable terminal excursions. Approximately
87.3979323% lower holdout MAE is an arithmetically correct descriptive result.

## Verification limits

The reviewer recalculated supplied prepared evidence only: no raw archive,
header/body access, original runner invocation or live Git verification.
Runtime identity, clean checkout, timing, read scope and occurrence of the local
preparation check remain producer attestations. The grouping summary was
reconstructed and matched its recorded hash, but its original file was not
provided. PDF bytes were not externally inspected; the PNG supplies reviewed
figure evidence.

Decimal precision is computational, not measurement precision. These are one
sequence's correlated target errors, not independent specimen replicates.
Growth-triggered acquisition and conditioning on realized gaps limit the result
to retrospective recorded-label evaluation. No mm calibration, physical
identification, phase-field recovery, generalisation or road validity follows.
E006's negative and E011's structural-admission verdicts remain unchanged.
