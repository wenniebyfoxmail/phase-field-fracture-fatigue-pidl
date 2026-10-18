# S04-E027 本地准备与独立代码审查交接

> 最新状态（2026-10-18）：用户批准的原trained98单文件只读核验/取回完成，自身大小与SHA256远近一致、已补data_lock；见本文末节和initializer_retrieval_20261018.json。下列未找到/无SSH/lock未改等是此前时点的历史记录。源码未改，资源预检与训练仍未进行。

2026-10-18；Owner chat `01a14bc7-fd2a-73e1-9d0f-de457ba1dcc0`；HQ chat `01a14bb9-6cd1-7ee2-9647-5190d786f7ba`。用户授权范围是本地接口、三臂代码、必要检查及独立审查；先不启动训练。报告在本对话/本地归档供HQ读取，没有另行发送消息。

**结论：代码准备范围通过独立审查，无剩余已知阻断性代码问题；完整 Code Ready / Run Ready 未签，运行未授权、未执行。**

## 绑定对象

- 最终审查源码快照：`91537ce240d892fc71f714cceedc1cea92c32b1b`，审查时工作区干净；其后仅追加本审查记录与结论，不改算法、runner、config、lock或protocol。
- Worktree：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/fem-synthetic-augmentation-design-20261017`；branch `codex/fem-synthetic-augmentation-design-20261017`。本地commit保存，未push。
- Runner：`SENS_tensile/run_s04_e027.py`；module：`source/s04_e027.py`；tests：`tests/test_s04_e027.py`。
- Protocol：`S04-E027/v1-source-faithful-P-20261018`；`experiment.md`及`data_lock.json`；旧Pro为方案审查，不替代此次代码审查。
- 独立审查者：本任务只读子代理 `/root/e027_independent_review`；主代理实现，审查者未修改源码。审查结果由子代理工具回传保存在本对话。

## 历史复用结论

此前已做过MIT-8 raw驱动warm-up/release、Path C局部damage监督、四字段直接强制和FEM-mesh预训练；不能称本次为首次FEM增强PIDL。Path C旧scorecard有组件收益，不能把所有旧监督归为失败。此次保留数据锚点、原生Q4固定完整前态、同一监督前缀后完整Adam/RNG分叉；定向检索未发现完全相同的三臂。具体出处及旧结果边界见`../fem_supervision_reuse_audit_20261018.md`。

源码核查纠正旧计划P臂转录：真实P是正能量log10加named-weight L2，PIDL gamma16875，而非原始能量或FEM gamma421875；修订写入E027且经独立核对。

## 审查轮次与修复

1. `c0113d565799f08e91be721f8019edb8d6767d9c`：核心接口及算法限定通过；三项P2为缺少分量/梯度与统一指标轨迹、逐段实际资源成本、图说明。独立13 tests及四MAT重放通过。
2. `12d96d14d211078c2efaecb6aba7c6da0b5c7136`：三项修复有效，独立14 tests通过；新增P2为跨臂LP诊断将P专用正能量限制传播到S/C。
3. `91537ce240d892fc71f714cceedc1cea92c32b1b`：保存能量，非正时辅助LP/其梯度NA，P实际目标不改；独立15 tests通过，代码准备范围通过。

已检查：来源一致的P目标、native Q4力/能量、C对damage的梯度、共享前缀完整参数/Adam/RNG复制、质量概率采样不重复加权、四文件身份与前态时序、参考trial history、禁止Mac/未知initializer执行、分量与独立诊断RNG、固定0/1000/1500、四段资源归属、图与评分输出来源、失败/预算保护。静态审查不能替代实际GPU图执行、资源成本验证或结果图视觉检查。

## 已完成的非训练证据

15个轻量测试、py_compile、git diff --check通过。四MAT已有参考重放：force maxabs差`8.605431227630064e-17`，free force norm`3.776120766585009e-15`，raw scaled差`3.020017395882757e-12`，trial-history scaled差`1.7239217865727685e-12`，BC误差0。摘要`nontraining_checks.json`；原收据在项目`local_archive/experiments/S04-E027/preparation_20261018/reference_check_final.json`。

**optimizer.step=0；训练循环进入=0；history commit=0；FEM solve=0；远程访问=0；initializer payload读取=0；新留出读取=0。** 没有新模型性能结果，不生成替代真实结果的图。源码中的未来执行路径未实际调用。额度检查各阶段均剩余81%，未使用reset/credit。

## 交HQ的下一步决定

初始化仅有原producer archive路径，当前无本地文件和精确字节身份，lock明确null；执行入口在数据/GPU/优化器前强制停止，禁止随机/其它checkpoint/旧UV头替代。应先由HQ安排准确权重的身份与可用性核实；任何lock更改须重新绑定审查。

随后由HQ统一决定是否批准指定producer的no-step三图预检和执行；需新Run、exact source、人工授权、完整资源/输出卡。预检P/S/C各100次forward/backward、无optimizer更新；实际成本和CUDA峰值当前未知。拟合总上限仍2 GPU小时/32GiB host/2GiB输出，超限停止，不自动换机/扩容/重试。若运行，完整Code Ready/Run Ready记录、真实图检查和独立证据审查仍须补齐；代码准备通过不授予科学结论或运行许可。

## 2026-10-18 初始化身份补查的额度停止记录

总部要求仅用本地源码/记录/清单补齐initializer身份，不训练、不远程。开场额度核对显示Codex used24%、remaining76%，低于此前80%工作下限；本轮不开始进一步定位阶段，仅保存当前可核实状态。现有`data_lock.json`仍指向唯一的原producer `pf_s04e011_pidl_pair_ad749c8_20261008T0912Z` 下、`s04e011_q4_production_ad749c8_current_active_native_q4_gp4_femIrrGP4_hardAlphaRecoverU0`分支的`best_models/trained_1NN_98.pt`（完整路径保存在lock），producer commit `ad749c8bbba8120b3961add989b11427fab86254`；sha256和bytes仍为null。本轮没有重新核实本地文件是否出现、产生状态/序号语义或字段容器身份，不能把旧“未找到”当作本轮穷尽搜索结果。

具体未闭合对象仍是该单一checkpoint本体或能唯一绑定它的既有本地manifest条目；恢复本地补查后，最小动作是先从其原运行contract/保存源码/归档清单核实98对应状态、序列化字段与已有hash/size及本地映射。若确无对应本体或清单，需由总部安排仅该确切文件的身份/可用性补齐，不接受同名其它运行、随机初始化或替代权重。此处是待办，不代表已经定位或授权取回；无初始化设计变更。此前15项检查和91537ce2独立代码审查结果保持，未重复审核，代码/lock未改，未新增数据或科学结果。

## 2026-10-18 初始化身份补查完成（仅本地元数据与源码）

总部后续指令澄清旧总部停止条件已取消，本轮继续完成本地核查；上一节76%停止保留为历史动作记录，不再作为当前停止依据。当前未闭合项是下述文件身份/可用性。

**已确认运行/状态/字段语义，未确认权重字节身份；无需更改初始化设计。** 结构化核查在`initializer_identity_20261018.json`，不改runner、data_lock、协议或三臂条件；保留15项检查和91537ce2代码审查，未重复全套审核。

- 唯一运行是`pf_s04e011_pidl_pair_ad749c8_20261008T0912Z`的native Q4/GP4 coordinate-MLP臂，producer commit `ad749c8bbba8120b3961add989b11427fab86254`。精确期望路径仍是data_lock的`initializer.producer_path`，未选择新文件。
- 本地原运行`model_settings.txt`与旧contract中的3799 bytes、SHA256 `7c7469b895f3e95eb5d45a86d861dce25e08ef33f29e5b205ba8267f34a99597`一致。恢复偏移1、每周期5步，故j=98对应c20s3、U=.08999988；c20s4目标j=99、U=.11999988。目标文件应是j98训练步结束时的网络参数，绝非初始U0恢复态、c20s4标签或共享paired-initial-state。
- 原producer保存源码`source/model_train.py:2837-2838`是`torch.save(field_comp.net.state_dict(), trained_1NN_{j}.pt)`。其git blob与旧contract的155527 bytes、SHA256 `975edbcc506cd0cdad8e6881f9be7384b13a38a3092284681c8ba9d123e49d9f`一致；network、construct_model、runner三个blob也逐一匹配旧manifest。预期是裸state_dict而非network_state_dict包装；8×400、2输入/3输出TrainableReLU，共26参数键、1125211标量。源码输出顺序raw u/v/damage，输入物理x/y；实际payload键、shape、dtype未读取，不能冒称已验。
- `checkpoint_step_98.pt`另存hist_alpha、hist_fat、psi_plus_prev等历史/mesh元数据，**没有网络参数**；更不是RPROP恢复文件。其旧manifest大小4497675、SHA256 `a0efb95da644236dcbefbe729990e607a7f4198d63b48603ee3bb1e0fddb4264`不能移给trained文件。原Q4/T3共同初始态的`e400cb...`也不是c20s3网络的哈希。

**纠正之前身份措辞：** 原计划称“trained98已由NCP contract/receipt绑定”过强。四份已存contract列出的是model97、model99及history98；原NCP reader只读s2/s4网络（c20为97/99），history98用于s4前态。它们不含trained98条目。本地可复原其唯一期望位置和源码语义，但没有该网络文件自身的已有哈希/大小，不能由邻文件推算，也不能宣称远端不存在。

本轮仅用`rg --files -uuu`检查项目根、Downloads、Documents的文件名清单：同名trained98/history98共121项，无原运行名/`s04e011_q4_production_ad749c8`匹配。没有打开这些其它同名权重；没有检查压缩包成员、其它卷或producer当前目录，因此“未找到”严格限于上述范围。已扫描E011已有manifest/contract/receipt文本，同样没有目标network98的条目。

三臂共同条件保持：P/S从同一个network98复制所有参数、各建空Adam与seed1采样；C在S1000时复制全部参数、非空Adam和采样RNG；不继承原RPROP，也不重新运行C前缀。共同应用目标U=.11999988，前态/历史仍来自原四MAT中的FEM输入，绝不由PIDL history98覆盖。

**只缺这一具体对象：** 原运行精确`best_models/trained_1NN_98.pt`网络文件及它自身的size/SHA256/可用映射。最小补齐动作是由总部安排对该唯一producer路径只读核验存在性与身份，存在时仅取回该文件及收据；无需其它checkpoint、新状态数组、计算图预检或训练。若文件实际缺失或不能归属，则停止此初始化准备，将任何替代设计单独交用户决定。本轮没有远程操作、checkpoint payload读取、模型实例化/替代初始化、新科学数组/留出、训练或FEM。

## 2026-10-18 原文件只读核验与取回完成

用户本轮明确批准只读核验原producer该确切trained98，存在则取回及其自身大小/SHA；不换权重、不做资源预检或训练。已在GPUServer8核验原唯一路径是常规文件且无路径跳转，hash前后inode/大小/mtime/ctime一致；单文件SCP取回后Mac重算大小/SHA相同，已设本地只读。

- 文件：原Q4运行`best_models/trained_1NN_98.pt`，路径/producer commit保持原定义；没有替代权重。
- 大小：**4510197 bytes**；SHA256：`e0acd981b8c6d69be9b88d676088b8a026448ee24f28ec231ecdd5c266edd69f`。
- 本地：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E027/initializer_retrieval_20261018T121735823711Z/trained_1NN_98.pt`。
- 紧凑收据：`initializer_retrieval_20261018.json`；原SSH/传输命令与stat收据：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E027/initializer_retrieval_20261018T121735823711Z/receipt.json`。

`data_lock.json`只补initializer的自身bytes/SHA、本地路径、producer hostname和核验状态；四MAT身份、protocol、producer路径/commit以及代码完全不改。此前“本地未发现/未知哈希”的状态由此次真实收据更新，先前过程记录保留。15项测试和91537ce2源码独审是历史有效验证，不重复整套测试，也不把旧审查冒充新data-lock快照审核。

初始化**字节身份和本地可用性已齐**。未反序列化模型，因此实际state_dict键/shape/dtype尚未检查；此前c20s3/裸state_dict语义仍明确是原源码/记录推导。未加载科学状态数组或留出，未改变初始化设计/参数，未启动GPU资源探测、计算图、训练或FEM。下一步只将更新后的lock交总部结合既有代码审查统一决定；本次单文件授权不包含资源预检或执行授权。
