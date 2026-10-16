# S09-E008 P1 Code Ready rereview request — round 3

请复审 exact candidate commit
`cf3a9036fe72420ff24101038d0276d8f74df236`。第一行只输出
`CODE_READY_PASS` 或 `REVISE_AND_REREVIEW`，请用中文。

Round 2 已关闭 F1、F3、F4、F7、F8，并把剩余问题收敛为 B1--B4。本轮请重点核对：

1. exporter 的实际 metadata 与 executable validator 是否共享同一三字段 frozen
   teacher-scale schema，equilibrium 是否仍在 producer resolution 时单独冻结；
2. export、resolve、run 是否都绑定外部给定的 exact approved commit 与受审文件；
   resolved config 是否只允许声明的 resolution 字段变化，并能拒绝 boundary/f
   tolerance、minimum outputs 等任意未列入漂移；
3. 是否在 canonical resolution 前拒绝原始路径各级 existing/dangling symlink 和
   `..`，resolved config 是否只能写入外部批准的 staging root；GPU UUID、PCI bus ID、
   name 和完整环境是否在 resolve/run 间一致；
4. build/preflight 早期失败 receipt 是否分开记录 expected/observed packet identity、
   verification status、optimizer mutations、fully logged updates、last diagnostic；
5. round-2 已关闭项目是否仍保持闭合，且测试没有通过放宽物理判据、容差、输出要求、
   路径或授权实现。

附件由该 exact commit 的 `git show` 生成，包含完整依赖源码、三个 CLI、五个测试文件、
base config、协议、两轮原始审核回传和 implementation status。冻结后 focused
synthetic/no-training suite 为 `64 passed in 3.37s`；Ruff F、`py_compile`、三个 CLI
`--help`、`git diff --check` 均通过。没有 producer/SSH/GPU 访问、真实 packet export、
optimizer 构造或训练。

若仍有 blocker，请给出文件/函数、触发条件、影响和最小修复。若 PASS，只允许进入
真实 packet export 与 read-only Taobo resolution/final execution-gate 准备；不自动
授权 optimizer training，也不构成科学结论。
