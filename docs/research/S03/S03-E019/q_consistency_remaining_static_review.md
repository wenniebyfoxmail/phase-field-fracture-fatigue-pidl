# E019-D02 剩余只读验收 — 独立静态审查记录

2026-10-17；审查者 `/root/e019_d02_review`，未参与本验收脚本实现。
当前仅方案/命令静态审查，不读取产物数组或执行验收/测试。

## 第一轮完整返回：REVISE_STATIC_REMAINING_ACCEPTANCE

> REVISE_STATIC_REMAINING_ACCEPTANCE：发现 1 项必须修订，暂不能通过。
>
> aa2024_d02_remaining_readonly.py:193、197 的 Q 向量求值路径比较直接调用通用 close。超容差时先抛出 STOP_IDENTITY，不会到达第205行的专属分流。这与方案第96–97行承诺的 STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED 不一致。
>
> 应仅修正上述参考求值差异的失败分类，并保留具体比较标签/原异常；不改变操作数、原容差、ratio 各自定义或通过标准。第205行的状态分歧检查仍需保留。
>
> 其余未发现必须修订项：
>
> - 标准库、固定白名单、来源快照及 A/B/派生说明绑定明确；无 producer 导入、写文件或重新分解路径。
> - 保存 U/T、五模式、原容差、eta 硬界、解析参考、旧负控及五探针检查对应既有方案。
> - producer/Decimal ratio 分别按各自操作数核对，没有新增跨路径标量相等门槛。
> - companion 两处派生映射与原 same-stem 限制明确，不冒称官方目录 validator 通过。
> - 自动命令通过后才允许一次 PNG 目视；PDF仅解析/元信息，不渲染或冒称视觉通过。
> - 预算、首异常停止、无重试及 stdout 后迟发失败限制有明确记录。
>
> 核验身份：clean HEAD 0a2ee105de9b9dde4641f2694c8c2d92295084ed；脚本 SHA256 93b048c9948475ca7c9cfd357c13c4e12b963c9ee258708c0f010af258bcecd3；方案 SHA256 14eda7a8ebfeed32267f4eec9da1b1a77b82898d04daeb609714af2f1f2dc928，均与送审值一致。
>
> 仅静态阅读/git/rg/hash；未执行 Python、导入、语法检查、测试、验收、算术、validator、pdfinfo 或图像查看，未读取数值产物、收据、图形、真实数组或留出，未写文件或外发。修订后需复审，不得据此继续暂停的验收。

## 最小修订（未运行）

仅在producer/reference与fsum/reference两处向量求值比较外捕获ValueError，
保留原异常链/文字和比较标签，专属标为参考路径差异未解决。
操作数、阈值、ratio、原状态分歧检查及其余白名单/操作均不变。
方案版本v1.1，代码/确切命令重新绑定SHA后进行独立静态复审。
尚未运行语法/导入/测试或任何验收，不据修订称缺口运行时验证完成。
