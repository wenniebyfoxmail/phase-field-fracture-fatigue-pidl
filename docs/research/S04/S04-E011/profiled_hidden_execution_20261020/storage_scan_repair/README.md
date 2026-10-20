# 原子JSON扫描竞态：局部修复（关闭，未运行）

目的：消除5449d5a9真实首检中出现的遥测假故障，继续原冻结c20 PIDL方向/预条件问题。科学方法和原输入、Phi、FEM damage、UV边界、1e-10、B0/约束Q4、工作/资源/时限上限均不变。

实际失败是`os.walk`列出monitor.json.2909412.tmp后，controller将其原子替换，sampler再stat已不存在的临时名字。仅原子JSON临时元数据已消失时可以不再计入当前存储；这并不允许忽略原始字段、任意cache/guard临时文件或其他IO错误。

本地精确改动只在control.bytes_under与人工测试：

- 遇到FileNotFound，只有basename精确为`*.json.<十进制PID>.tmp`才继续；其他FileNotFound仍抛出。
- 存在的临时文件仍按实际字节计入，符号链接仍拒绝；PermissionError和其他OSError不捕获。
- os.walk的onerror显式重抛，避免不可读目录被默认静默跳过。

42项mock测试通过：原37，加消失JSON临时名、普通/未知文件消失、存在临时文件计数、symlink/权限、目录遍历权限错误5组。没有真实NN、FEM、GPU、Linux重启验证或性能改善结果。独立精确差量审查见review.json。

当前[关闭修复卡](repair_card.json)没有新RunID或新claim路径，也没有launcher/启用authority；不称为新producer-ready包。已运行的5449d5a9远端代码、原目录、claim和结果冻结。本地修复没有上传或启动；下一次真实执行需要明确的新尝试授权及前瞻的精确包/路径/claim安排，不能自行清除旧claim或将本轮剩余时间当作重跑许可。

证据资产：[本轮真实停止](../../runs/pidl_profiled_hidden_preflight_result_20261020.md)。本修复只处理这次已定位的atomic JSON情形，不声称其他并发文件情形已实测排除。
