# S09-E008 P1 Code Ready review — round 4

- Reviewer: ChatGPT Pro, Haofan account
- Conversation: https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b
- Submitted: 2026-10-16 15:02 BST
- Review duration shown by ChatGPT: 13m 30s
- Exact candidate: `f54327490ce8c02f6c042753d36ddcd32ecc5771`
- Bundle: `S09-E008-P1-code-ready-rereview-round4-bundle-f543274.md`
- Bundle bytes: `68532`
- Bundle SHA256: `6471c551a4bb29f04af41afc4bec0ee5f48f1dba29d971d61c5f666e30795d32`
- Verdict: `CODE_READY_PASS`

## Verbatim reviewer response

CODE_READY_PASS

审核对象：`f54327490ce8c02f6c042753d36ddcd32ecc5771`。

**B2-R3 已关闭：clean A / dirty executing B 的双目录反例，已被 CLI 与 exporter 函数接口共同消除。** 同目录 clean/dirty、错误 approved commit，以及相邻 B2 binding 的独立检查均符合预期；本轮未发现新的阻断。B1、B3、B4 维持关闭。

## 一、实际核验范围与结果

本轮 manifest 的 **6 个文件，字节数及 SHA256 全部一致**。附件中的四文件 exact diff 能应用到上一轮附件，应用结果与本轮对应文件逐字节一致。

为复跑测试，我使用了**上一轮附件中的未变依赖，加上本轮文件覆盖**；没有把未重新附带的依赖冒充本轮完整 Git 导出，也没有访问原仓库认证 Git 对象。

| 检查 | 独立结果 |
|---|---|
| 重建后的五文件 synthetic/no-training suite | **65 passed** |
| 双目录、同目录及相邻 binding 专项测试 | **14 passed**，其中一项包含六种 binding 漂移检查 |
| Python 编译 | **20 个文件通过 `py_compile`** |
| 三个 CLI `--help` | 均返回 0 |
| 测试后文件身份复核 | 基线目录中的源码、配置和测试字节均未改变 |

运行环境为 **Python 3.13.5、PyTorch 2.10.0+cpu，CUDA 不可用**。Dirty 反例只修改独立的本地 fixture 副本。没有访问 producer、SSH 或真实科学数据，没有导出真实 packet；**optimizer 构造与 steps 均为零**。本地未安装 Ruff，未独立复跑 Ruff。

## 二、双目录反例的实际复现

本轮使用**真实本地 Git 仓库与实际 CLI 子进程**，没有 mock Git 的 commit 或 cleanliness 返回值。

先做旧版本正对照：上一轮代码仍能让 dirty B 的 CLI 检查 clean A，从而通过代码身份门、继续到故意缺失的 synthetic config；指向 B 自身时则拒绝。随后对修复版本得到以下结果：

| 场景 | 修复后的实际行为 |
|---|---|
| 执行 dirty B，仍传 `--repo-root A` | **CLI 参数解析直接拒绝**：`unrecognized arguments: --repo-root`，退出码 2 |
| 执行 dirty B，不传已删除参数，并将工作目录设为 clean A | **读取 config 前拒绝**：`tracked execution files are dirty` |
| 同目录 clean A / clean B | 代码身份门通过，随后触发预先设置的缺失 synthetic config 哨兵 |
| 同目录 dirty：修改 exporter、export CLI 或 shared identity module | 均在读取 config 前拒绝；**staged modification** 也被拒绝 |
| Clean 目录，但 approved commit 错误 | 在读取 config 前拒绝 commit mismatch |
| 直接调用 exporter 函数并传旧 `repo_root=` | **Python 接口拒绝**：`TypeError: unexpected keyword argument 'repo_root'` |

这里的 clean 情形以 `FileNotFoundError` 作为**通过身份门后的预设停止点**，不是 packet export 成功，也不是测试失败。

修复不只是隐藏帮助文本中的参数：CLI 已删除 caller-controlled root；函数也不再接收该参数，并在读取 config 前从自身 `__file__` 得到实际代码根目录。

## 三、相邻 B2 binding 核验

**身份检查与 metadata 记录使用同一个实际 module code root。** 独立探针从 clean A 导入并运行 exporter，即使当前工作目录位于 dirty B，实际 Git 检查及 metadata 的 commit 查询仍指向 A；代码记录也使用 `current_commit(code_root)`，不再使用外部提供的另一目录。

这项探针保留真实的 Git identity、tracked-file cleanliness 和 base-config hash 检查；仅对来源 qualification/decoder 使用 synthetic mocks，并捕获 writer 参数，**没有写出 packet**。实际产生的 metadata 可通过既有 executable validator。分别改变 exporter commit、approved/training commit 一致性、packet hash、base-config identity、boundary tolerance、minimum outputs，六种漂移均被拒绝。

按已核对的 exact diff，shared identity module 未改变，完整配置不变量检查及既有消费端绑定也未改变；没有通过放宽容差、阈值或输出要求来关闭本项。

**本轮不需要进一步代码修复。**

## 四、允许的下一 gate

本次 `CODE_READY_PASS` 只允许该候选进入：

**真实 packet export → read-only Taobo resolution → final execution-gate 准备。**

真实 packet 身份、Taobo 环境与设备、equilibrium normaliser 及 resolved config，仍须在各自 gate 中实际核验。

本次不自动授权 optimizer training，也不构成 P1 通过、模型能力或科学有效性结论。这一授权边界与附件请求一致。
