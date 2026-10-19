# S01-E028 独立审查记录

独立审查者e028_independent_review；用户指定实际gpt-6.1-sol / High（新代理明确model与reasoning effort）。只读，无SSH、真实forward/训练、新图或polygon内容访问。

- 840e518f：Design MODIFY_AND_REREVIEW。补旧center参考对照输入、共同评价集合和各组合基线口径，防止不可复算或样本变动混淆机制。
- 2b38766a43fab43cd1fb71fb4a1f8dbb9db50462：Design REVIEW_PASS。9项输入、共同R_any-FG集合/权重、自身reference与预测的六基线、严格LOO逐图先验闭合；全地点原生对照可改变D7判断，不需再加小样本训练试跑。主候选/主标准/数据与封存不变。
- 82bcda6da1745c92c18b809dbeb0681c094d0379：Code Ready MODIFY_AND_REREVIEW。独立43-Werror与Pillow12.3合成fixture通过，但短命子进程memory_info竞态可能使watchdog静默退出；F02格中心偏移，缺raw probability与mean对照。
- b045170988b3f2a8fc641b7a7b89c617bb6c9e41：**Code Ready REVIEW_PASS**。逐进程memory_info仅读一次、已退出进程忽略NoSuchProcess，监督异常显式停止且写盘失败仍终止；bin中心与原生crop extent精确对应，原始概率/mean/max/叠图补齐。独立46-Werror测试1.16秒，Pillow12.3纯合成fixture通过，24项manifest一致；实际查看all_final/missing_final各5图及README，缺支持地点保持null/inconclusive。

最终manifest SHA256 `11c67539cadac809aa22efc8b74689fd3f54fe5b719be93c1f5df4b400d5a76b`。没有剩余必要代码阻断；512tile真实显存/3600秒吞吐未实测，未读取真实源图/polygon或计算新法真实分数。

PASS的范围始终是设计/工程，不是目标域定位成功、OOF检测收益或运行许可。

## GPU0 placement-only amendment

用户明确授权GPU0或Taobo后选择同Windows GPU0；R001仍未启动、预算未用。
- 8efb4c66：MODIFY_AND_REREVIEW。独立48-Werror及Pillow12.3合成fixture通过，27绑定一致；但两卡同型号，须额外验证实际torch逻辑0 UUID。
- fdf11452bc6770b75229e13ee79e226dc1c2caf3：**Code Ready REVIEW_PASS**，实际gpt-6.1-sol / High。逻辑0 UUID必须等于GPU0 UUID，错误/空/缺失拒绝且先于模型加载；独立49-Werror1.28秒通过，工作树干净，27绑定一致。manifest f6a975a67a88b7882ee8cfe9f9f61f688ce9788baf99eb222c77f3baa2bfa1e5。
科学协议、输入、评分、预算不变；历史helper未改，Realtek未放行；新E028 GPU0基线仅冻结经有效签名核实的7个exe路径/hash，未知/C类型/hash/UUID/利用率不符仍停止。PASS只覆盖执行准备，实时资源仍须核验。
