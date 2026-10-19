# Claim audit — GAPS384 and backbone repair

| Claim | Evidence | Status and boundary |
|---|---|---|
| GAPS is a pavement-distress dataset acquired with a mobile mapping system; the official page describes grayscale 1920×1080 images at about 1.2 mm/pixel. | TU Ilmenau official GAPS dataset page: <https://www.tu-ilmenau.de/en/neurob/data-sets-code/gaps> | Supports road-imaging provenance and native image format. It does not map derivative GAPS384 files to individual roads/sites. |
| FPHBN supplies pixel-level crack reannotations derived from GAPs and links the dataset package used here. | Authors' repository: <https://github.com/fyangneil/pavement-crack-detection> | Supports use as published segmentation labels. The repository exposes no recognized licence, so this package is local academic research only and is not redistributed. |
| The selected encoder weights are torchvision ResNet18 ImageNet weights. | Official PyTorch weight object/documentation and file: <https://pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html>, <https://download.pytorch.org/models/resnet18-f37072fd.pth> | Local file identity is additionally fixed by SHA-256 and strict state-dict loading. |
| Local GAPS384 package has 384 pairs, 382 nonempty masks and two empty masks. | `qualification_receipt.json` plus full decode in `test_repair.py`. | Direct local inventory fact; it does not establish physical crack truth or width. |
| No high-similarity duplicate was detected against used CRACK500 and CFD images. | 3,869,184 four-rotation pHash comparisons, exact decoded-pixel hashes, receipt and `audit_public_b.py`. | Screen found zero exact matches and zero pHash Hamming ≤8. This is not proof of no semantic or scene overlap and excludes sealed Road420. |
| A pretrained encoder is the appropriate minimal repair. | D1 failure panel plus isolated design comparison. | This is a testable inference, not an established result. Only a separately authorized producer run can accept or reject it. |

The allowed conclusion remains a finite diagnostic against public published segmentation labels. No claim is permitted about physical crack truth, crack width, independent-site generalization, field safety or human-review utility.
