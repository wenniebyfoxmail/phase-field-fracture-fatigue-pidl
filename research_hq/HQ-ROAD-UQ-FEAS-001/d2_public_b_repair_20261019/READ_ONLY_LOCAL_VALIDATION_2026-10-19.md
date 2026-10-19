# Read-only local validation — 2026-10-19

No optimizer, backward pass, training, producer process or Road420 access occurred.

Passed checks:

- official ResNet18 weights strictly load with SHA-256 `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec`;
- even and odd synthetic image sizes return same-size one-channel logits and 512-dimensional encoder features;
- logits and features are finite;
- GAPS384 decodes as 384 matched 1080×1920 pairs with 382 nonempty masks;
- F1/F2 threshold arithmetic resolves to 287 Dice-positive images, fewer than 191 degenerate predictions, and 95 accepted images;
- Python compilation and runner help/import succeed without a producer launch.

Command:

```text
python test_repair.py --weights /Users/wenxiaofang/Downloads/resnet18-f37072fd.pth --gapszip /Users/wenxiaofang/Downloads/GAPS384_FPHBN_official_20261019/GAPs384_raw_img_gt.zip
```

Result: `PASS`; training or optimizer steps: `0`; Road420 access: `false`.
