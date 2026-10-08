# GPT Pro code review

## Review 1

- Bound commit: `8d2eb87a853083946ab105d5a5796911c6a9ca6a`
- Verdict: `BLOCKED_CODE_READY`
- Blocking findings:
  1. the required representative figure could select an empty tip mask and
     incorrectly label pixel `(0, 0)` as a released tip;
  2. the formal producer guard did not bind the reviewed commit or the
     authorised Taobo host.
- Non-blocking hardening adopted: scan all saved prediction arrays for finite
  values before writing the NPZ.
- Resolution: the two guards and regression tests were added without changing
  the model, split, loss or relaxed v1 performance criteria. A second review is
  required on the resulting commit before launch.
