# Stage A 启动修复与继续执行记录（2026-10-22）

## 本次授权

人方要求修好 PowerShell 启动和错误日志，不改全局策略，取消预算限制继续阶段 A，成功后进入阶段 B 或训练。本次选择先阶段 B FEM；阶段 A 的物理状态、残差阈值、旧前态和历史保存要求不变。原三小时和零启动二十分钟不再构成本次累计停止线。每个任务的有限防挂时限在其 authority JSON 中显式给出，不重置或隐瞒原历史成本。

执行源码从 `9a763140cde0155a7a28dfbcee2ede5b0da49db4` 隔离到 `worktrees/s04-stage-a-launch-20261022`，避免另一个任务对旧工作树的并发编辑。旧树未清理、回滚或覆盖。

## 已完成的修复与实际检查

- 新 supervisor 以完整 x64 PowerShell 路径启动，`-ExecutionPolicy Bypass` 只作用于本次子进程；没有 `Set-ExecutionPolicy` 或全局设置写入。全局四个 scope 在启动前后分别记录。
- cmd 进程从 launcher 入口之前就重定向 stdout/stderr；supervisor 从 watchdog 创建时同时异步读取两条管道，记录退出码、完整异常和最终 receipt。watchdog 为本任务的挂起子进程先绑定 Job Object，再核验身份、写 receipt，最后 resume；清理只针对持有句柄的本任务进程。
- 每次新 label/authority/输出路径，禁止覆盖旧 receipt。可选累计截止为 null，本次没有累计预算。原 disabled 双臂和 MATLAB 仍串行运行，保留最多4 CPU与空闲磁盘保护。
- 两份独立静态复核未发现阻止 prepare 的确定错误；实机 PowerShell parser 对两文件均返回零错误。producer 上45个部署文件和51个来源文件已逐一 SHA256 匹配，目录为原任务根下的新 `code_02`。
- 实际可用 Python3.10.11 依赖为 numpy1.26.4/scipy1.15.3/h5py3.15.1/torch2.5.1+cu121/matplotlib3.7.1；只做导入，未优化或训练。Python3.12 缺 torch 的原观察保留，未安装或修改环境。

## 当前实际执行状态

错误捕获负控 `log_probe_02` 的 WMI 创建返回0，cmd PID41896，时间2026-10-22T00:18:05.8080984Z。该负控仅主动抛出 `E036_EXPECTED_LOG_CAPTURE_PROBE`，不启动 MATLAB/FEM。

其进程日志结果目前 **UNKNOWN**：自动审批两次拒绝后续只读日志/状态读取，理由是把 HQ “停止托管”解释为本窗口也不得继续。复核时已提交本窗口人方直接继续授权及 HQ 明确“只停止HQ协调、不取消本任务”的原文，仍被拒绝；已请求人方澄清，未绕过。第一次较长远程入口还碰到 Windows 命令行长度限制，未产生远端计算；对应失败 receipt 保留，随后改为短入口读取已上传任务脚本。

MATLAB checkcode、28 mock、新 MEX 构建、U0入场、disabled双臂及四个冻结状态原生比较均尚未启动；不得把 parser/部署成功当作科学一致性。Stage B 和训练尚未开始。

## 文件与复现指针

case：`local_archive/experiments/S04-E036/stage_a_20261021_2142`。

- `analysis/direct_user_continuation_02_authority.json`：人方授权原文。
- `run_workspace/prepare_02_r2/`：最终已部署 prepare 配置/manifest/入口；旧未部署候选包保留。
- `logs/stage_prepare_02_r2.json`：实机 parser、源码 SHA、资源快照。
- `logs/launch_log_probe_02.json` / `launch_log_probe_02b.json`：命令行长度失败与后续 WMI 创建结果。
- `analysis/continuation_02_remote_review_hold.json`：当前审批阻断及明确的未执行范围。

解除阻断后先读取现有 probe receipt，不盲目重发；验证错误、非零退出与全局 policy 未变后，执行已准备的 `prepare_02`，再按真实结果推进原生比较。所有失败和历史锁保留。

## 隔离树后续本地准备（未部署运行）

比较器移除隐藏600秒上限，CLI要求显式 `--wall-seconds`，由独立比较器watchdog核对与本任务authority一致。新增7个墙钟检查案例分批覆盖：首批4通过/3失败，失败为mock报告元数据缺失；仅修复fixture并重跑原3项后全部通过。原失败及两批JUnit/stdout/精确SHA保留于case/logs/python_compare_wall_01*、_02*及python_compare_wall_validation.md。没有把这两批写成完整42项套件通过。

新阶段B authority/前态导入/driver及其独立launcher/watchdog已准备；以阶段A真实原生比较及成功进程记录为前提，仍未部署或运行。已有c82s5字节资产仅为候选，来源及当前原生入场未完成，不当作可用前态。每个窗口只从已读回前态推进，不填补旧history slot1、不补跑新recovery。B的科学阈值与普通/紧容差角色不变。PowerShell子系统独立静态记录见 tools/s04_e036_fem/PROCESS_LAUNCH_STATIC_REVIEW_20261022.md。
