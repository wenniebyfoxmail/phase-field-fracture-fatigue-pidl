---
storyline_id: S04
scope: independent_method_and_input_review
date: 2026-10-12
status: hold_waiting_for_g5_owner_data_lock
execution_owner: source_dialogue_01a1131d-017c-7b03-a95a-ad73ba8fcc9c
---

# G5只读复核、配对资产与唯一D0 run card

结论：同意 `HOLD_PAIRED_MODEL_RUN__G5_NOT_FULLY_PASSED`。v10 integrity/availability
通过不释放paired model run。本次复核未执行D0/重算D003、未加载checkpoint tensor、未读取
Windows scientific payload或修改G5文件。方法owner仅写本记录；G5/data-lock由主对话负责。

2026-10-12 coordination update：fresh v10已正常结束且terminal integrity通过；主对话已
明确接管G5/data-lock/D0唯一执行owner。U0.115完整matched PINN尚缺，G5继续HOLD。
本方法对话不启动任何任务，也不修改共享Obsidian。

审核对象：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/docs/research/S04/S04-E016/g5_contract_role_input_audit_20261012.md`
（2026-10-12 HOLD版本）。这是独立方法/metadata review，不是native数值重算或Code Ready PASS。

## U0.115是否有qualified matched PINN trajectory？

**目前没有可登记为qualified matched的PINN U0.115证据。** FEM read-only reuse/reseal
已记录；它仅证明FEM资产可复用。existing PINN export与E013 input lock均只列.11/.12/.13。

| 查询范围 | 结果 | 支持范围 |
|---|---|---|
| 本地 `local_archive/after_strict_setting_alignment/pidl_result/` amplitude目录/文件名 | 精确U0.115/Umax0.115/u0115匹配0 | inspected local matched amplitude资产未找到 |
| 已锁定 PINN export contract、E013 data lock、D003 coverage | 仅.11/.12/.13，264cycles | 不包含.115；不能增加第四fold |
| Taobo三root的amplitude目录，maxdepth4 | SSH成功，host GPUServer8；匹配0 | 命名目录不存在于此bounded查询，不证明全host不存在 |
| 同三root的 `model_settings.txt`，maxdepth6，精确umax=0.115 field | 477份settings；匹配0 | inspected metadata未找到exact-amplitude run |
| 一个0.115字符串候选：monoU02 | umax=0.2，1 physical cycle，24 monotonic displacement substeps | 排除；0.115仅为单调加载的中间载荷 |

Taobo只读查询root：`/mnt/data2/drtao/pidl_archives`、`/mnt/data2/drtao/wennie`、
`/mnt/data2/drtao/projects`。未扫描另一个磁盘、legacy /runs、/pidl-canonical、更深匿名目录或
无settings归档，因此结论是**matched qualification未建立**，不是“所有远程存储绝无此轨迹”。

完整证据路径：

- existing deployment-source contract：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/pidl_peak_trajectories_three_umax_20261007/contract.taobo.json`
- 原data lock：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/research/S04/S04-E013/input_lock.json`
- D003 metadata与来源：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/trajectory_coverage.csv`
  和同目录 `paired_cycle_index.csv`、`receipt.json`。
- FEM reuse审计：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/docs/research/S04/S04-E016/request31_v2_readonly_audit_20261008.md`；
  producer receipt指向 `C:\q4runs\request31_v2_readonly_audit_20261008\u0115_reseal_receipt.json`
  （本次只读文档引用，没有读取Windows）。
- false candidate settings：
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/recovery_monoU02_b6d5610_20260701_141419/raw_archive/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc1_Nstep25_U0.2_recovery_monoU02_b6d5610_current_active_fem_gp_tri3_g_mean_femIrrGP3_hardAlphaRecoverU0_uSeq24_Umax0.2/model_settings.txt`
  （line2 umax0.2，line3 cycles1，line24 substeps24，line25中间载荷0.115，line34 state mapping）。
  同目录 `best_models/checkpoint_step_*.pt`本地只列step0--16（17个），settings预期25steps；
  未证明该copy完整，未deserialise。它们属于这条单调加载序列，不能作为.115循环checkpoint。

查询原样与exit状态见[asset_search_receipt_20261012.md](asset_search_receipt_20261012.md)。
G5 owner若知道其它run registry/path，下一步只核其metadata；匹配后才核settings、checkpoint
coverage、state0、mapping和lineage。无checkpoint不能靠重新训练自动补齐。

## G5需补充的具体字段/分界

HOLD判断正确。进入paired data lock前还需明确以下条款，本文不修改G5 owner记录：

1. **完整PINN与配对PINN区别**：每trajectory记录模型source/commit、settings、state0、
   complete physical-cycle范围、每cycle checkpoint/trained-model存在性、续跑segment边界、
   recovery-offset/substep mapping、both-producer event metadata。不能仅凭103-cycle FEM宣布
   PINN完整，不能把 `checkpoint_step_115`当成Umax0.115。
2. **prediction origin**：当前s4后使用的PINN histories必须确认为s4 post-commit，不能加载
   s5或下cycle的历史；d/current damage与hist_alpha/committed max damage分列。
3. **same support**：逐channel绑定node/GP/cell、quadrature、插值/containment、reduction、
   clipped/raw。FEM ContractB的s4 nodal u/d覆盖本身不证明PINN history GP和raw GP可同支持比较。
4. **资格范围**：producer 7/7不是reference/capture-neutrality/irreversibility独立PASS。
   G5若只允许processed/native-archive imitation，D0/model card必须继承该role，不能推广teacher。
5. **normalizer分工**：input/driver-transform scales只fit outer-training PINN；Delta的target
   scaling可来自outer-training labels但必须冻结并inverse，绝不访问confirmation。不能在inner
   validation中用outer-fit全部数据重新算feature stats；每inner fit也独立标准化。
6. **event信息隔离**：common-pre-event只能由G5 owner作为retrospective admissibility/scoring
   mask提供，不能形成feature、cycle/lifetime归一化或inference stopping signal。未来event形成
   strata只可评分；训练strata固定C1--20/C21--40/C41+。未来missing不是padding来源。
7. **heldout schema与数值区别**：确认集schema/coverage可由owner返回booleans；其scientific
   values、event-normalized profiles、feature stats、scores保持关闭。C0缺失使用显式mask，不伪造
   unloaded/history值。float32 export identity/replay的容差与native residual tolerance分开。

## native-support与reduced-head选择修正

**最小D0选择“同状态s4、reduced cell fields直接Delta”路线。** 前提是G5 owner逐channel确认
双方同s4时刻及同cell reduction；现有A-summary不得直接充当B-target。减少新GP管线依赖，
也避免把同一个cycle标签当成同一个state。

- direct primary-channel candidates仍为reduced `d/alpha_bar/raw psi`；它们都是对应声明输出
  的监督字段，目标为FEM−PINN；不声称三者是独立物理状态。
- 如果希望纠正 `mean f`，可在D0用**额外直接reduced f head**做监督诊断；它是同源相关的
  auxiliary output，单列report，不重复算作独立primary或强制 `f(mean alpha)`。
- exact active需same-state native joint support：d、raw psi和声明driver实际需要的其它
  parents在同一GP/已锁定quadrature mapping上共同可用，先按定义计算再mean；只有reduced parents时，
  approximation单列，或用qualified exported mean-active作为另一个direct auxiliary target。
  不用mean-parent乘积伪称native active，也不默认加入multiplicative f。
- `H`若无matched历史support，保持missing；不由alpha_bar或单个current raw推断。
- native-GP exact-derived heads保留为**另一条后续路线**：只有PINN/FEM primitive支持一致、
  GP evaluator和reduction都锁定时才采用。Nodal damage本身不足以恢复GP疲劳history。

该选择修正旧方案对reduced字段派生heads的依赖；它不替G5批准任何数据。

## 部署输入只读审核结论

proposal-v1的**声明输入**可以是因果PINN-only：coords/mesh、已知loading/Umax/cycle、
当前PINN和两个过去cycles、PINN global summaries/geometry neighbors。当前尚无实现的
direct-feature pipeline，因此结论为 `POLICY_COMPATIBLE_IMPLEMENTATION_NOT_REVIEWED`。

D003中Delta相关性、FEM max/error、top-error区、first-event和future-window终点全是
标签/诊断信息，不能从其CSV拼入X。D0不以“这些columns已存在”为授权。以下feature直接禁止：
FEM event/tau、FEM support/top-error location、FEM residual/coefficient、future PINN、
任何confirmation statistic。PINN-only q99 foreground mask可以因果计算，但不可冒充FEM support。

## 最小D0 run card（只形成，当前不执行）

| 项 | 固定内容 |
|---|---|
| Single decision | 在获批同状态s4 reduced data上，直接场输入与历史的闭式baseline是否显示可审计增益，从而定位下一模型/数据需求 |
| Activation | G5 owner显式提供verdict、逐字段data lock、admitted development IDs与唯一执行owner；当前HOLD |
| Input unit / origin | 完整Umax轨迹分组；每完整cycle field；s4 post-commit；horizon0 |
| Data | 仅获批development；.115只有qualified PINN counterpart后进入；.1175/.125完全排除 |
| Reuse | 原D003表/图原样复用；不重算旧POD/ridge或264cycle差异表 |
| Arms | B0 Delta0；B1直接多输出closed-form ridge；不NN、不PCGrad、无optimizer loop |
| B1 inputs | 同cycle PINN reduced d/alpha_bar/f/raw/declared active proxy，c-1/c-2与missing masks，coords/area/load/Umax/cycle，PINN-only globals与geometry-neighbor means |
| Labels | matched physicalDelta及事先固定transformDelta；reduced f如admitted可作auxiliary，H不补造 |
| Sampling | 每training trajectory全部admitted cycles；固定geometry/area-based最多2048cells/cycle用于fit；不按FEM support筛选；heldout评分用全部contained cells |
| Split/selection | Leave-one-complete-development-Umax-out；ridge alpha[1e-2,1,1e2]仅inner whole-trajectory选择；standardizers只fit当前inner/outer training |
| Loss weighting | trajectory等权；fixed physical-cycle strata等权；area weights；各通道training-scale归一化；zero denominator或missing channel明确unidentified |
| Primary outcome | Diagnostic，逐fold/stratum/channel B1/B0 error ratio；不把旧<0.90借作scientific PASS、不用Ridge miss证明NN无效 |
| Metrics | reduced physical error+预声明history/raw transform error；最差通道、early/background、mapping/floor、cost；f辅助、不重复投票 |
| Budget | Mac闭式light analysis <=5min、<=2GiB RAM、<=100MiB outputs；达到cap停止，不转GPU/新训练 |
| Stop | 缺qualified配对轴/同状态/锁定语义先stop；identity/finite/leakage失败inadmissible；不偷偷退回旧3轨迹重跑 |
| Evidence | input review、metadata/role lock、唯一receipt、closed-form fit selection表、perfold/percycle表、按预声明规则的对比图 |
| Runner status | 尚无该D0实现/Code Ready review；现有audit_direct_delta_cycles.py是D003描述脚本，不是B1 runner，不能当作D0命令执行 |

closed-form B1仅作为同信息最简comparator。NN是否值得测试结合新增信息/独立轴与measured
bottleneck决定，不再采用“任何ridge fail就关闭NN”的旧先验。

唯一执行owner已明确为**主对话 `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`**，其掌握
G5/data lock与资产角色，并已确认接管。本方法对话只提供设计/run card与review。
D0仍须等待G5通过、data lock与runner/protocol审查；U0.115缺配对不被假定为完整。
