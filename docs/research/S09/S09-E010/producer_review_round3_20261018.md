# S09-E010 producer focused rereview round 3

- Review channel: ChatGPT Pro, Haofan account
- Conversation: <https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb>
- Review package: `S09-E010-producer-rereview-d31ca666.RIvcmu.zip`
- Package size: 32,623 bytes
- Package SHA256: `f03d0ff494d72073218fefb7bc89fe021f58dbd55c588c5fcb8220ac719554a3`
- Base commit: `7548a97aa4268fa89586a660e597e58dbe539a0c`
- Reviewed candidate: `d31ca666dcde44cdf30ef9b9c45044a2c95c217f`
- Verdict: `REVISE_AND_REREVIEW`

The reviewer independently verified the ZIP identity, all 4/4 manifest content
files, CRC, path safety, and the exact base-to-candidate patch. R3 (strict disk
termination-receipt schema validation) and R6 (preserving current-arm counts
when receipt close fails) were closed.

One R4 blocker remained. `_decision_from_results()` placed any
`METHOD_INAPPLICABLE` state before the shared-identity validity result, so a
real shared/start identity mismatch could be reported as method-inapplicable.
The A25 replay-stop helper similarly allowed every method-inapplicable A25,
without separating missing update-500 evidence caused by legal anchor
stationarity from a failed frozen start-identity clause. The reviewer reproduced
this with a legal A25 method stop, completed B25/B0 arms, and a single B25
initial-state identity change: `shared_identity_pass` was false but status was
`METHOD_INAPPLICABLE` instead of `EXECUTION_INVALID`.

The required minimal repair is to keep a legal A25 method stop arm-local only
when all frozen A25 start-identity clauses pass, and to give shared-identity
failure validity priority over method status in the final decision. The frozen
losses, arms, budgets, thresholds, data and scientific criteria remain
unchanged. This review did not authorise producer execution.
