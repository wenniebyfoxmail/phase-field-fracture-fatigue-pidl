# 梯度算术路径最小零更新核验（设计 v2；未实施、未执行）

**当前处置：复用另一owner已完成的算术对照；本方案作为补充设计保留，暂不实施或执行。详见末节收口补充。**

本轮仅准备方案并独立审核。没有新 producer Run、NN forward、参数扰动、训练或 FEM 求解。
原始失败和9项差异保留；`atol=1e-6, rtol=1e-4` 不变。设计审核不等于 Code Ready 或执行许可。

## 问题、复用与范围

S04 / S04-E011，C1 evidence-validity，synthetic，同一已见 c1s1 C 原点的数值诊断。
问题：现有全参数梯度分解差异主要来自系数求值、反传中加权/汇合/归约的浮点次序，
还是参数布局、漏项、状态/映射或梯度实现错误？本轮不评估 W0/W25 效果。

复用 `pf_s04e011_wpair_grad_audit_20261018_v1`（GPU源码 `99cad0b3`）的
初始 bundle、原输入、原始6组向量与[已审核结果](runs/loss_weight_no_step_audit_20261018_result.md)。
9/1,125,211项越界，相对L2差1.069986724e-6；H3[1,386]容差比2.531779。
末端重累加 saved-float32 gradients 仍9项失败，既没有重放模型，也同时改变了系数与运算顺序，不能作归因。

已检查的实现：`tools/loss_weight_diagnostics.py::gradient_probe/flatten_grad`、
`tools/run_loss_weight_pair.py::make_field/evaluate/regularizer`、
`source/nodal_damage_alignment.py`、`source/compute_energy.py`、`source/q4_quadrature.py`、
`source/network.py::TrainableReLU`、`SENS_tensile/field_computation.py::NonsmoothSigmoid`。
静态上当前链式公式包含 Eel/Ed/Eh/R，beta只乘Eh，R只包含名字含weight的参数；
尚未发现可直接确认的漏项，但静态等价不证明数值反传正确。
选择 continue：只分解已有失败，不改物理、初始化、网络、gamma、容差或训练器。

## 决策阶梯与冻结项

| 步骤 | 最小动作 | 继续条件 / 转向条件 |
|---|---|---|
| D1 已完成 | 复用已保存差异和实际代码 | 不重复原权重实验 |
| D2 当前 | 冻结本设计，独立只读审核 | 设计通过后仍需独立runner实现、Code Ready和明确执行授权 |
| D3 未执行 | 一次有界零更新算术核验 | 按下表归因；缺数据或超时保留inconclusive，不重试 |

固定 U=.02999988，beta=1，weight_decay=1e-5，全部对称/硬box新补丁关闭；
86756原生节点、86408 Q4、2×2 GP，251-node crack line；AT1/volumetric、
E1/nu.3/w1=1/l0=.01/tol_ir=.005（gamma16875）、residual_stiffness0、f_fatigue1。
network、mapper、所有history及输入均复用同一原件；不新增FEM target或holdout。
先核对完整 SHA256/bytes，不只按文件大小认同一输入。原始来源：

- `/mnt/data2/drtao/pidl_archives/pf_s04e011_wpair_grad_audit_20261018_v1/readout/initial_bundle.pt`
- 同目录 `preflight_origin_gradients.failure.pt/.json`
- `/mnt/data2/drtao/wennie/pf_s04e011_wpair_grad_audit_20261018_v1/inputs/` 下 network/history/initial_inputs。

当前本地没有全量原始向量/bundle；未来执行前只读核验远端身份、冻结manifest。
不能把当前摘要当成全量已取回；输入身份不明即停止，不重建或换源。

## 一次运行中的最小对照

必须使用**独立只诊断runner**：不创建optimizer、不调用训练main、不带200步或两臂schema；
不更新history。生产runner及其失败检查不修改、不绕过。诊断runner把失败写出后完成
本表预先规定的对照，失败不会打开训练入口。所有比较先保存向量再写判定。

记 `e=(Eel,Ed,Eh)`，`S=Eel+Ed+Eh`，`L=log10(S)+lambda*R`，lambda=1e-5。
`theta`严格按named_parameters排列，保存名字/形状/offset/requires_grad/unused-mask；
不以state_dict含buffer的顺序代替参数布局。`autograd.grad`不写入`.grad`。
每个dtype只构建一张原点图并retain，所有种子detach；保存native scalar seeds本身。

| 路径 | 精确操作 | 区分的因素 |
|---|---|---|
| D | `grad(L,theta)`，同图首尾各一次 | 完整路径与同图重复性 |
| P | 原实现：raw `grad(e_j,theta)`及`grad(R,theta)`，再乘手算c并按原顺序相加 | 重现旧expected；FP32末尾再读4组raw得到P-repeat |
| N | 对`L`求相对于`(Eel,Ed,Eh,R)`的native scalar seeds；保存与`1/(ln(10)*S)`、lambda的逐位差 | 只比较系数求值；不得用Python double重算替换native seed |
| M | `grad((Eel,Ed,Eh,R),theta,grad_outputs=native_seeds)`，一次多输出VJP | 固定系数，检查共同反传路径汇合 |
| U | 对每个输出分别用对应native seed作VJP，再按固定顺序相加 | M与U区分同时/分次反传；不是把raw参数梯度末端乘种子 |
| Q | 将同一raw参数梯度在末端乘native seeds，按P顺序相加 | U与Q区分反传前加权/反传后加权；Q与P只改系数 |

全部保存 P/D/N/M/U/Q 及重复读数。按CPU float64从**已经保存的向量**计算
`D-P = (D-M)+(M-U)+(U-Q)+(Q-P)` 的逐分量差异账本；右侧每个差先在double
中对原向量相减，避免又引入float32重累加。保存残差并显式报告，不把账本恒等式当作正确性证明。
输出全部参数的原容差比及全体越界集合，另列原9项与最大绝对差位置；不只看L2或选中的坐标。

### FP32节点接口定位（不另建原点图）

仅FP32追加：对`(u,v,d)`分别读取3个能量的raw节点梯度（3次VJP），
再直接读`log10(S)`的节点梯度（1次）；R不依赖节点场，保持独立参数通路。
记录原dtype节点组合 `q_post=sum(seed_j*q_j)`，与native `q_direct`比较。
分别将这两组已detach的节点种子通过**原来的场图**拉回theta（2次VJP），
再加U中已得到的seeded R梯度，保存原加法次序。由节点端与参数端的差异定位
能量→节点接口还是节点→网络/参数接口；共享参数与R汇合仍可能产生浮点差，不把某一桥接向量当真值。
节点比较沿用1e-6/1e-4作描述性读数，不把不同单位/空间的数值大小直接比较，也不据其改变参数准入。

### 真正FP64重放（不等同于上次末端double累加）

将保存的FP32参数、coordinates、浮点history和**全部mapper常量**逐值精确widen到FP64；
load/theta/domain等**原来已经是Tensor的输入**必须取FP32原点实际运行时值再widen，
例如load用原FP32 Tensor的bit pattern，theta用原FP32 `pi/2` Tensor，不得直接用double字面量重建。
若旧bundle没保存这些Tensor，在FP32原点按原构造代码生成一次并保存hex/bytes，FP64只提升这份值。
connectivity/mask仍long/bool；递归处理state_dict中的非Tensor extra_state，不把它误作参数。

Python标量不先偷偷降成FP32：沿用原源码/构造顺序与运行时binary64值。
`MaterialProperties(1.,.3,1.,.01)`的E/nu/w1/l0及实际mat_lmbda、mat_mu，
`PFFModel`的tol_ir/residual_stiffness和实际irrPenalty，先在FP32基线构造时记录type/float.hex，
FP64复用这些相同Python属性，不能改用tensor公式、重新排序或从舍入后的mu/lambda反推材料。
`mat_lmbda=E*nu/(1+nu)/(1-2*nu)`、`mat_mu=E/(1+nu)/2`的Python求值顺序保留。
Q4的Python `1/sqrt(3)`、shape/dN列表以及ln(10)、lambda、map support/coeff等，
记录实际标量来源与binary64值，两个dtype沿用同一Python运算顺序；按原源码在Tensor操作入口
转到各自dtype。FP64的Q4张量/几何重算与Tensor算术属于精度对照，不将保存FP32输入重新解释成更精确的十进制数据。
Q4几何、所有网络层、field、energy、R与上述全部D/P/N/M/U/Q反传均为FP64；
不只把loss或最后梯度转double。释放FP32图后才建立FP64图，禁止autocast。

尤其**不能重新计算raw_reference或anchor_raw来把FP64重新锚定成d0**：那会换函数。
FP64保留保存的raw_reference、anchor_raw、initial_damage不变再widen，故输出可能相对FP32轻微偏移；
保存u/v/d、每项能量、Eh激活及其梯度、位移BC/裂纹线和所有分支变化。
网络ReLU的`coeff*x`、damage map在±2处的piecewise region、volumetric split及penalty均记分支mask；
明确连续但导数不同的kink与relu-square在0导数连续的情况。跨dtype有效分支不同则不能将FP64变化
单独解释成同一局部Jacobian的归约误差，标记branch-sensitive/mixed；不自动冻结分支或换函数。
不得将FP64中Eh很小但非零的结果强制归零，也不得借此开beta25对照。

### 两个事先指定方向的局部分支差分（不是原全局函数差分）

普通中心FD会跨越C-origin的damage map折点，混合两侧.25/.001斜率，无法检验代码
在±2选中的中心导数。FP64保留raw_reference后原点是否仍在折点必须实测，不能预先假定。
因此固定12次差分事前全部指定为**FP64原点实际分支的局部延拓shadow objective**，
只核验该点所选计算程序的导数，不称原全局分段目标已获FD验证。

只在FP64，方向固定为单位参数坐标 e_i：
H3.weight[1,386]（global483186）与 H1.weight[112,95]（global206495），均zero-based。
前者是最严重原越界，后者是最大绝对差但未越界；不代表全网络独立验证。
从同一次native FP64原点forward保存的操作数，冻结全部非光滑原语实际分支：
网络ReLU依据`coeff*x>0`（在0选inactive、斜率0）；map `>2/<-2`为tail，±2属center、斜率.25；
volumetric split与penalty的ReLU也冻结，再保留原平方/后续算术；hard-line/BC mask原样保持。
其他不存在的非光滑分支不得默默遗漏，实施时先按实际source做原语清单。

每个原语在**已保存的原点操作数**上只做标量/逐元素代数检查，验证native与local extension
的值及源码选定斜率相同；ReLU-square在0的导数均0，map折点按实际中心分支。
这些不调用NN forward、autograd或新VJP；保存不相同的全部位置并停止FD，不借改mask修正结果。
共享的平滑操作和连接关系保持源码顺序，只有布尔branch selector冻结；影子计算不得重锚mapper。
原始native D/P/N/M/U/Q及跨dtype分支监测始终保留，不被shadow替代。

在隔离的功能性参数副本上求中心差分，原点参数/mapper/history绝不原地扰动：
`[L_local(theta+h e_i)-L_local(theta-h e_i)]/(2h)`，
h固定为 `{2^-20,2^-24,2^-28}*max(1,abs(theta_i))`，不根据结果换步长或方向。
共12次forward，不构图/反传；每次复用冻结的FP64原点branch masks和mapper常量，
记录实际正负扰动、L_local、BC/line，以及扰动操作数若用native selector会跨分支的计数。
跨分支不重新选择mask；这是局部延拓定义，不能拿shadow的离点值充作全局目标值。

将FD与native D64、P64的该分量都按**原**`1e-6+1e-4*abs(D64_i)`比较，报告三档原始值。
最小两档均满足且原语值/斜率对应已验证，才称这两个方向获得局部程序数值差分支持。
消减导致不稳定、shadow语义不一致或未完成则记不可判，不自动加方向/步长。
这一对照独立于autograd反传，但仍共用平滑forward与选定分支；不是独立物理能量实现，
也不能排除两个方向以外的bug。跨dtype非光滑分支改变仍须单列，不被局部FD成功覆盖。

## 调用数、资源与停止（拟议上限，不是执行授权）

单卡Taobo，最多60秒（外部TERM55s+KILL5s）、allocator22GiB；不承诺FP64/FD一定能在预算内完成。
FP32最多22次reverse调用：raw4×2 + D2 + N1 + M1 + U4 + node4 + pullback2。
FP64最多12次：raw4 + D2 + N1 + M1 + U4。总reverse≤34；原点forward2、FD forward12，总forward≤14。
N也计为一次reverse；Q与账本只做保存向量算术；branch监测不得额外forward。
顺序：核验身份→FP32所有比较/重复与节点定位→释放图→FP64比较→两方向FD→写terminal。
预算临近即停止并保留前缀，不跳过失败项、不转CPU补跑、不扩大时间、加臂或自动重试。

建议预留的唯一Run名称 `pf_s04e011_grad_arithmetic_20261018_v1`，尚未创建或启动。
新路径只能在 `/mnt/data2/drtao/wennie/<Run>/` 与 `/mnt/data2/drtao/pidl_archives/<Run>/`。
运行前按项目协议查共享GPU进程/利用率/显存和存储，显式GPU编号；资源不合适就不启动。
TF32/matmul精度、deterministic flags、CUDA/cuBLAS/PyTorch/GPU型号全部记录并保持同一FP32设置；
不得为使对照通过暗改这些设置。若原设置无法从旧receipt还原，记录缺口并在Code Ready前明确，不能声称exact replay。

身份/布局/冻结状态错误、非finite、log域错误、OOM、时间/调用上限即停；
首个FP32重建必须d==d0、能量逐值复现旧值（Eel=.0006000853609293699、Ed=.005059129558503628、Eh=0）。
若能量/初场不复现则停止，记“基线状态或数值设置未复现”，不进行精度归因；
输入hash相同也可能因backend/算术设置而能量不同，不能仅凭这个条件宣判输入身份错误。原梯度是否逐位复现另记，不把CUDA重复性当作输入身份。
如果FP32 P/D原容差失败不复现，仍完成同图首尾重复并记录，后续归因不作“旧故障已解释”的结论。
参数、mapper、history前后逐值相等，优化更新/history提交/FEM求解均必须0；
FD正负副本单列为预定函数评估，不是优化或被接受端点。

## 事前结果判读（不改变原检查）

| 观测 | 可支持的判断 | 下一项 |
|---|---|---|
| 布局/漏项/系数语义/状态不一致得到可复现实例 | 具体实现/构造问题；标明首个坏接口 | 只修该点，另行审查；原失败保留 |
| FP32同图D或P重复读数跨原容差变化 | 存在执行/归约重复性问题；尚不能归因为固定求和次序 | 保留各向量，不追加重复或直接放宽 |
| FP32原失败复现，桥接能定位改变次序的具体接口；FP64全参数P/D及桥接均满足原容差，两个局部FD方向支持，跨dtype非光滑分支可比且无语义缺陷 | 在所查快照/路径上支持浮点算术路径解释；不是证明整个实现无bug | 汇报每段贡献、剩余不确定性；训练仍关闭 |
| FP64仍超原容差，或已验证原语对应的local FD与两条autograd路径稳定不符 | 实现/反传问题仍待查；单独FP64失败不足以证明bug | 定位首个接口，不引入新的物理/优化因素 |
| mixed/branch-sensitive、不能复现旧失败、超时、缺数据或FD不可判 | inconclusive，写清已排除/未排除项 | 只提出下一项最小区分，不自动执行 |

三种解释允许共存；不得强行把数值和实现二选一，也不得仅凭FP64通过宣布“只是浮点”。
原FP32 `allclose`结果始终单列，任何shadow/FP64/FD成功都不改写旧失败或自动开放W0/W25。

## 最小证据与实施前检查

原件manifest、源码commit/dirty状态、全部命令/设备/时间/调用计数和退出receipt；
FP32/64参数layout、freeze hashes、native/manual seeds、完整P/D/N/M/U/Q与重复向量、
FP32节点及pullback向量、origin字段/能量、branch mask（可bitpack）与差异索引、FD所有原始读数。
按阶段立即落盘，不在最后一个断言后才保存。标注任何缺失；超时的missing不是通过。
图只需一张：接口差异/原容差比并列FP32/64，附原9坐标和两方向local-FD步长曲线；
零线和原容差边界明确，解释branch与重复性，不画训练收益。raw留归档，git存compact摘要和脚本。

后续独立runner需静态审查保证无optimizer/train/history入口，并以小型共享参数图验证
native-seed与postscale的区分、参数布局和故意漏项能被发现；只做CPU轻量单测。
再审查实际上传包、输入hash与55+5秒launcher，之后才可能申请该准确版本的执行授权。
本设计未冻结未来源码commit，当前状态只可能为DESIGN_REVIEWED，绝非CODE_READY。

## 独立审核修订记录

v1 `e13223c6` 经独立只读Codex设计审核为MODIFY_AND_REREVIEW：
将普通全局FD替换为上述明确的局部分支延拓；补齐原运行时Tensor提升和Python标量的来源/转换规则。
同时明确能量不复现不单独证明输入身份错误。调用上限34 reverse /14 forward保持不变；
局部原语核验不得暗增NN forward或VJP。v2已获焦点复审REVIEW_PASS_SCOPED_TO_DESIGN，绑定`1c02fff598298d3891557677fb51dc01f9896837`；
没有剩余设计阻碍。仍未实施或执行，不能升级为Code Ready、根因确认或运行许可。

## 收口补充：复用并行owner新证据，不安排重复执行

方案复审后收到总部同步，并直接读取原对话 `PIDL 上翘诊断与改善：完整物理场`
（thread `01a14bbc-c8fd-7bd2-85fe-e0d6cbadc85d`）的人方指令与最新记录，
以及其本地已保存控制结果、代码和证据复核receipt。该对话另有明确的
“查清修好9项、复审后原W0/W25各200步”授权；该授权不用于本对话启动任何工作。

已有控制Run `pf_s04e011_wgradfix_8edc762_20261018T210153Z`，源代码
`8edc762a99bacfa6825ed413a148fbcccd09a921`，在同一原点、float32、原1e-6/1e-4下：

| 已存在对照 | 越界数 | 与本设计的关系 |
|---|---:|---|
| 原参数梯度末端缩放相加 | 9 | 重现P；raw分项和direct均报告与原件逐位一致 |
| 提前缩放但分别反传 | 12 | 已覆盖“仅移动乘法位置不足以闭合”的U类控制 |
| 手算独立链式系数、一次联合VJP | 0，逐位相等 | 已覆盖M类核心，不能再把这一问题当作完全未知 |
| 真实输出adjoint统一网络VJP | 0，逐位相等 | 已有网络共享反传路径定位，不是独立系数参考 |
| H3固定X/adjoints的局部仿射顺序对照 | FP32为4，局部FP64为0 | 支持局部归约精度解释；不是完整网络FP64重放 |

这份已有证据及其独立复核支持：所复现9项与共享网络中分别/联合反传的float32
加权和汇合顺序有关；没有把训练loss、梯度、优化器或容差改成另一个值。
这不等于全实现无bug，也不替代完整高精度梯度oracle。
本对话只读取已保存的compact控制和源码，**没有重新计算GPU/模型或独立重开全向量**。
已有复核也明确其独立核对范围为原9项数值/代码和producer摘要，不能写成重算全部新向量。

来源：[已有修复与证据说明](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/S04-E011/runs/weight_gradient_fix_20261018.md)、
[控制结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/S04-E011/runs/weight_gradient_arithmetic_controls_20261018.json)、
[证据复核](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/pidl-weight-gradient-fix-20261018/docs/research/S04/S04-E011/runs/weight_gradient_fix_evidence_review_20261018.json)。

**当前处置改为reuse/defer**：上述v2是已经通过设计审核的补充方案，不实施、不排队、不另建producer。
它额外能检验完整FP64模型/能量/链式路径（已有64仅局部GEMM），
原运行时标量提升、跨dtype非光滑分支变化，以及两坐标局部程序导数。
只有这些剩余问题被明确列为新的决策瓶颈，才考虑另行实现/Code Ready/准确版本执行授权；
不因补充设计已通过就重复现有控制或延迟原owner的取回核验。

原owner报告pair Run `pf_s04e011_wpair_fix_8edc762_20261018T210743Z` 已各200步完成，
正在核验场数组；本对话未重算或确认其FEM误差，不新增场结论。
两臂产物和场误差由该执行owner保持唯一所有权，HQ取回判断。本对话没有启动两臂。
因此上文“训练关闭/未启动”均指本对话的准备权限及本设计，不能改写另一对话的授权执行事实。
