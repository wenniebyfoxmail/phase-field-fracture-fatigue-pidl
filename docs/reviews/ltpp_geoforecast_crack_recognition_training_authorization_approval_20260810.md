# LTPP non-destructive recognition training authorization

Date: 2026-08-10  
Decision: `APPROVE_ONE_TAOBO_TRAINING`

## Approved execution

The reviewer found no remaining blocking item and authorized only:

- runner SHA-256
  `4022096e8ab47d17770e2c58498e3c13a3f6007711f8101ab7620a25aecc5c33`;
- producer: Taobo;
- authorization ID:
  `ltpp-recognition-nondestructive-v1-taobo-once`;
- exactly one complete six-section LOSO execution of the frozen challenger.

The approval is tied to the previously frozen input, static-source, validator,
and no-fit receipt hashes. Any optimizer step consumes the authorization. A
crash, incomplete fold set, recognition-gate failure, zero-crack-sentinel
failure, negative result, visual/provenance/metrics anomaly, or other runtime
failure does not permit an automatic retry, resume-as-new-run, individual fold
rerun, restart, rescue fit, or second execution. Any new fit requires a new
authorization request.

## Machine-readable receipt

`ltpp_geoforecast_crack_recognition_training_authorization_approved_20260810.json`

Claim boundary remains current-map recognition on the frozen scanned-form
carrier only.
