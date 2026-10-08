# S01-E001 producer preflight — 2026-10-08

Status: environment ready; training not started.

## Producer

- Alias / hostname: `gpu-server` / `D-26-09`
- Planned device: GPU 1, NVIDIA RTX PRO 6000 Blackwell Max-Q
- Check at preflight: 1,149 MiB / 97,887 MiB, 0% utilisation
- GPU 0 was active and is out of scope. No process was interrupted.
- Taobo was unreachable at the earlier connection check, so no job was routed
  there.

## Isolated runtime

- Python: `C:\Users\xw436\pavetrack_env\Scripts\python.exe`
- Python base: 3.12.14
- PyTorch: 2.11.0+cu128
- CUDA runtime reported by PyTorch: 12.8
- `torch.cuda.is_available()`: true
- visible CUDA devices: 2
- torchvision: 0.26.0+cu128
- Ultralytics: 8.3.205
- pandas: 2.3.3
- openpyxl: 3.1.5

This setup changed only the isolated `pavetrack_env`. Import and CUDA discovery
were checked. No training, inference, data transfer, or confirmatory image
access occurred during this preflight.

The hash-bound code packet was staged at
`C:\Users\xw436\pavetrack_stage\S01-E001-v1`. The producer runtime passed
`compileall` and all 13 lightweight unit tests. No dataset was transferred and
no model was instantiated by that check.
The producer also recomputed all 15 hashes in `code_review_bundle.json`; there
were zero mismatches.

## Remaining launch gates

1. selected train/validation downloads complete and pass the workbook audit;
2. independent code review is bound to `code_review_bundle.json` and passes;
3. GPU 1 is rechecked immediately before launch;
4. a fresh Run receipt records PID, command, code hashes, data hashes and log.
