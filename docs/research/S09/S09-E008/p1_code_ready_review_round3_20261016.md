# S09-E008 P1 Code Ready review — round 3

- Reviewer: ChatGPT Pro (Haofan account, OpenCLI)
- Exact candidate: `cf3a9036fe72420ff24101038d0276d8f74df236`
- Conversation: https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b
- Review duration shown by UI: 14m 44s
- Scope: dependency-complete synthetic/no-training rereview; no producer access, real packet export, SSH, GPU training, optimizer construction, or optimizer step

## Verbatim review

REVISE\_AND\_REREVIEW

审核对象：cf3a9036fe72420ff24101038d0276d8f74df236。

**原始五个测试文件已独立复跑，结果为 64 passed。B1、B3、B4 可关闭；B2 的配置不变量检查已修复，但仍有一个代码身份绑定阻断：export CLI 可以检查另一份干净仓库，而不是实际执行的代码目录。** 已关闭的 F1、F3、F4、F7、F8 未发现回归。

## 一、实际核验结果

核验内容

本轮独立结果

Manifest 与恢复出的文件

**26 个文件**的字节数及 SHA256 全部一致，测试后再次核对仍一致

Python 编译与依赖

**20 个 Python 文件**通过 py\_compile；12 个被导入的项目模块均在附件内

原始 synthetic/no-training suite

**64 passed**，没有修改候选源码或五个原始测试文件

补充独立检查

**46 passed**，包含实际 exporter metadata 接口、配置漂移、路径、环境比较、早期失败回执及已关闭项回归检查

三个 CLI

\--help 均返回 0

46 项补充检查中包含**确认剩余反例能够复现**的测试；该测试的 passed 表示反例成立，不表示候选通过。

运行环境为 **Python 3.13.5、PyTorch 2.10.0+cpu，CUDA 不可用**。Optimizer 构造设置了禁止调用检查，未被触发；**optimizer 构造和 steps 均为零**。没有访问 producer、SSH、真实 packet 或科学数据目录，也没有执行真实 packet export。GPU 查询和 producer orchestration 的补充测试使用显式 mocks。

附件字节与 manifest 的对应关系已经核实；候选的 Git 归属依据附件的 git show 声明，没有访问原仓库认证该 Git 对象。Ruff 在本地不可用，原仓库的 git diff --check 也未独立复跑。附件对候选来源及提交方测试结果的声明见审核请求。

## 二、B1–B4 逐项结论

### B1．Exporter metadata 与 executable validator——关闭

Exporter 现在通过 frozen\_packet\_normalisers() 生成且只写入三个冻结 teacher-scale 字段：

纯文本

`damage_increment history_increment displacement`

equilibrium 和 interface 不再混入这个 metadata 对象。独立检查使用 **tiny synthetic exporter → 实际 writer → 实际 loader → executable validator**，实际产出的 metadata 已被接受，而不是仅检查一个手工拼装的预期字典。来源 qualification 和来源 decoder 在这项接口测试中明确使用 mocks，没有读取真实 A002 数据。

Equilibrium normaliser 仍在 resolver 中单独计算，然后才构造模型；独立的无训练时序检查确认了这一调用顺序。该时序测试不构成真实 CUDA/完整 native-size physics 的运行验证。

### B2．完整配置不变量与已审代码绑定——部分关闭，保留一个阻断

**配置部分已关闭。** \_resolved\_config\_base\_projection() 只逆向恢复声明的 resolution 字段，随后核对完整 canonical base-config hash。独立检查确认，修改 boundary tolerance、derived-f tolerance、minimum\_outputs、raw-increment coefficient、source identity 或加入未声明字段，均会被拒绝。原始 base-config 字节与上一轮完全一致，没有通过放宽条件实现修复。

**代码身份部分尚未完全关闭。** 现在确实有 approved-commit、tracked-file cleanliness 和 packet exporter commit 的比较；但 export CLI 的**实际执行根目录**与用户传入的 **\--repo-root** 没有绑定。下节给出已实测的唯一剩余 blocker。

### B3．路径、staging 与 GPU/environment——关闭本轮已列项

路径检查已经移到 canonical resolution 之前。独立检查覆盖了 ..、existing symlink、dangling symlink、相对路径、非批准 staging direct child 及不存在的 staging root，均被拒绝；合法 staging 路径通过，检查本身不创建输出文件。

GPU 记录已包含 UUID、PCI bus ID 和 name；resolver 与 execution preflight 使用这些字段及环境快照进行比较。使用显式 mocks 的检查确认 UUID、PCI、name 或 Python environment 漂移会被拒绝。**这只核验查询与比较逻辑，不代表已认证真实 Taobo 主机或 CUDA 设备。**

### B4．失败身份、计数和最后诊断位置——关闭本轮已列项

在已经准备好审计目录的情况下，独立测试了 no-CUDA、build qualification failure 和 execution-preflight failure，确认回执分别保留：

-   expected / observed packet hash 及 verification status；
-   optimizer\_steps\_completed 与 fully\_logged\_updates；
-   last\_diagnostic\_update 与最后有效诊断日志位置。

Runtime 尚未成功返回时，observed 为 null、verified 为 false，但 expected hash 不再丢失；runtime 返回后发生 preflight failure，则保留 observed hash。上述测试均停在 optimizer 构造之前。

更新计数的赋值顺序也已区分：optimizer 调用返回后增加 completed count；本次要求的日志及 scheduled diagnostic 写入完成后，才增加 fully-logged count。**这一部分做的是源码/AST 顺序核验，没有运行训练中途故障实验。**

## 三、唯一剩余 blocker：B2-R3——检查仓库不等于实际执行仓库

### 位置与原因

涉及：

纯文本

`scripts/export_s09_stage0a_p1_packet.py source/s09_code_identity.py::require_approved_code source/s09_stage0a_p1_packet.py::export_s09_e008_p1_packet`

CLI 从自身位置确定 ROOT，并从 ROOT/source 导入 exporter；但检查代码身份时，传入的却是独立的 args.repo\_root：

Python

`ROOT = Path(__file__).resolve().parents[1] sys.path.insert(0, str(ROOT / "source")) ... repo_root=args.repo_root`

因此，**加载代码的位置和执行 Git 检查的位置可以不同**。

require\_approved\_code() 只对传入的 root 执行 HEAD 和 tracked-file 检查，没有要求它对应实际执行模块所在的代码树。

### 实际本地复现

我创建了两份纯本地合成 Git checkout：

**A** 是干净的批准目录；**B** 从 A 复制，HEAD 相同，但在 B 的 exporter 源文件中加入一个无害的未提交常量。两次都实际执行 **B 的 export CLI**，并使用一个故意不存在的本地 synthetic config：

CLI 参数

实际结果

\--repo-root A，approved commit 为 A 的 HEAD

身份检查通过，继续到读取 config，随后报 **FileNotFoundError**

\--repo-root B，同一个 approved commit

在读取 config 前报 **ValueError: tracked execution files are dirty**

这证明：**同一份已修改的实际执行代码，只需把 \--repo-root 指向另一份干净目录，就能通过当前身份检查。**

这两份 Git checkout 及其 commit 都是本地测试 fixture，**不是对用户 cf3a903… Git 对象的外部认证**。两次调用均没有读取科学数据或导出 packet。

### 影响

该缺口直接影响 exact-commit provenance。若流程继续导出，当前 metadata 又会通过：

Python

`"exporter_code_commit": current_commit(repo_root)`

记录 **A 的 commit**，而非证明实际执行的 **B 的代码字节**属于该批准版本。后续 resolver 再比较这一字符串，不能补回缺失的执行代码身份绑定。这里的 metadata 后果是根据源码作出的判断，本轮反例没有实际导出该类 packet。

### 最小修复

**在任何输入读取前，将被检查的 repository root 强制绑定到实际执行 CLI/module 的根目录。** 最小做法是 export CLI 直接使用已有的 ROOT，或者保留 \--repo-root，但先拒绝其与实际 ROOT 不一致的情况；不能只验证用户传入的另一份目录。

补充三种无训练回归即可：同目录 clean 通过、同目录 dirty 拒绝，以及本轮的 **clean A / dirty executing B** 跨目录情形拒绝。保持现有配置、数据选择、阈值、容差和输出要求不变。

## 四、已关闭项的回归核验

已关闭项

本轮结果

**F1：D 与判据**

D 仍与 RMS 分离；判据及构造前分组/baseline 检查未改变。补充检查确认等于 0.25D 时接受、刚超过时拒绝。

**F3：固定 schema / canonical loader**

Loader、array validator、writer 的函数 AST 与上一轮一致；原始 tamper、dtype、canonical 检查仍通过。

**F4：非有限值与 prestate**

相关检查函数 AST 未改变；补充逐一向七类 output/support 字段注入 NaN，全部被拒绝。

**F7：三目标与梯度合并**

实名三目标、缺失/额外目标拒绝、零块补齐保持；额外做了六组合并代数与独立 NumPy 实现对照，均一致。

**F8：依赖闭包**

完整依赖与五个测试文件可实际复跑，不再存在附件缺失阻断。

Stage-0A transition、Q4/AMOR physics、operator backbone 和 merge 模块的整文件 SHA256 与上一轮一致；协议及 base config 也字节一致。另核对了 **10 个相关函数的 AST**，均未出现逻辑变化。上述结论只涉及代码与测试回归，不涉及记忆能力、泛化或科学有效性。

## 五、允许的下一 gate

**本次只允许：修复 B2-R3 → 本地 synthetic/no-training 回归 → 冻结新的 exact candidate commit → 独立 Code Ready 复审。**

B1、B3、B4 及此前已关闭项无需重新开启方法设计；下一轮重点应收束在**实际执行目录与被检查目录的绑定**及相邻回归。

当前不放行真实 packet export、Taobo resolution 或训练。后续取得 CODE\_READY\_PASS，也只允许进入真实 packet export 与 read-only Taobo resolution / final execution-gate 准备，不自动授权 optimizer training，更不构成科学结论。

独立复审证据包：26 文件 hash 核验、64 项原始测试、46 项补充检查、双目录 CLI 反例及复现脚本
