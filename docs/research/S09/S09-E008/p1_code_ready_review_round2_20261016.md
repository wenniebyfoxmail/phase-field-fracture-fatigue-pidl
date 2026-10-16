# S09-E008 P1 Code Ready review — round 2

- Reviewer: ChatGPT Pro (Haofan account, OpenCLI)
- Exact candidate: `b9f2a2ea999c43c637e2deb9ef407002bd487f97`
- Conversation: https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b
- Review duration shown by UI: 11m 49s
- Scope: dependency-complete synthetic/no-training rereview; no producer access, real packet export, SSH, GPU training, or optimizer step

## Verbatim review

REVISE\_AND\_REREVIEW

审核对象：b9f2a2ea999c43c637e2deb9ef407002bd487f97。

**五个原始测试文件已独立复跑，结果为 59 passed；但当前候选仍不能通过 Code Ready。** 本轮可关闭 **F1、F3、F4、F7、F8**；**F2、F5、F6 部分修复，尚未闭合**。最直接的阻断是一个正常路径上的接口错误：**exporter 生成的 normalisers metadata 会被 executable validator 拒绝**，并非需要异常输入才触发。

## 一、实际核验与边界

我恢复并核对了 manifest 中的 **24 个文件，字节数和 SHA256 全部一致**，测试后再次核对仍一致；**19 个 Python 文件通过 py\_compile，三个 CLI 的 \--help 均返回 0**，项目源码 import 未发现缺项。附件声明这些文件由指定 commit 的 git show 生成；本轮确认的是附件字节与 manifest 的对应关系，没有访问外部仓库认证 Git 对象。

原始五文件 suite 在本地 **Python 3.13.5、PyTorch 2.10.0+cpu、CUDA 不可用**的环境中得到 **59 passed**。另完成 **20 项独立检查**：其中 11 项检查已修复行为，9 项用于复现剩余缺陷或检查缺失的 guard；**反例测试通过，表示缺陷被成功复现，不表示候选通过。**

本轮没有访问 producer、SSH、真实 A002 packet 或科学数据目录，没有执行真实 packet export，**没有构造或运行 optimizer，optimizer steps 为零**。独立接口测试只使用 tiny synthetic arrays；producer 失败路径只在隔离 mocks 下运行至注入异常。当前容器未安装 Ruff，因此没有独立复跑其检查；也没有把提取目录上的检查冒充原仓库的 git diff --check。

## 二、F1–F8 逐项复审

原 blocker

本轮结论

核验结果

**F1：D、判据与分组资格**

**关闭**

D 与 damage RMS 已分字段，正式判据使用 0.25 D，输出实际阈值；分组非空和正 persistence baseline 在模型构造前检查。独立测试覆盖等于阈值、刚超过阈值、空分组和零 baseline。

**F2：配置、packet 与已审代码绑定**

**部分修复，未关闭**

width/lr/scales/groups/epsilon 漂移已拒绝；resolver 已增加外部 approved commit 与 tracked-file 检查。但存在 exporter/validator metadata 不兼容、resolved config 不变量检查遗漏，以及 exporter 本身缺少代码批准绑定。见 B1、B2。

**F3：固定 schema 与 canonical loader**

**关闭原项**

已补 canonical identity/manifest bytes、bytes/count、固定数组 membership、dtype/shape/finiteness 和既有数组语义检查；不再仅相信 manifest 自述 dtype/shape。teacher alpha/f 的进一步资格检查由构造前流程承担。

**F4：非有限值与 prestate 检查时序**

**关闭原项**

negative alpha 已在模型构造前拒绝；七类 projected/raw output 与 support-weight 字段先检查有限性；evaluation 检查 metrics 后才返回 finite=True。约束容差本身能否漂移，另归 F2。

**F5：producer 路径与环境**

**部分修复，未关闭**

原来的越根路径反例已被拒绝，run/archive direct-child 和 environment 比较已补；但 symlink 检查发生在 resolve() 之后，仍接受同根链接重定向；GPU 唯一身份与 resolver staging 也未完全锁定。见 B3。

**F6：日志与失败证据**

**部分修复，未关闭**

loss、gradient、scheduled diagnostics 已增量写入并 flush，未缩放 raw-increment MSE 与新增梯度诊断已补；但早期失败的 expected packet identity、部分失败覆盖及更新计数语义仍不完整。见 B4。

**F7：目标缺失与参数顺序**

**关闭**

autograd 前要求恰好三项、实名、固定顺序；未连接参数保留零块；每步 parameter order 对照 resolved config。missing/reordered objectives 的拒绝测试已通过。

**F8：依赖与测试附件缺失**

**关闭**

三个缺失源码和四个缺失测试文件均已补齐，完整五文件 suite 已复现。其他接口测试的遗漏不再归为“附件缺失”。

F1 的实际 false-growth 上限现在为：

0.25D\=0.25×0.00016864539921617467\=4.216134980404367×10−5.0.25D=0.25\\times0.00016864539921617467 =\\boxed{4.216134980404367\\times10^{-5}}.

代码直接使用独立的 detectable\_growth\_scale\_D，并在构造前检查分组与 baseline；这修复了上一轮把 RMS 当成 DD 的错误。这里确认的是**实现及配置一致性**，没有重新读取真实 A002 数据认证该数值。

F3、F4、F7 的主要修复分别对应 loader 的固定检查、输出有限性检查和实名三目标检查；这些已实现的修复应保留，不必重新改写方法。

## 三、仍需修复的四项发现

### B1．正常导出的 normalisers metadata 与执行校验不兼容——F2

**位置：**
source/s09\_stage0a\_p1\_packet.py::export\_s09\_e008\_p1\_packet
source/s09\_stage0a\_p1\_trainer.py::\_validate\_reviewed\_config

exporter 写入的是完整对象：

Python

`"normalisers": config["normalisers"]`

因此 metadata 有五个字段：damage\_increment、history\_increment、displacement、equilibrium、interface。但 executable validator 要求它与仅含前三个字段的 expected\_scales **整个字典相等**。

**实际复现：** 我在 9-node、4-Q4 合成 fixture 上运行了未修改的 exporter、writer、loader 和 validator。只对来源 qualification、来源 decoder 和合成 A002 receipt hash 做显式 mocks，没有接触真实数据。同一份 exporter 实际生成的 metadata：

纯文本

`executable=False：接受 executable=True：ValueError: packet frozen normaliser metadata drift`

**触发条件与影响：** 正常 exporter 输出进入 executable validation 即触发。它会在进入训练前拒绝正常 packet，不能通过真实运行来“验证是否有问题”。

**最小修复：** 为 frozen teacher scales 定义一个共享的明确 schema，exporter 与 consumer 使用同一个三字段对象；equilibrium placeholder/interface 与其分开保存，equilibrium 仍按既定顺序在 resolver 冻结。增加**使用 exporter 实际产出 metadata 的正向、无训练接口测试**。

目前原始 runner fixture 手工构造的 metadata 没有完整覆盖这些字段，主要 runtime 测试使用 executable=False，因此 59 项通过没有覆盖这个交界。

### B2．resolved config 的不变量未完整锁定；exporter 仍缺少已审代码绑定——F2

**位置：**
source/s09\_stage0a\_p1\_trainer.py::\_validate\_reviewed\_config
source/s09\_stage0a\_p1\_packet.py::export\_s09\_e008\_p1\_packet
scripts/export\_s09\_stage0a\_p1\_packet.py

**配置部分的实际复现：** 独立 validator 探针中，以下修改仍被接受：

-   peak\_boundary\_lifting.atol = 1.0；
-   derived\_f\_identity.atol = 1.0；
-   minimum\_outputs = \[\]。

其中边界容差不只是文字漂移：在 tiny CPU runtime 中加入 **0.1 的边界误差**，原容差下被拒绝，改为未被锁住的容差后，hard\_constraint\_report() 返回零违反计数。该函数确实从 config 读取容差。

上述 executable-validator 探针使用的是该 validator 要求的三字段 metadata，以**单独隔离检查 F2**；没有把它冒充当前 exporter 已能成功进入执行路径。问题的核心是：**检查 receipt 里写着正确的 base-config SHA，并不等于验证 resolved config 只改变了允许 resolution 的字段。** 当前实现检查了若干指定字段，但没有完整的不变量比较。

**代码身份部分的静态核验：** resolver 已接收并检查外部 approved\_code\_commit，这项修复成立；但 exporter 函数及 CLI 仍没有 approved-commit 输入、当前 commit/执行文件检查，也没有把 exporter 的代码身份写入 packet。之后批准 trainer commit，不能反向证明 packet 是由同一个已审 exporter 产生的。

**最小修复：** 对 hash 已验证的 base config 做完整不变量比较，仅允许明确列出的 resolution 字段变化；约束容差、minimum outputs 等不能遗漏。同时让 exporter 与 resolve/run 共享已审 commit 和执行文件身份检查，并将 export 代码身份绑定到 packet。不要通过放宽容差或删减输出要求来修复。

### B3．symlink 检查在解引用之后；设备身份及 staging 仍未闭合——F5

**位置：**
source/s09\_stage0a\_p1\_trainer.py::validated\_producer\_paths
resolve\_execution\_config、\_execution\_preflight

当前路径函数先执行 resolve()，随后才对结果调用 is\_symlink()。这时原路径上的链接已经被解引用，因此该检查不能证明原路径没有 symlink。

**实际复现：** 仅在本地临时目录中映射两个批准根目录，创建指向**同一批准根内、尚不存在目标目录**的 run/archive symlink。函数接受这些路径，并返回被重定向的目标；含内部 .. 的路径也会规范化后被接受。

这不是声称新反例逃出了批准根：**旧的越根漏洞已修复，但声明的“拒绝 symlink / 非 canonical 路径”没有实现。**

另外两点由源码直接确认：GPU 校验使用 get\_device\_name(0) 和 CUDA\_VISIBLE\_DEVICES 文本，未记录每张卡的唯一身份；resolver 对任意 output\_path 创建父目录，没有阻止 resolved config 被写进未来 run/archive root，进而提前破坏 freshness。

**最小修复：** 在解引用前检查原始路径成分和各级链接，包括 dangling symlink，再核对 canonical direct-child 与 freshness；将 resolved config 限定到事先批准、不会创建未来 run/archive root 的 staging 位置；记录并复核能区分同型号设备的物理 GPU 标识。保留已经补上的 hostname/environment 比较。

### B4．早期失败仍丢失 expected packet 身份；更新计数没有区分完成与完整审计——F6

**位置：**
source/s09\_stage0a\_p1\_trainer.py::run\_training

**实际复现：** 在 build\_runtime 处注入前置资格失败，确保 optimizer 构造不可能到达。代码确实生成了 archive failure receipt，并正确记录 stage 和 successful\_updates=0；但其：

纯文本

`packet_manifest_sha256 = null`

resolved config 中已经存在的 **expected packet hash** 没有另行保留。原因是异常发生时 runtime 尚未返回，failure handler 只尝试从 runtime 取 packet identity。

这里**不应把尚未验证的 expected hash 填成 observed hash**。正确修复是分开记录预期身份、实际观察到的身份及验证状态。

源码还保留两处上一轮要求中的缺口：部分批准、路径及 archive 创建检查位于 try 之外；successful\_updates 在 optimizer.step() 返回后立即增加，早于本次诊断构造、序列化和 flush。因此它统计的是已返回的 optimizer 调用，而不是另外验证过的“完整审计更新”。

**最小修复：** 在可信审计上下文中先保存 expected code/config/packet identities，observed identity 单独记录；让可安全留痕的前置失败进入结构化 failure 路径，不为留痕创建未经批准的目录。分别记录已完成 optimizer mutation、最后完整写入的更新和最后有效诊断位置。现有增量日志与 scheduled diagnostics 的修复应保留，无需重做。

## 四、允许的下一 gate

**本次只允许：本地有界修复 B1–B4 → synthetic/no-training 回归 → 冻结新的 exact candidate commit → 独立 Code Ready 复审。**

F1、F3、F4、F7、F8 无需重新开启方法设计；修复重点是接口一致性、身份锁定、路径和失败审计。**本次不放行真实 packet export、Taobo resolution 或 optimizer training。**

后续取得 CODE\_READY\_PASS，也只允许进入用户限定的真实 packet export、read-only Taobo resolution 与 final execution-gate 准备，不自动授权训练，更不构成科学结论。

独立复审证据包：24 文件 hash 核验、59 项原始测试日志、20 项独立检查、反例脚本及复现说明
