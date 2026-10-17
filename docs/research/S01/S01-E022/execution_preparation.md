# S01-E022-R001 执行准备（尚未传送或执行）

精确实现f8990c148b14298db16490cd6f4460794271a8dc；方案3e776d0e经6.1 sol-Medium审查通过，代码复审结论见同级implementation_status。manifest205绑定/源码包206文件，SHA c0ab6c70a517c3b56f91fee874e1b177879c1a8d45a67ab29ebf9438f82ebc8b。只传源/合同/测试，不含私有审查/结果/提交历史。

本地源码包：local_archive/experiments/S01-E022/prepared_R001/S01-E022-R001-v1-f8990c14-source.tar.gz，546715bytes，SHA3f74ca87381e359dc8e1644f49697f8d7d8f028c73cc7bc209ecd10e186a66ee；成员逐一与当前绑定源码核验一致。若复审改源码，当前包立即作废并准备新精确版本，不能继续执行此包。

未来指定公开分支codex/s01-e022-semantic-localization-20261017，基于已公开E021cb9fdc5186aaf317edb06bfecedcacab74a53aaf生成source-only提交，核205绑定一致后方可推送。当前尚未生成或推送公开E022commit。

未来唯一producer为gpu-server/D-26-09/ad\xw436，物理GPU1/逻辑0、固定UUID及WDDM桌面进程基线必须现场核验，CPU1、3600秒、聚合RSS4GiB、GPU allocated/reserved各4GiB。原835训练图/19成员/metadata/E003 checkpoint须hash/身份核验，source/run/log均用新目录，无重试/换机/放宽。真实预检/源码传送/公开分支推送及R001尚未执行，本轮用户范围为方案→审查→实现/测试。

源码入口scripts/pavetrack_semantic_selector/producer.ps1，参数Source、ReviewedCommit、ManifestSha256；PowerShell固定原19成员ZIP/metadata/E003路径、R001与wrapper-logs，无需手改源码。启动前须确认source-only公开字节和实际执行源码均等于精确Code Ready版本；使用脱离SSH的独立包装进程并保存PID/日志/资源/收据。不得因断线重试。

决定性结果：3/5/6已知有益GT能否进入原前三/检测预算，OOF684旧检测保留率、新/失/净GT及macro/12地点变化。主标准旧>=95%、净>=1且macro>0；组件进步单列。若前三仍0或全弃权，按冻结停止固定最后层margin归因双描述家族，不换层/目标/梯度法/参数、放大容量或扫描交集救结果。新确认/validation/reserve及旧资格排除地点继续封存。
