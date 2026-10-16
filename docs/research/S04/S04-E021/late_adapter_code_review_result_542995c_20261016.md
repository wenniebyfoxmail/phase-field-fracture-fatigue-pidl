# 542995c独立静态审核：两项必改，尚未完整就绪

2026-10-16 Europe/London。送审代码 `542995c387d113bc398a9f77ceb38ea1dcf3e0b7`；
工程记录7db8df8，发送核验e1effa5。审核由既有「多目标优化学习 FEM–PINN Delta」对话完成，
thread `01a12d15-9b60-7280-8248-18386d6ef741`，turn `01a146ab-4be2-7680-8537-bbc7ba5881db`，
final message `msg_015d0a19570ed14a016ad29adfe9d08191a2e9ca5ba1c045fb`。
已观察turnCompleted、status=completed、error=null，未重发请求。对方仅静态读源码和指定记录，
明确未运行测试、读取真实源或修改记录；本主对话统一核对、写文档和Obsidian。

## 逐条核对

| 审核意见 | 主对话源码核对 | 处置 |
|---|---|---|
| 必改1：summary缺自身run_id／code_commit身份校验 | adapter193–195只检查status、original_verdict、fitting_invoked；producer s04_raw_replay.py216明确result.update(run_id,code_commit)，无需读真实JSON即可加；SUMMARY_ID mock仅改status | 确认成立。下一修订加固定Run／commit及错值、缺字段拒绝mock；本轮不追加修改或运行 |
| 必改2：MOCK_ONLY可配真实ReadOnlyIO | snapshot162–171的授权后仅对REAL域检查binding；MOCK域带显式mock binding仍可进入io.metadata；现有fixture均是MemoryIO，没有联锁拒绝这个组合 | 确认成立。下一修订在任何源IO前拒绝mock域与真实reader组合，并断言无源调用；不通过真实IO试验复现 |
| 四源白名单／O_RDONLY／O_NOFOLLOW／token及finally关闭合理 | adapter43–85与身份清单核验对应；metadata不是内容认证 | 接受当前实现的静态评价，不升级为实际归档验证 |
| 授权路径、env、父PID及grant拒绝顺序合理 | check_grant、prepare／decode_child及mock跨cwd代码相符 | 已实现的是组件与内存交接，不是完整真实launcher或人类授权证明 |
| acquire_real在未绑定前拒绝；guard预算／单次目录机制不变 | REAL_VERIFICATION_BINDING=None先于ReadOnlyIO构造；guard仅固定worker配置；纯核心和9984226方案diff为空 | 接受。原单次mock不重跑，真实入口继续关闭 |
| fd层mock边界 | fake-fd仅成功读取／关闭；未覆盖fd mismatch、读取异常及读取中漂移 | 明确为覆盖限制；后续最小差异mock应补这些分支，不称本次已验证 |

## 当前判定及唯一下一步

五组mock通过且预算内，是既有工程记录事实；不因审核发现而删除或改写其历史结果。
但独立审核**尚不认可适配合同完整就绪**：两项必改未修，不能以mock完成宣称Code Ready或真实执行许可。
本轮收到意见后仅静态核对／记录，没有调用测试、重新mock、打开真实控制JSON／CSV或拟合。

建议唯一下一步：只修上述两项联锁／身份问题，补对应差异mock及fd错误边界，准备新的单次mock卡，
仍60秒／512MiB／5MiB、失败不重试；先独立静态差异审核，不自动执行下一次mock。
该步骤不需真实数据。再后的verification selector查看／绑定、复审、真实授权reader／launcher和
实际分析批准均须单独明确；此时不申请或执行真实schema查看，避免修代码与访问数据混为一步。
无需现在改顶层科学设计或增加模型实验；U0.1175／U0.125确认数据关闭，E017／NN／多目标训练暂缓。

本次PIDL实验闸门用于区分工程完成、静态审核和科学证据；没有更改科学指标、数据角色或旧E021结论。
源码仍保持送审542995c，输出只读冻结，旧R002及失败现场完整保留。独立对话无共享文件写入，
本对话统一更新进度笔记及Roadmap；未push、未删除工作树或其他对话改动。
