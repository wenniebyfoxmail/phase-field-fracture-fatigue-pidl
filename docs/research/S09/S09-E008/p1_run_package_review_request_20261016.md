# S09-E008 P1 run-package independent review request — 2026-10-16

第一行只输出 `PACKAGE_READY_PASS` 或 `REVISE_AND_REREVIEW`。请用中文。

审核对象是 commit `785129c` 固定的 bounded P1 memorisation run package。只做包级设计/可执行性审核；不要训练、不要访问 producer、不要把本审核提升为 Code Ready。

请检查：

1. 学习映射与 Stage 0A 边界是否一致，是否仍有 same-cycle/future leakage 或错误 rollout 含义；
2. 16 cycles、normalisers、history 通道、f 的派生关系和 native supports 是否一致；
3. width/rank/seed/dtype/1,000 updates/data order/AdamW 参数是否确定到足以实现；
4. 三目标、raw increment 配对、逐目标 autograd、median norm equalisation、fixed cyclic projection、zero-gradient 与 global clip 的顺序是否闭合；
5. `L_judge`、growth、near-stagnant、hard constraints 与诊断 buckets 是否既不互相混写，也不让次要诊断 rescue 正式 verdict；
6. equilibrium normaliser、packet identity、trainer commit、GPU id 等当前占位符是否处在正确 gate，是否还有必须在实现前冻结但遗漏的决策；
7. stop rules、minimum outputs、Taobo fresh roots、no CSD3 fallback 和 no-training boundary 是否一致。

若 PASS，只允许实现 packet exporter 与 trainer、做 synthetic/local no-training tests，并提交 exact-commit Code Ready 审核；不得启动训练。

## Attachment manifest

- `docs/research/S09/S09-E008/p1_memorisation_run_package_20261016.md` — 4630 bytes — SHA256 `9aa032370e645633b41460ed835db445a47b34863222f998ff869916dec0b672`
- `docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json` — 5729 bytes — SHA256 `b0224306eb7ea0ce06684f2aa4ba757ae8ccf5fb59553f34232996bf85fbb1e7`
- `docs/research/S09/S09-E008/experiment.md` — 11150 bytes — SHA256 `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34`
- `docs/research/S09/S09-E008/implementation_contract.md` — 4095 bytes — SHA256 `5775e025d38568f3bb0923e937b7ef15762a1ca207eee810c694f20fdff5bb80`
- `source/s09_stage0a_transition.py` — 12234 bytes — SHA256 `7627778ab6bff56cccd3017d45afe9c04329f41b62a06bcf1ddeb5150c523be7`
- `source/s09_multiobjective_update.py` — 2271 bytes — SHA256 `7d42a90eb48267a1762481f6cbc76739b193248981fda880d410d4cb55062352`
