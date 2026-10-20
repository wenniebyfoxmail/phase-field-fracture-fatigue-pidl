# 完整比较的精确准备与审批边界

2026-10-20；继续现有hybrid owner/D12。用户授权本地准备和独立审核，要求准确版本与预算送审；本轮不执行SSH、FEM或训练。隔离分支 `codex/fem-surrogate-comparison-prep-20261020`，基点 `829508617534c6c5febc813899498a31053684df`。原source/solver/worker/launcher不改字节，只增加准备和只读环境inventory工具及本文。

## 要解决的问题

先产出相同约束和历史合同下的连续数值轨迹，再检验冻结网络damage初猜是否在相同质量下，比前态和经典外推初猜减少总在线时间。现有局部收敛状态只用于既有回放，不能拼成疲劳teacher。数值参考不是物理真值。

## 完整比较内容

| 部分 | 精确工作 | 阶段上限 |
|---|---|---|
| 绘图依赖、原生回放、最终分析 | 原生五态回放，最终封存场/轨迹评分；依赖仅常量三角形Agg/PNG/PDF | 合计共用4 hosth，绘图首阶段120秒含45秒清理储备 |
| train_A/train_B/validation | 幅值系数.8/1.2/1.0，各120周期×5子步=600；独立初态、各自接受历史 | 各20 hosth，共60 hosth |
| 一次fit | 1200训练转移、600验证转移；4×64图网络；原loss/seed/20000更新/early-stop | 最多6 GPUh，一次fit |
| test_reference/test_classical | 幅值.9，各600子步；相同问题和数值求解器 | 各20 hosth，共40 hosth |
| test_hybrid | 幅值.9，冻结NN初猜＋共同约束校正，自身历史600子步 | 最多6 GPUh |

合计3600个数值子步；GPU阶段12小时内分6/6，不与CPU开销相加冒充核心小时。总host墙钟上限136小时，≤16核，所以分配上界2176 coreh；phase上限合计116小时，不能用136小时补超某个phase。单物理子步120秒、首停不重试；原数值容差、节点域、Anderson和历史一次提交全部不变。

已知旧工作617.3239415297285墙钟秒、572.315113 CPU秒、GPU0，均保留在原prior_costs；因此新包前剩余135.82852112735284 hosth、12 GPUh，不能重置账本。后续环境inventory及控制开销也应记入同一预算。RAM64GiB；GPU显存上限24GiB，实机容量与空闲须另查，不误设大于设备物理容量的最低空闲要求；主输出128GiB＋归档128GiB，启动须有256GiB可用。以上是资源上限，尚无完整轨迹实测耗时预测。

三个测试臂完全共享全空间机械/约束damage/受保护Anderson/热初始化及缓存/数值精度，只改变damage初猜。最后同场力学、damage KKT、节点不可逆与疲劳一致后一次提交；测试臂自身历史推进，不在线使用参考场。原卡的质量、f<1覆盖及相对两个强基线的10%完整在线时间条件均保留；单次匹配比较不声称统计显著性。未到达的场图状态明确缺失。

## 当前已完成和真正缺项

本地已可构建：既有61文件闭包＋其来源manifest＋本次准备工具/文档/测试；7个原生输入文件逐字节复核，约89MB，未np.load或读取科学数组值；新建议Run ID为 `pf_hybrid_complete_20261020_r2`，旧r1不复用。实际source commit、代码artifact、待激活卡SHA和包字节数在本地build_receipt.json，以独立复审的实际版本为准。

**完整启动仍缺生产端Matplotlib确切版本。** 旧卡/旧独立审查明确要求：一次获准的实际环境确认 → exact pin → 差量复审 → 人方对准确执行版本审批 → 科学阶段。旧卡值为null，本地3.9.2仅开发证据，不能代填。本次待激活卡实例化了完整phase、建议fresh路径和预算，但 `execution_enabled=false`、Matplotlib null；它不是可直接启动的完整科学审批卡。当前GPU空闲、CPU容量、旧deps目录及网络可达也未核验，历史记录不代替实时准入。

## 仅请求审批的准确前置动作

对象：`drtao@172.16.100.2`，预期hostname `GPUServer8`；不转到其他机器。读取 `/usr/bin/python3` 版本及numpy/scipy/torch/osqp/h5py/psutil/matplotlib的distribution metadata，并给出来源路径。检索路径含旧自有 `/mnt/data2/drtao/wennie/pf_hybrid_full_20261019_r1/deps`，仅用于识别既有run-local依赖；不修改或删除旧运行目录。

准确payload为 `tools/hybrid_runtime_inventory.py`，通过SSH stdin交给isolated Python执行，不在远端落地脚本；命令和payload SHA载于runtime_inventory_request.json。该脚本只使用Python标准库和distribution metadata，不import科学包、不读项目状态/模型、不渲染、不安装、不创建目录、不查询/占用GPU。1CPU；RLIMIT_CPU10秒、地址空间256MiB；远端GNU timeout20秒＋最多3秒kill储备；本地单次SSH最多45秒，连接10秒/1次；失败立即保存结果，不重连、不改机、不安装。

默认工具仅显示请求。将来获准后唯一命令形如：

```text
python tools/request_hybrid_runtime_inventory.py --request <reviewed runtime_inventory_request.json> --output <fresh local receipt.json> --execute
```

`<...>` 在送审包APPROVAL.md中替换为准确绝对路径；该示意不是执行授权。该前置动作最多传输一份已审核的标准库脚本，不发送项目数据。结果只写本地收据；这是环境观察，不是运行时import/render/科学准入通过。

成功后由实际收据固定Matplotlib exact版本、核对原六依赖版本/来源，并解决新run的隔离依赖来源（旧OSQP不能假定已系统安装）；计入本次inventory实际费用，重建新精确卡/包并独立差量复审后，再展示最终启动审批版本。任一版本/身份/路径缺失即返回，不选择新pin碰运气、不安装、不跳过原Agg检查。

## loading/property补充

不同loading的第一版已覆盖幅值，但未覆盖变幅/载荷比/方向或材料变化。多材料模型当前明确不支持：FrozenGraphInterface绑定单一physics_id，state0与backend identity同绑，准备器固定材料。不能只在JSON添加case后声称泛化。

另附[loading/property扩展设计](loading_property_extension.md)，它是供选择的后续设计，不混入本轮3600步、一次fit或12GPUh，也不自动生成数据。扩展需要新的协议、材料族准入与归一化、每材料state0身份、完整轨迹划分及尺度复核；本次尚未实现/审核其runner。

## 本地再现与独立审查

从干净准确提交运行 `tools/prepare_hybrid_comparison.py --inputs-root <retained inputs_v2> --out <fresh local archive>`。builder只做文件哈希、metadata读取和本地复制打包，不import科学模块；拒绝不同既有source/input、dirty依赖和覆盖已有目录。包不自动复制旧deps或执行任何远端动作。

人工测试、独立现状审计与最终准备包审查分别记录：算法原61文件复用审查不因为新文档重复；本次新工具做精确差量审查。最后复审应区分“准备包/只读inventory动作通过”与“完整producer启动被runtime pin阻断”，不得用一个笼统PASS掩盖后者。
