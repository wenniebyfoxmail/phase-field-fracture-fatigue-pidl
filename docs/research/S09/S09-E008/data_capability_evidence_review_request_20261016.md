请对 S09-E008-A002 的真实 scientific data-capability receipt 做独立 Evidence Ready 复核。请用中文。附件包含完整 JSON receipt；不要访问 CITPC12，不要训练或运行 FEM。

第一行只输出 EVIDENCE_READY_PASS 或 REVISE_AND_REREVIEW。

请独立检查：
1. receipt 身份：audit_id、host、target commit `918ec57e1b6eaf3c9489ae37af866328775021ac`，核心代码 hashes；
2. 366 unique payload inventory 是否数量唯一、SHA256 格式有效、bytes为正，hash qualification verdict 是否一致；
3. decoded physical=366、logical=438、substeps=0..5、context/static identity 是否一致；
4. logical bindings 是否正好覆盖 c0001_s00..c0073_s05，72个alias source关系是否符合 prior-s05，hash/load/fingerprints 字段是否完整；
5. P1 selected cycles 是否恰为16个且在1..73，growth和near-stagnant至少各4个，D/eta/normalisers是否有限、正值及内部关系合理；
6. native weight shapes是否为86756和86408x4，static hash是否匹配冻结值；
7. 明确区分 execution/data-capability PASS 与训练、accuracy、rollout、generalisation、FEM truth、teacher validity、PINO benefit。

允许的下一步若 PASS：只允许准备一次有界 P1 memorisation run 的最终 run package/approval gate；不得直接训练。

附件身份：
- receipt SHA256 `5e41fd019f8bbe0bcc297923f659c215c3bf085a9bd7aa2e3146e3183b9f6de9`，486723 bytes；
- packet summary commit `7c5d7a7a3eef095bf7b75b5399fb69af19e5074c`；
- capability code SHA256 `a2fe082938837e16bc26f7f41cd2063726255ec59bf70e36d884ccfd0b2df5ad`；
- packet code SHA256 `02f1f742d3b69977d10db5ba46904864104ec7ce1dd93e7c5c660d39dae589e0`；
- P1 code SHA256 `8502f52dad72d8310f514304f1837a1b493590b577f067cafc6bdcad8f358514`。
