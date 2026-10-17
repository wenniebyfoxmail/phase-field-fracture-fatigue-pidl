# S09-E009 producer package exact-commit review request

Please review exact commit `3a3296d63370babda8ad7063fdfcff306a18bedb` only against its parent `dd6acd0b56940b41afe65b67c748b712cd581195`.

Return exactly one of these tokens on the first line:

- `PRODUCER_PACKAGE_READY_PASS`
- `REVISE_AND_REREVIEW`

This is a focused review of the newly added producer layer. The numerical core and no-training runner integration are inherited trust anchors:

- core `8b6a2e49b241ae73f433645cb30a69291f7aee53` — `CORE_CODE_READY_PASS`;
- integration `efeffbfae4395f95228c56e3f530e323f1ab8f6a` — `RUNNER_INTEGRATION_READY_PASS`.

Review questions:

1. Does the resolver bind the exact reviewed integration/config/protocol/base/packet, exact clean producer commit, approved staging path and physical GPU identity without an optimizer step or caller-spoofable execution identity?
2. Does the four-arm state machine preserve the frozen 500-per-arm schedule, no budget transfer, true optimizer-step count after a post-step logging failure, conditional checkpoint semantics and all terminal receipts?
3. Is R an exact E008 replay through update 500, including the legacy first-500 gradient-row byte stream and numeric replay gate, with no second clip?
4. Does the evaluator compute every frozen metric from one checkpoint over all 16 examples, preserve the fixed growth/stagnant support and strict JSON/NA rules, and reject incomplete scorecards?
5. Does the writer emit the declared conditional evidence set, prevent performance interpretation after an execution/replay/shared-identity failure, and preserve graded component progress without upgrading it to a scientific claim?
6. Do the local tests genuinely avoid `AdamW.step`, producer access, SSH and training while exercising resolver, state machine, evaluator, replay bridge and writer?
7. Are the two explicit CLIs and final run card sufficient for one later reviewed/authorised producer run, with CSD3 fallback prohibited?

Local evidence at the exact commit:

- selected suite: `84 passed in 2.17s`;
- `py_compile`, Ruff F/E9 and `git diff --check`: pass;
- exact real-packet update-0 evaluator reproduction: `L_judge=0.8541368615961056`, `G=0.0005017354462152066`, `persistence=0.0005017354462152066`, `F=0`, violations `0`;
- all producer tests replace `torch.optim.AdamW.step` with a fail-if-called sentinel.

A PASS means code-ready for the separate final execution/preflight action only. It does not authorise SSH, transfer, optimiser execution or training, and it is not a scientific result.
