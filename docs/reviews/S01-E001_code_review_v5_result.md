# S01-E001 independent code review v5

- Verdict: **FAIL**
- Bound protocol: `S01-E001-v5`
- Bound bundle SHA-256: `7b5c3bb7a3c98691fe5ce3b783001810cd23088f5dcf77b3a0e6f9616b8ef814`
- Bound repository base commit: `dd738f177b5dbcced537a29497b4df3c38608a66`
- Hash verification: all 16 bound files and the workbook matched.
- Static tests: 27 passed.
- Safety: no training and no confirmatory-image access were performed.

## Blocking findings

1. CUDA logical ordinal remapping could make `cuda:1` execute on physical GPU0
   while the separate `nvidia-smi` check verified physical GPU1.
2. The YOLO fingerprint covered checkpoint-supplied YAML metadata rather than
   the instantiated module graph and parameter shapes.

All other historical findings remained closed. Training remained blocked.
These findings are addressed only in the subsequent v6 candidate and require a
new independent review.
