# ea9cafb范围实现：fd4700f独立静态代码审核请求

2026-10-17 Europe/London。用户批准实现并直接提交独立代码审核；不批准执行、真实读取或拟合，不重复mock。
源码`fd4700f3e48057d8a99294648b2df1667742914d`，基于干净ea9cafbc907cb683544aca75a58480b51c7487bd。
仅3源码变更：新增s04_late_access.py／s04_late_access_guard.py，修改s04_late_adapter.py的事件记录及调用级许可。
未改四源／schema／归因公式／容差／原预算监督器／原9984226方案／ea9cafb范围卡或旧输出。
只有3文件AST解析和git diff检查；未导入模块、运行CLI/help／测试／mock、读取真实metadata／内容或创建Run。

## 实现定位和未验证事项

| 合同 | 实现／限制 |
|---|---|
| 授权reader | 固定本Run authorization.json，64KiB有界UTF-8、常规／只读／非链接、O_RDONLY／O_NOFOLLOW、path／fd token及关闭；严格JSON沿用原adapter |
| worker | 固定输出，先检查父子环境与完整代码，再读授权并校验grant；复用真实四源snapshot，仅写接入控制结果，不调用describe／report，不落盘rows／background数值 |
| 默认关闭 | REAL_ACQUISITION_ENABLED仍False；普通旧调用无execution_refs即拒绝。授权路径核对refs／grant／父子／固定目录后，创建绑定同一grant对象、代码、输出和实际父PID的私有调用级permit；不全局改True |
| 非优化 | guard／worker在其他依赖前if／raise拒绝sys.flags.optimize非0，子环境固定PYTHONOPTIMIZE=0 |
| 实际访问状态 | metadata_attempts为保守尝试标记，非完成metadata认证；读取按os.read返回块计content_bytes。worker失败仍写访问记录；无worker终态时父回执以null/unknown表示，不能自称未读 |
| 监督器 | 复用原cap_reason／output_size／cleanup_child；新身份／路径／四输出及真实完成判据单列，不把实际读取记成mock。60秒／512MiB／5MiB、58秒工作余量、20ms采样及16KiB回执余量保持 |
| 人方授权 | --allow-real-read、--approval-ref、--review-ref和精确源码是调用联锁；引用只作追溯，不自动证明实际人方批准／独立认可。主对话在未来获批执行前必须读回真实批准及审核版本，并将引用填入命令／回执；本轮没有此执行许可 |

五运行依赖文件：s04_late_attribution.py、s04_late_attribution_guard.py、s04_late_adapter.py、
s04_late_access.py、s04_late_access_guard.py，均在SENS_tensile。guard核对tracked／clean、源码等价、
冻结方案及ea9cafb范围卡无差异。固定拟Run仍为S04-E021-LATE-DIAG-R001，当前未核查／创建输出。
未来launcher接口仅--out、--expected-commit、--approval-ref、--review-ref、--allow-real-read；
当前不提供填好许可的启动命令，不调用它、不生成真实授权或运行卡执行许可。
返回内容的运行时正确性、资源／清理、OS fd行为、授权交接和实际四源适用性尚未动态验证。
原静态认可／已消耗mock不自动覆盖本次新reader／worker／guard。真实执行版卡仍待审核后单独准备和批准。

## 发送身份及最终正文

发送：S04主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c；接收：
「多目标优化学习 FEM–PINN Delta」01a12d15-9b60-7280-8248-18386d6ef741。无附件或计算承诺。

<!-- REVIEW_BODY_BEGIN -->
请对fd4700f3e48057d8a99294648b2df1667742914d做独立静态代码审核，范围是用户批准的ea9cafbc907cb683544aca75a58480b51c7487bd四源只读接入合同。工作树/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016。合同在docs/research/S04/S04-E021/late_real_readonly_access_scope_and_run_card_v1_20261017.md；实现说明及本请求在late_real_access_code_review_request_20261017.md。

相对ea9cafb仅新增SENS_tensile/s04_late_access.py、s04_late_access_guard.py，并修改s04_late_adapter.py的访问事件和调用级permit。请完整核对授权reader的固定64KiB只读fd／path交接，grant精确字段和父PID／完整SHA／绝对路径检查是否全部在科学stat/open之前；四源固定、有界全文但仅使用原声明字段，实际接入不调用describe/report或拟合／归因。共享真实开关仍False，私有permit只在grant、引用和实际父子交接校验后创建；请检查这种默认关闭与受限入口的边界，不能用旧mock通过替代本版认可。

请重点检查监督器在原60秒／512MiB／5MiB及58秒工作、20ms采样、16KiB余量下，是否计入授权和全部四输出；首因／terminal_caps、未知退出／回执失败、已发生或未知真实读取能否正确保留；仅清理本guard进程组、不重试。新worker失败时保留访问计数；metadata_attempts是保守尝试标记，content_bytes按返回读取块计；无终态结果时父回执不得写false。请同时检查新完成判据、默认非优化启动、源码／scope身份和固定新目录。

批准／审核引用是追溯字段，不是人方身份自动认证。未来执行前必须由主对话核对实际批准和审核正文、绑定最终代码／命令；当前只有实现／送审授权，没有真实执行许可。请指出代码或说明是否在这点过度声称，或还有必改／范围缺口。

本轮仅AST语法／diff检查，没有导入或运行项目模块、CLI/help、mock、测试、优化负例或资源核验；不读取任何真实JSON／CSV／控制输出／数组／模型／轨迹／确认数据，不创建Run或授权。请也只读Git源码／合同和文档，不导入／运行、修代码、补测试、扫描真实路径或写共享记录／Obsidian。只在本对话最终回复静态结论、具名必改项／未验证边界和唯一最小下一步，不回发主对话或派任务。主对话读取后逐条核对并统一更新Obsidian，避免双写和重复计算。即使静态认可也不执行或开启确认数据。
<!-- REVIEW_BODY_END -->

内部措辞检查（不发送）：以本轮用户短句和精确范围为参考，仅保留技术审核必要信息，
无科学收益／人方身份认证承诺；不声称精确仿写，不夹带计算或写入任务。送达和最终回传另行核验。

## 首次送达及唯一必改

上述正文一次发送，回传指定threadId且isError=false。turn `01a14aa3-fa95-7361-bf5f-743a5afe8380`
completed、error=null；最终message `msg_015d0a19570ed14a016ad39f843d948191b8cfc1ab9fadd50f`。
回传fd4700f需修订后复审：execute计时在参数／路径检查后才开始，漏计预检；其余主要接入逻辑静态可接受。
主对话读回该turn，仅Git源码／合同查看，无导入、执行、真实路径扫描或共享写入。
语义限制一并保留：代码已有受限真实读取路径，不能笼统称真实读取完全不可达；默认开关False不是人方许可认证。

主对话按用户已批准的实现／预算范围，仅将monotonic和UTC开始点移至execute函数最前两条语句；
新源码`33feec6813347177649cffbcc0ba39297937a09e`。差异为2行前移，没有其他行为／范围／预算变更。
只做该文件AST及diff检查，仍未导入、执行、读取真实数据或重复mock。下述为差异复审最终正文。

<!-- DIFF_REVIEW_BODY_BEGIN -->
请对33feec6813347177649cffbcc0ba39297937a09e进行只读静态差异复审，延续本次用户已批准的ea9cafb范围实现及独立代码审核。工作树仍为/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016。

已逐条核对上轮fd4700f意见：唯一必改是计时起点偏晚。新提交只把s04_late_access_guard.py中的started=time.monotonic()及对应UTC开始时间移至execute入口，作为最前两条语句，参数／路径预检不再被排除。后续58秒工作余量、elapsed、终态及post-receipt仍引用同一个started；没有改源码其他部分、四源、授权、预算或停止规则。请核对这项必改是否闭合，给出新版本静态结论及是否仍有必须修正项。

其他边界沿用上轮：已有受限真实读取路径，默认开关仍False，但不声称真实读取完全不可达；许可引用只是追溯字段，人方批准和精确审核须由主对话在任何未来执行前实际核对。本轮只有AST／diff检查，没有运行、CLI/help、mock、负例、资源核验或任何真实metadata／内容读取。原mock不重跑，确认数据关闭。

请仅阅读Git源码差异、原合同和请求文档，不导入／运行代码、不补测试／修代码、不扫描真实路径、不写共享文件或Obsidian，不回发主对话／派任务。直接在本对话最终答复结论、范围限制和唯一下一步，由主对话读回核对、统一记录；静态认可不等于执行许可。
<!-- DIFF_REVIEW_BODY_END -->

## 差异复审送达与回传

差异正文一次发送，回传指定threadId、isError=false；这是已知首审意见后的新版本复审，不是未知结果重发。
turn `01a14aa8-180a-7d93-b7ea-f252e25e86e0` completed、error=null，最终message
`msg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab`明确认可33feec6，计时必改闭合、无新增必改。
主对话读回该turn，仅Git差异／源码核对，没有运行或真实读取／共享写入。
最终逐条核对及限制见`late_real_access_code_review_result_33feec6_20261017.md`。
