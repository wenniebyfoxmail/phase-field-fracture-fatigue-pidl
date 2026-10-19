# 首版 producer 独立复审：需要修改后复审

范围：不可变提交 `d05fd5834468f04e200d70e7f4dce7873241af6d`，artifact `73f617acd9d23fc6706c6493665e3d92035d29f4e317bc3e3b3566a43c62d276`，源卡 SHA `5603ff641bd8d4fdf97dd8e208447785cc1dff2bc0a78e40157cb6dc74486097`。该结论不覆盖提交后的启动器/工作树改动，不提供本对话执行许可。

独立 reviewer：`/root/loss_weight_readonly_review`。只读静态审核；未运行科学 worker、FEM、训练、补充 FP64 或 SSH。完整原始报告、材料哈希与机器收据已同目录归档。

1. **R1 / P1：硬时间上限可能超支且成功登记。** `tools/run_hybrid_producer.py:119-157` 的 deadline 依赖同一监控循环；其中 GPU 查询可阻塞 15 秒（76-78）、目录扫描及 JSON fsync 没有独立 deadline（146-154）。退出后只核对 return code，未再核对超时；110-116 还另给最长 20 秒终止宽限。因此 120 秒子步及 phase/GPU/总时间上限不能据此称硬限。Popen 后、进入 supervise 前的日志写入/信号异常还可能遗留 worker（236-239）。需从 Popen 起无条件清理自有进程组，使独立时间控制覆盖监控阻塞，终止宽限纳入已分配预算，成功退出也复核全部 deadline。
2. **R2 / P2：失败资源峰值从最终账本丢失。** `supervise:158-160` 异常时不返回已采样 usage；外层 233 初始化空字典，finally 仅补 wall/CPU。需使失败/kill 的 RAM、VRAM、存储样本及终态版本与完整耗时同样持久化。
3. **R3 / P2：经典对照质量未进入联合提速判断。** `outcome:172-181` 仅检查 NN 质量，却以 `min(CF,CC)` 比较并可给 `supports=true`。若经典轨迹未达到同一质量要求，不能称三组在匹配质量下已建立加速。需固定质量可比性处理，并分别报告各组质量与成本。
4. **R4 / P2：预定科学输出尚未实现完整。** `tools/hybrid_producer_worker.py:117-146` 只有 u/v/d、A/r/f、反力误差；原设计/预算中的 raw/active、能量、负 damage/历史回退、形态、fallback 汇总及真实场图未补齐。需完成输出与保存接口，或明确缩小结论；本用户请求完整场、分量与回退，不能直接省略。

数据隔离与原子状态提交的已查部分未发现新的严重混用；这不能抵销上述问题。41 项轻量检查通过仅作为已有工程检查保留，不能将此首版判为 producer-ready。

本对话不改原 owner 工作区，不另写重复 producer。由唯一 owner 修复后冻结包含实际启动入口的完整闭包，再对变更及下游影响复审；未变更库的旧审查结论复用。
