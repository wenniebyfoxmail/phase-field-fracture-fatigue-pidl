# S01-E001 execution runbook

The commands below are a prepared plan, not evidence that a run happened.
Training stays blocked until the independent v11 code review passes.

Use the isolated producer runtime explicitly:

```powershell
$python = "C:\Users\xw436\pavetrack_env\Scripts\python.exe"
$run = "C:\Users\xw436\pavetrack_runs\S01-E001-R008"
```

The official initial weights were downloaded before training and frozen in
`run_config.json`. Auto-downloads are not accepted as claim-bearing inputs.

## 1. Development data only

Prepare train and validation together. The command must not include `test`.

```powershell
& $python scripts/pavetrack_cv/prepare_dataset.py `
  --workbook data/Dataset_PDdescription.xlsx `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --config docs/research/S01/S01-E001/run_config.json `
  --image-root data/pilot_images `
  --image-root data/scaleup_images `
  --output prepared/development `
  --splits train validation `
  --mode copy
```

## 2. Fit proposer and mine development crops

```powershell
& $python scripts/pavetrack_cv/train_proposer.py `
  --dataset prepared/development/dataset_train_validation.yaml `
  --development-manifest prepared/development/manifest_train_validation.json `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --output $run `
  --device 1 `
  --weights artifacts/yolo11n.pt `
  --config docs/research/S01/S01-E001/run_config.json

& $python scripts/pavetrack_cv/mine_crops.py `
  --manifest prepared/development/manifest_train_validation.json `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --proposer "$run/proposer/weights/best.pt" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --config docs/research/S01/S01-E001/run_config.json `
  --output "$run/crops" `
  --split train `
  --device 1

& $python scripts/pavetrack_cv/mine_crops.py `
  --manifest prepared/development/manifest_train_validation.json `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --proposer "$run/proposer/weights/best.pt" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --config docs/research/S01/S01-E001/run_config.json `
  --output "$run/crops" `
  --split validation `
  --device 1

& $python scripts/pavetrack_cv/train_reranker.py `
  --crops "$run/crops" `
  --train-crop-manifest "$run/crops/crop_manifest_train.json" `
  --validation-crop-manifest "$run/crops/crop_manifest_validation.json" `
  --development-manifest prepared/development/manifest_train_validation.json `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --pretrained-state-dict artifacts/mobilenet_v3_small_imagenet.pth `
  --config docs/research/S01/S01-E001/run_config.json `
  --output "$run/reranker" `
  --device cuda:1
```

## 3. Validation and model freeze

```powershell
& $python scripts/pavetrack_cv/evaluate_two_stage.py `
  --manifest prepared/development/manifest_train_validation.json `
  --proposer "$run/proposer/weights/best.pt" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --reranker "$run/reranker/best_reranker.pt" `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --config docs/research/S01/S01-E001/run_config.json `
  --output "$run/evaluation" `
  --split validation

& $python scripts/pavetrack_cv/freeze_for_test.py `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --config docs/research/S01/S01-E001/run_config.json `
  --proposer "$run/proposer/weights/best.pt" `
  --reranker "$run/reranker/best_reranker.pt" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --validation-evaluation "$run/evaluation/evaluation_validation.json" `
  --output "$run/test_authorization.json"
```

The evaluator filters this development manifest to validation records and
refuses any manifest containing a test record.

## 4. Single confirmatory access

Only after Step 3 has written the model-bound authorization may the test images
be downloaded and prepared.

```powershell
& $python scripts/pavetrack_cv/prepare_dataset.py `
  --workbook data/Dataset_PDdescription.xlsx `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --config docs/research/S01/S01-E001/run_config.json `
  --image-root data/confirmatory_images `
  --output prepared/confirmatory `
  --splits test `
  --test-authorization "$run/test_authorization.json" `
  --proposer "$run/proposer/weights/best.pt" `
  --reranker "$run/reranker/best_reranker.pt" `
  --validation-evaluation "$run/evaluation/evaluation_validation.json" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --mode copy

& $python scripts/pavetrack_cv/evaluate_two_stage.py `
  --manifest prepared/confirmatory/manifest_test.json `
  --proposer "$run/proposer/weights/best.pt" `
  --reranker "$run/reranker/best_reranker.pt" `
  --proposer-receipt "$run/proposer_receipt.json" `
  --data-lock docs/research/S01/S01-E001/data_lock.json `
  --config docs/research/S01/S01-E001/run_config.json `
  --output "$run/evaluation" `
  --split test `
  --validation-evaluation "$run/evaluation/evaluation_validation.json" `
  --test-authorization "$run/test_authorization.json"
```

Stop after this comparison. Do not tune on the returned test result. Run SAM2
only in a new preregistered experiment if the primary delta is at least +0.10.
