# S01-E001 independent code review v4

- Verdict: **FAIL**
- Bound protocol: `S01-E001-v4`
- Bound bundle SHA-256: `4f129708071a45d24f4c8cf8b662a68f3038d24d8ee78206650d9de95ffd54f0`
- Bound repository base commit: `dd738f177b5dbcced537a29497b4df3c38608a66`
- Hash verification: all 16 bound files and the workbook matched.
- Static tests: 25 passed.
- Safety: no training and no confirmatory-image access were performed.

## Blocking findings

1. The runtime gate checked only the caller-supplied `cuda:1` string. It did
   not freeze or observe the physical GPU name, UUID, PCI bus ID, driver,
   availability, or device count.
2. The proposer semantic gate checked a loadable one-class Ultralytics detector
   but not the frozen YOLO11n architecture. Another one-class YOLO family could
   pass a self-consistent synthetic chain.

All other v1-v3 blocking findings were confirmed closed. Training remained
blocked. These two findings are addressed only in the subsequent v5 candidate
and require a new independent review.
