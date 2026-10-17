# E019-D01 — v1.1一次独立只读算术验收结果

2026-10-17；独立执行者 /root/e018_code_review，主代理未重复执行或复算。
用户明确批准已审v1.1命令一次、单线程CPU/60秒、首个非预期异常即停、
不重试；ratio跨路径差异使用专属分类，不直接判原report错误。

## 结论与实际范围

独立执行一次、exit0、无STOP/警告/traceback，结果：
`PASS_SAVED_C1_C3_ARITHMETIC_WITH_C0_LIMITATION`。

来源/CSV序列化、C0已存H/Gram、C1–C3已存因子与p/r分层账本、独立Q
参考、跨例相同p/r不同A对照通过。三例ratio跨路径比较一致；C2/C3原Q
不通过仍是预登记负控，不是本次验收异常。没有放宽阈值。

限制不变：C0原C/A未保存、不重构原A层账本；原逐分量Qr未保存，不认证
其逐bit求值历史；计数字段仍是原收据/报告自报，不独立认证全进程行为。
两个factor_reconstruction_max的exact_match=false如实保留，满足原比较
容差，不称逐位相同、也不称原保存0代表高精度残差恰为零。
这不恢复真实E019暂停状态，不证明真实根因、物理反演或未来预测有效。

## 执行身份与计时

- 已审材料快照：f805eab139c9fbcce1ea4c7ff6d695da08bb2015。
- 实际起始/脚本结束HEAD：e75d3a8add790a7dc8349491cf656c2f775a3c24，clean。
- 方案/确切命令SHA256：95ce2969c707c0b3b29282c966999eb2e38b5f9adb4961e7d057af17a2746719。
- 从已核字节的方案第104–319行原样提取唯一bash命令，/bin/bash，login=false。
- 工具chunk d32f4e，同步完成、无运行中session；执行次数1，exit0。
- elapsed_before_stdout_seconds=0.37604833295335993秒/60秒，是最终JSON
  输出前取样，不是全部stdout结束后的精确总耗时；stdout后的预算检查
  亦通过，否则不会exit0。未把验收时间写回原诊断/显示收据。
- 五项线程1、CUDA空、Python -I/-B/-Werror；只用标准库、无文件写入。
- 脚本完成末次固定产物/11源码哈希和HEAD/dirty不变核对，无额外补查。

独立执行者未重跑producer、测试、QR/SVD、求解或绘图，未读取真实数组
或留出，未修改命令、资产、原receipt或V01。主代理仅记录返回结果。

## 完整原始stdout

以下保留该次命令的全部标量核对与来源身份，不含原始矩阵/真实数组。

```json
{
  "status": "PASS_SAVED_C1_C3_ARITHMETIC_WITH_C0_LIMITATION",
  "completed": [
    "frozen provenance and CSV serialization",
    "C0 saved H/Gram only; original C/A ledger unavailable",
    "C1 saved factor/projection ledgers and independent Q reference",
    "C2 saved factor/projection ledgers and independent Q reference",
    "C3 saved factor/projection ledgers and independent Q reference",
    "saved cross-case mechanism contrast"
  ],
  "limitations": [
    "original C0 C/A ledger unavailable",
    "original componentwise Qr not saved",
    "no actual E019 root cause or physical claim",
    "counter fields are self-report, not process audit"
  ],
  "scalar_checks": [
    {
      "case": "C0",
      "metric": "gram_defect_max",
      "saved": "2.8576781600238502723279871378722656898622590973527172401435353377E-16",
      "reference": "2.8576781600238502723279871378722656898622590973527172401435353377E-16",
      "delta": "0E-80",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "A_total_max",
      "saved": "0E-38",
      "reference": "0E-38",
      "delta": "0E-38",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_gram_defect_max",
      "saved": "0.0000",
      "reference": "0.0000",
      "delta": "0.0000",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_HtL_max",
      "saved": "0.0000",
      "reference": "0.0000",
      "delta": "0.0000",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_E_max",
      "saved": "0E-38",
      "reference": "0E-38",
      "delta": "0E-38",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_input_term_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_residual_term_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_input_amplified_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_residual_amplified_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_ledger_error_max",
      "saved": "0.0000",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "factor_reconstruction_max",
      "saved": "0",
      "reference": "0E-36",
      "delta": "0E-36",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C1",
      "metric": "p_existing_subspace_max_mm",
      "saved": "0",
      "reference": "0E-20",
      "delta": "0E-20",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "p_new_evaluation_max_mm",
      "saved": "0",
      "reference": "0E-20",
      "delta": "0E-20",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "r_new_subtraction_max_mm",
      "saved": "0",
      "reference": "0E-16",
      "delta": "0E-16",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "p_float_error_max_mm",
      "saved": "0E-18",
      "reference": "0E-18",
      "delta": "0E-18",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "r_float_error_max_mm",
      "saved": "0E-14",
      "reference": "0E-14",
      "delta": "0E-14",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "Htp_max_mm",
      "saved": "0E-11",
      "reference": "0E-11",
      "delta": "0E-11",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "Hty_max_mm",
      "saved": "0E-16",
      "reference": "0E-16",
      "delta": "0E-16",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "Htr_max_mm",
      "saved": "0E-16",
      "reference": "0E-16",
      "delta": "0E-16",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "Q_identity_max_mm",
      "saved": "0",
      "reference": "0",
      "delta": "0",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C1",
      "metric": "Q_identity_ratio",
      "saved": "0",
      "reference": "0",
      "delta": "0",
      "exact_match": true,
      "kind": "matrix",
      "saved_source": "producer_einsum_Qr_from_frozen_report",
      "reference_source": "independent_fsum_Qr_from_saved_H_r",
      "comparison_semantics": "additional_cross_path_scalar_check_not_implied_by_mm_vector_tolerance",
      "atol": 1e-12,
      "rtol": 1e-12
    },
    {
      "case": "C2",
      "metric": "A_total_max",
      "saved": "1.11022302462515654042363166809082031250000E-16",
      "reference": "1.11022302462515654042363166809082031250000E-16",
      "delta": "0E-57",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_gram_defect_max",
      "saved": "3.3087224502121106994856347682798514142632484436035156250E-24",
      "reference": "3.3087224502121106994856347682798514142632484436035156250E-24",
      "delta": "0E-79",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_HtL_max",
      "saved": "0.0000019073486328125000000000000000000000000",
      "reference": "0.0000019073486328125000000000000000000000000",
      "delta": "0E-43",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_E_max",
      "saved": "1.058791184067875423835403125849552452564239501953125E-22",
      "reference": "1.058791184067875423835403125849552452564239501953125E-22",
      "delta": "0E-73",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_input_term_max",
      "saved": "4.4408920985006261616945266723632812500000000E-16",
      "reference": "4.4408920985006261616945266723632812500000000E-16",
      "delta": "0E-59",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_residual_term_max",
      "saved": "0",
      "reference": "0E-59",
      "delta": "0E-59",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_input_amplified_max",
      "saved": "0.000001907348632812500000000",
      "reference": "0.000001907348632812500000000",
      "delta": "0E-27",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_residual_amplified_max",
      "saved": "0",
      "reference": "0E-59",
      "delta": "0E-59",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_ledger_error_max",
      "saved": "0.0000",
      "reference": "0E-59",
      "delta": "0E-59",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "factor_reconstruction_max",
      "saved": "0",
      "reference": "2.6469779601696885595885078146238811314105987548828125E-23",
      "delta": "-2.6469779601696885595885078146238811314105987548828125E-23",
      "exact_match": false,
      "kind": "matrix"
    },
    {
      "case": "C2",
      "metric": "p_existing_subspace_max_mm",
      "saved": "7.4505805969102755978439311945749068399891257286071777343750000000000000000000000E-9",
      "reference": "7.4505805969102755978439311945749068399891257286071777343750000000000000000000000E-9",
      "delta": "0E-88",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "p_new_evaluation_max_mm",
      "saved": "6.7762635780344027125465800054371356964111328125000000000000000000E-21",
      "reference": "6.7762635780344027125465800054371356964111328125000000000000000000E-21",
      "delta": "0E-85",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "r_new_subtraction_max_mm",
      "saved": "6.7762635780344027125465800054371356964111328125000E-21",
      "reference": "6.7762635780344027125465800054371356964111328125000E-21",
      "delta": "0E-70",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "p_float_error_max_mm",
      "saved": "3.3881350201914691415376449691587712464979631477035582065582275E-21",
      "reference": "3.3881350201914691415376449691587712464979631477035582065582275E-21",
      "delta": "0E-82",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "r_float_error_max_mm",
      "saved": "3.38813178901720135627329000271856784820556640625E-21",
      "reference": "3.38813178901720135627329000271856784820556640625E-21",
      "delta": "0E-68",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "Htp_max_mm",
      "saved": "7.4505805969170518614219655972874534199945628643035888671875000E-9",
      "reference": "7.4505805969170518614219655972874534199945628643035888671875000E-9",
      "delta": "0E-70",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "Hty_max_mm",
      "saved": "0E-16",
      "reference": "0E-16",
      "delta": "0E-16",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "Htr_max_mm",
      "saved": "7.45058059692382812500000000000000000000000E-9",
      "reference": "7.45058059692382812500000000000000000000000E-9",
      "delta": "0E-50",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "Q_identity_max_mm",
      "saved": "1.86264514923095703125E-9",
      "reference": "1.86264514923095703125E-9",
      "delta": "0E-29",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C2",
      "metric": "Q_identity_ratio",
      "saved": "1755501.13315377128310501575469970703125",
      "reference": "1755501.13315377128310501575469970703125",
      "delta": "0E-32",
      "exact_match": true,
      "kind": "matrix",
      "saved_source": "producer_einsum_Qr_from_frozen_report",
      "reference_source": "independent_fsum_Qr_from_saved_H_r",
      "comparison_semantics": "additional_cross_path_scalar_check_not_implied_by_mm_vector_tolerance",
      "atol": 1e-12,
      "rtol": 1e-12
    },
    {
      "case": "C3",
      "metric": "A_total_max",
      "saved": "0E-38",
      "reference": "0E-38",
      "delta": "0E-38",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_gram_defect_max",
      "saved": "3.3087224502121106994856347682798514142632484436035156250E-24",
      "reference": "3.3087224502121106994856347682798514142632484436035156250E-24",
      "delta": "0E-79",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_HtL_max",
      "saved": "0.0000019073486328125000000000000000000000000",
      "reference": "0.0000019073486328125000000000000000000000000",
      "delta": "0E-43",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_E_max",
      "saved": "1.110224083416340608299055503493946162052452564239501953125E-16",
      "reference": "1.110224083416340608299055503493946162052452564239501953125E-16",
      "delta": "0E-73",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_input_term_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_residual_term_max",
      "saved": "4.44089209850062616169452667236328125000000000000000000000000E-16",
      "reference": "4.44089209850062616169452667236328125000000000000000000000000E-16",
      "delta": "0E-75",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_input_amplified_max",
      "saved": "0",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_residual_amplified_max",
      "saved": "0.0000019073486328125000000000000000000000000",
      "reference": "0.0000019073486328125000000000000000000000000",
      "delta": "0E-43",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_ledger_error_max",
      "saved": "0.0000",
      "reference": "0E-40",
      "delta": "0E-40",
      "exact_match": true,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "factor_reconstruction_max",
      "saved": "2.77555756156289135105907917022705078125E-17",
      "reference": "2.7755602085408515207476387587348654051311314105987548828125E-17",
      "delta": "-2.6469779601696885595885078146238811314105987548828125E-23",
      "exact_match": false,
      "kind": "matrix"
    },
    {
      "case": "C3",
      "metric": "p_existing_subspace_max_mm",
      "saved": "7.4505805969102755978439311945749068399891257286071777343750000000000000000000000E-9",
      "reference": "7.4505805969102755978439311945749068399891257286071777343750000000000000000000000000E-9",
      "delta": "0E-88",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "p_new_evaluation_max_mm",
      "saved": "6.7762635780344027125465800054371356964111328125000000000000000000E-21",
      "reference": "6.7762635780344027125465800054371356964111328125000000000000000000E-21",
      "delta": "0E-85",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "r_new_subtraction_max_mm",
      "saved": "6.7762635780344027125465800054371356964111328125000E-21",
      "reference": "6.7762635780344027125465800054371356964111328125000E-21",
      "delta": "0E-70",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "p_float_error_max_mm",
      "saved": "3.3881350201914691415376449691587712464979631477035582065582275E-21",
      "reference": "3.3881350201914691415376449691587712464979631477035582065582275E-21",
      "delta": "0E-82",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "r_float_error_max_mm",
      "saved": "3.38813178901720135627329000271856784820556640625E-21",
      "reference": "3.38813178901720135627329000271856784820556640625E-21",
      "delta": "0E-68",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "Htp_max_mm",
      "saved": "7.4505805969170518614219655972874534199945628643035888671875000E-9",
      "reference": "7.4505805969170518614219655972874534199945628643035888671875000E-9",
      "delta": "0E-70",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "Hty_max_mm",
      "saved": "0E-16",
      "reference": "0E-16",
      "delta": "0E-16",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "Htr_max_mm",
      "saved": "7.45058059692382812500000000000000000000000E-9",
      "reference": "7.45058059692382812500000000000000000000000E-9",
      "delta": "0E-50",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "Q_identity_max_mm",
      "saved": "1.86264514923095703125E-9",
      "reference": "1.86264514923095703125E-9",
      "delta": "0E-29",
      "exact_match": true,
      "kind": "vector"
    },
    {
      "case": "C3",
      "metric": "Q_identity_ratio",
      "saved": "1755501.13315377128310501575469970703125",
      "reference": "1755501.13315377128310501575469970703125",
      "delta": "0E-32",
      "exact_match": true,
      "kind": "matrix",
      "saved_source": "producer_einsum_Qr_from_frozen_report",
      "reference_source": "independent_fsum_Qr_from_saved_H_r",
      "comparison_semantics": "additional_cross_path_scalar_check_not_implied_by_mm_vector_tolerance",
      "atol": 1e-12,
      "rtol": 1e-12
    }
  ],
  "source_sha256": {
    "docs/research/S03/S03-E019/subspace_localisation_plan.md": "adbe5d5c9dafbdef0f9db99c231dda5e25840401fd98cac6021b24b320f11be4",
    "docs/research/S03/S03-E019/experiment.md": "b956f21fa8c417d65d668ca876d91a35b04756c97318938eb95312e758b0cbde",
    "scripts/aa2024_kinematic_capacity.py": "4beb88d2a4b9aef20cc2c60face876f5469202c47b0f268bbc3efbd1cf3abaa7",
    "scripts/aa2024_geometry_prior.py": "0bb5c1c0689bca78021ba6cfbe0ed8979141bca665eabf68e7790f82da363fe5",
    "scripts/aa2024_boundary_basis.py": "da7862fb55674e8fa83f44334e3e821b4cb7a087ab04a4e09bd9ac9c3dc60b66",
    "scripts/aa2024_triplet_structure.py": "cf5e4b9dfc30e7c332af3900790694f0fe358225de525cca936c49c17df8b07c",
    "scripts/aa2024_patch_mechanics.py": "7b2299cb3baeb37b9bf7ef4879affbaa7088a0933779cbfca5552dc49bef7a39",
    "scripts/aa2024_rigid_observable.py": "ebfab2714a7cee1ce03405c4dfd5741eedb6ba4f1de5e4e94ca1525bf4f2199d",
    "scripts/aa2024_qsubspace_diagnostic.py": "3da24d94de4b18777898969dcf12e19f3442e1c1c3ca3dab4d5732d355c7843c",
    "tests/test_aa2024_qsubspace_diagnostic.py": "b73c200724f4e72afbe6628860d5de18771ce74490afd75499ac41a8eb204e36",
    "docs/research/S03/S03-E019/subspace_test_design.md": "cb76d82c6303964ab3ded5b875a50180c058b93cadef0f3d657304a3eda1156d"
  },
  "head": "e75d3a8add790a7dc8349491cf656c2f775a3c24",
  "elapsed_before_stdout_seconds": 0.37604833295335993
}
```

## 主代理有限接收

仅将保存C1–C3账本及C0 H/Gram的有限核验记为完成。保留两个非逐位一致
的因子重构标量，不把原C2保存0写成高精度参考严格0；不把预定负控原Q
不通过写成整次失败。合成对照中相同p/r、不同A的现象获此独立核对支持，
仍不足以从真实p/r唯一倒推根因。C0原A层、原逐分量Qr和真实E019限制
继续有效。本轮不自动开启任何真实访问、producer修复、再诊断或新求解。
