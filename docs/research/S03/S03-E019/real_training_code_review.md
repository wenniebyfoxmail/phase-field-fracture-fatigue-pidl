# E019-D03 独立只读代码审查

2026-10-17；审查者 `/root/e019_d02_review`，未参与这三个新文件的实现。
仅静态源文件/git/rg/hash，未执行Python/导入/语法检查/测试/计算或读取
local_archive数值产物、真实数组/收据/留出；未修改文件或外发。

## 第一轮：REVISE_STATIC_CODE

审查snapshot `662840fb081d0252a55e68d975ad5ea32d16dafd`，代码基线
`e086d70318242778680ad23fefbd05316e9254f6`。初始三源码SHA分别为
40e8e21b556040d4c8084fdfc0c6b7083a0a9e339b6cd8f71e68461ab2e05b4e、
8efe9797f43a9b6601e476d3114d81601edf2af44d48bbe53bca1db7fc4beb4c、
e57a74f4a15b23ec58daaa229222460a159dd4d29e959f1b0a0b2236a8045fbb。

5项必须修订，已按用户授权修正，尚待复审，不称Code Ready：

1. 导入前warning/logging停止保护及命令-W error；无字体例外。
2. verifier逐文件连到锚定PREP/FIT artifacts，核来源/训练身份/载荷序；代码
   manifest键集必须恰3项，而非允许空集合跳过。
3. A加--source-commit，起止代码字节/HEAD/clean一致；只允许受审基线后的docs差异。
4. B/C/D完成标志前末次核代码/HEAD/clean；D也末次核真实来源原字节。
5. 只写新根的MPLCONFIGDIR/XDG_CACHE_HOME；固定输入/输出/祖先拒绝软链，
   输入要求普通文件。缓存权限不等于允许其他真实数据读取。

新加4项人工测试设计（共24项）：Python warning、logging WARNING、假软链
拒绝、runtime HEAD改变；全为声明的人工预期控制，不运行实际警告来源或文件I/O。
测试未执行，修正没有改变算法、原阈值、cutoff或允许的真实信息集。

初审已核数值核心无必须换算法/阈值问题：完整构造链与b=Az、保留双侧、
一次gesvd/两QR、一次候选Q、eta、全量BLAS/完整参考及像内先行平方账本。
这些是源码静态对应，不是运行或真实数值通过。
