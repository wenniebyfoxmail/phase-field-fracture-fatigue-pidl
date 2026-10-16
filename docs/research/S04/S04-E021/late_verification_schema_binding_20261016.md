# Verification字段绑定：单文件只读结构查看

2026-10-16 Europe/London。用户批准仅查看指定verification JSON的字段路径和类型并补齐绑定；
不批准CSV、独立数组文件、确认数据读取或真实分析／拟合。本主对话唯一修改代码、记录及Obsidian。
基于干净HEAD `bd47bd2f825e536e2e7dcc54d9f655c42fae7d3b`，继续使用原专用分支／工作树。

## 本轮唯一真实文件查看

仅打开：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_verification.json`。

一次stdlib独立schema探针，不导入任何项目runner或loader。精确路径拒绝alias，regular file且
≤1MiB，O_RDONLY|O_NOFOLLOW，文件描述符及路径的dev／ino／mode／size／mtime_ns前后相同，
finally关闭fd。JSON重复键／非有限常量拒绝；仅输出路径及类型，不输出标量值，不展开JSON数组元素。
不扫描目录、不跟随JSON中的路径，不新增hash，不改源权限／内容，不保存原JSON副本。
没有打开CSV、summary、其他控制JSON、轨迹、模型、NPZ/MAT/PT或确认数据。

这是已批准的真实控制JSON结构读取，**不能继续写成“本轮没有读取任何真实文件”**；
但没有对真实数值计算比值、R/G/Q、误差分解或其他科学量。JSON整体解析只为结构，未据此核验
run、commit、计数、审核状态或晚期数值是否符合既有预期。其他字段和值均不作本轮结论。

## 五项显式映射与单位（最小结构决策表）

JSON Pointer空前缀代表根对象；表内不保存任何实测标量值。

| 适配语义 | 实际路径 | 观察类型 | 处理 |
|---|---|---|---|
| run_id | /run_id | string | 显式选择，未来snapshot仍核对固定Run |
| runtime_commit | /code_commit | string | 选择code_commit，不猜reviewed_source_commit的值；未来核对原runtime提交 |
| rows | /ordered_unique_rows | integer | 严格int，不接受bool |
| counts | /exact_cycle_counts | object | u011／u0115／u012／u013各为integer；未来仍核对原固定counts |
| late_ratio（适配后的量） | /u011_C41_plus_RMSE_increase_percent | number | 源是RMSE增幅百分数，不是比值；未来需1+percent/100 |

路径与类型已观察；身份等式及数值是否通过尚未检查。runtime语义依据原运行卡／审核记录与
code_commit字段名绑定，不能把schema查看当作其值已等于08242ea的证明。若未来不相符必须拒绝。
源百分数精度也未核对；仍保留原1e-12比值比较容差，不因未看数值而预先放宽。
这不是MSE增幅或平方比，不对百分数再平方／开方，也不改变旧科学结论。

## 最小实现与授权限制

`SENS_tensile/s04_late_adapter.py`：

- REAL_VERIFICATION_BINDING从None改为以上五个明确selector；不做递归搜索或模糊字段回退。
- 新纯函数bound_verification_values只处理调用方给定的dict，严查string／int／dict及计数int，
  百分数字段只接受int／float并拒绝bool／string／非有限值；执行时才换算为比值。
  **本轮没有对真实doc调用这个函数。**
- REAL_ACQUISITION_ENABLED=False；acquire_real和REAL域snapshot均在源IO前拒绝。
  schema许可不等于四源读取许可；本轮不启用、不创建真实CLI或授权reader／launcher。
- 既有真实Run／commit／rows／counts／冻结比值检查保留，四源白名单、数据角色、原纯核心、
  9984226计划、归一化／分组及监督器预算逻辑均不改。

`s04_late_adapter_checks.py`仅更新未绑定时代的拒绝断言／状态，写入纯人工字段夹具：
百分数到比值、七种类型／数值错误及缺字段拒绝，并检查已绑定REAL域仍在任何IO前拒绝。
没有复制真实控制文件值，所有新增用例**尚未执行**。本轮只用ast.parse和git diff --check，
不导入任务模块、不运行mock／guard，不创建新Run或local_archive输出。
旧R002及运行卡只对应fb484ae，不作为新绑定已测／已审证明；不复用已消耗的尝试或改写旧回执。

## 当前判断及唯一下一步

字段路径／类型与最小绑定实现已补齐，状态为**schema bound／execution disabled**，不是新代码
已测、Code Ready或真实分析就绪。当前无数值实验，以上映射表足够，不需要装饰图或新增计算。
PIDL闸门据此保留结构确认、代码审查、执行授权和科学证据之间的区别。

唯一下一步建议：先对这次字段绑定、百分数换算、类型拒绝及显式关闭联锁进行独立静态差异复审；
本轮不发送新的审核或执行消息。认可后再决定最小针对性mock及真实授权reader／launcher的准备范围，
不直接读取CSV或启动分析。新mock／真实运行都不能继承已消耗的R002许可。
方法对话继续只读分工，本轮未向其发送任务；主对话单写Obsidian与Roadmap，避免重复实现／计算。
U0.1175／U0.125确认数据关闭，E017／NN／多目标训练暂缓。原结果和其他对话改动保持原状。
