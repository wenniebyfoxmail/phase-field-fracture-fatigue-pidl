> 当前任务入口：[一次授权下的自动机械检查与授权边界](../complete_execution_20261020/current_entry.md)。本文及v2审批链保留历史版本；逐项管理审批要求由该前瞻修订承接，不重用已消费许可。

# 2026-10-20 完整比较准备交付 v2

目的：复用现有严格FEM和4×64图初猜，以相同质量下完整在线时间比较前态、经典外推和NN初猜；本轮用户授权准备、独立审核和版本/预算送审，未授权本轮科学启动。

本轮：原owner基点829508617534c6c5febc813899498a31053684df的61文件未改，7个已有输入只核验哈希；新增标准库准备器、单次只读依赖inventory工具、5项合成测试及材料/载荷扩展设计。准确打包源提交2df7ded03a51e7375e2f1530155a655df79be0b8，branch codex/fem-surrogate-comparison-prep-20261020。本文及审核收据作为后续文档提交，不改变已审核源包。

结论：独立原实现审计69项合成测试通过；准确导出v1的5项新增测试通过。v2仅修正反力缩放一句，未重复测试。独立差量复核无剩余发现，结论只覆盖准备包与准确inventory请求；不含实际运行时准入、完整科学启动或多材料runner。详情见[准确收据](preparation_review_v2.json)、[原实现审计](existing_owner_audit.json)。无SSH、新FEM或训练，未解码holdout/科学数组。

## 准确本地交付

- 审批正文：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/v2/APPROVAL.md`
- packet：同目录，含68源文件、源manifest、tar、输入核验、构建收据、待激活卡、inventory请求、独立审核md/json。
- source artifact：`f5b14d5550d7cc902b8bcf656d353f60c1f6100020e676fe3ec1676c16977516`
- tar SHA：`301acca70c015c0fc2841f6fa1fde6f38ccbf066ab997cd5820cd6694c2a84f9`
- pending card SHA：`259068706fb609473e01d515c796c94b3fb0c8591f2ebbb244c3b89cb354de00`
- inventory request SHA：`1ebed9fd05a22c8af72ac8cc44d3d133d466c507bc48793ca2d3ac9414730062`
- APPROVAL SHA：`39e66753ef537da18c3a7d01f58b410a4c8ad3fedbd56ad4f3ee2658b46e0ed3`

## 预算与下一决定

完整A：3600子步、一次fit；原phase合116hosth、全局136hosth/≤16核/2176分配coreh、12GPUh；旧617.3239415297285秒保持，inventory前余135.82852112735284hosth。RAM64GiB，VRAM上限24GiB，主128GiB/归档128GiB。每物理子步120秒，首停不自动重试。此为上限，未获得实际完整耗时或设备货币单价。

当前完整卡execution_enabled=false、Matplotlib exact pin=null。按原v4合同只能先送审一次drtao@172.16.100.2/GPUServer8的标准库metadata核查，remote20秒加3秒kill、本地45秒、CPU10秒/256MiB、0GPU、0项目数据/科学包import/远端文件/安装/重试。具体完整命令与payload见APPROVAL；尚待人方批准。结果不等于包真实import/render可用性。随后须落实新run依赖来源/pin、入账、重建准确科学卡与差量审查，再给人方启动审批，保留原Agg/runtime/容量检查。

扩展B：见[载荷与材料设计](loading_property_extension.md)。优先变幅路径、Gc和alpha_T；目前FrozenGraphInterface和backend/state0绑定单physics_id，尚未实现材料族runner。候选新标签3000步+三配置三臂测试5400步，共8400新步和一次材料族fit；沿旧阶段上限算248hosth/24GPUh仅规模参考，尚无完整控制/存储预算，未获准，也未混入A预算。

## 2026-10-20 用户补充：逐case实测耗时

后续重新计算FEM case时按[逐case elapsed time要求](case_elapsed_time_recording.md)导出实测汇总，使用[空表模板](case_elapsed_times_template.csv)。主计时复用已有supervisor逐phase wall_seconds（含失败/清理），并区分worker轨迹时长、子步/内核分解和共享开销。本补充不修改已审核v2源包或授权任何新运行。
