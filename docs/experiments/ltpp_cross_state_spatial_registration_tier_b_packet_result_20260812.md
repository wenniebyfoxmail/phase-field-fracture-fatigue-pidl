# LTPP cross-state Tier B packet result — 2026-08-12

## Decision

`APPROVED_FOR_TWO_PERSON_BLIND_COLLECTION_ONLY__NO_FIT`

The collection packet for `27-6251 c3` and `08-1053 c2` is built and externally
approved for independent Tier B annotation only. No registration model was fit
and neither section is qualified for 2-D crack modelling.

## Immutable packet

Path:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_cross_state_spatial_registration_tier_b_review_candidate_20260812/`

- annotator A: 14 blind images and 14 empty unlocked records;
- annotator B: 14 blind images and 14 empty unlocked records;
- candidate tasks: 66 per map, 1,848 null statuses in total;
- public and sealed manifests: rechecked without mismatch;
- pre-review focused packet-builder tests: `4 passed`;
- sampled visual QA: four packet images retain readable printed map carriers
  and outer frames; handwriting and side ink remain visible but are forbidden
  evidence under the frozen occlusion/ambiguity rules.

The packet files retain their pre-review HOLD status and hashes. The separate
external-review decision authorizes release without rewriting the immutable
packet.

| Receipt | SHA-256 |
|---|---|
| protocol | `31344668bbd21ae0ee74ad274d90b217432fbc138edde55e5e0beff62c386986` |
| amendment | `d5cfaf245838cf337d1a0b5f532ce8d43b261916a85cbf971a47e46adc59e078` |
| request | `531af362de5e0bbd9e055277283aa8c0c0982d885f4d3d277669cfbdf6fe7424` |
| builder | `30a76b3bfaad7292aba524fb9a12c4be6d4dd8fcc0a30412a9e6c7dab8a51fe0` |
| submitted tests | `5a2a63ff459d906c44550877cb65d40e387eddcc5969f78ccd1b86837487e8a5` |
| packet status | `adb86849722c2a11d9f7b18a1a209c01cbe2196688f1896298a78da7b5e98e0f` |
| public manifest | `3a186637c93c450d60d5280e1bbba61e248ba7b7fc2cd80909bf14017551c1f5` |
| sealed manifest | `aa6756a60c1032c8f60117fdce2ceaa1c0647ff1ed065773187edade7b083b0e` |

## Future independent-validation option

Recruit two eligible blind annotators; neither may be the user, implementer,
protocol reviewer, or anyone exposed to prior registration outcomes or
cross-date crack evolution. Release one role to each person in isolation. Only
after both roles lock may the custodian run the existing mechanical availability
consensus. Transform fitting remains unauthorized.

For operational release, run the existing local annotation server with
`--expected-maps 14`; its default remains 8 for the historical packet. This is
a packet-size compatibility switch only and does not alter records, candidate
roles, controls, or scientific gates.

Post-review operational smoke: both A and B roles opened with 14 maps, and the
expanded focused suite passed `5 passed`. Annotator-server SHA-256 is
`0a6bda1fbe24e1106d859024e6eb9c9f6c6bd786ff7eb2b06b61e83976d3cba0`;
the expanded test-file SHA-256 is
`49c1f46d2ebe38ba898ae6e60d49d3a96b9d0da6fe146e31d2544964bf632500`.

For the current project stage, the owner chose a separate one-person
development route instead of recruiting two annotators. That route is recorded
in `ltpp_cross_state_single_owner_grid_annotation_20260812.md`. It does not
modify this immutable packet or inherit its independent-control status.
