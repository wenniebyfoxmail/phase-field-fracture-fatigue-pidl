# Stage-0A decoder independent-review submission — 2026-10-16

- reviewer surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- target commit: `637235af6c2b68b24a832191a4ae691902e964f6`;
- submitted packet: `decoder_code_review_request_20261016.md`;
- submitted packet SHA256:
  `845562202f277983f6a62358b137aaeb79ac4bfd760e6e34f63126f4ef2c6cea`;
- submitted scope: read-only source/state audit, fail-closed decoder, synthetic
  tests and Stage-0A P1 interface;
- explicit exclusions: no scientific payload decode, FEM execution, training,
  Stage 0B or scientific-validity upgrade;
- UI verification: the new conversation visibly contains the named attachment
  and the exact instruction to return the A--G review with a one-line verdict;
- completed verdict: `REVISE_AND_REREVIEW` after 9m18s of Pro review;
- response record: `decoder_code_review_round1_20261016.md`.

Submission itself is not Code Ready. The first review independently reran seven
packet tests and 18 directed synthetic probes. It passed the bounded state-
sufficiency classification but found material decoder/P1 interface gaps that
must be repaired and rereviewed before scientific payload decode.
