# U0.115 PINN metadata查找receipt

日期2026-10-12。只读metadata/目录查询，未反序列化checkpoint、未加载科学数组、未计算Delta。
不是producer Run；不申请/占用GPU，无远程文件写入。

本地精确amplitude-path查询：

```sh
rg --files local_archive/after_strict_setting_alignment/pidl_result | rg -i '(/[^/]*(Umax0[.]115|_U0[.]115|umax0115|u0115)[^/]*/)'
```

在parent project root执行；count0。existing contract和data lock逐条只读，IDs .11/.12/.13。

Taobo connection由project `docs/taobo_gpu_submission_protocol.md`确认：
`drtao@172.16.100.2`；SSH `-F /dev/null -o BatchMode=yes -o ConnectTimeout=8
-o ServerAliveInterval=5 -o ServerAliveCountMax=1`。两次command均exit0。

第一项remote command：

```sh
hostname
find /mnt/data2/drtao/pidl_archives /mnt/data2/drtao/wennie /mnt/data2/drtao/projects -maxdepth 4 -type d \( -iname "*u0.115*" -o -iname "*u0115*" -o -iname "*umax0115*" -o -iname "*umax0.115*" \) -print
```

返回仅 `GPUServer8`，目录match0；exec session98536，exit0。

第二项remote command：

```sh
find /mnt/data2/drtao/pidl_archives /mnt/data2/drtao/wennie /mnt/data2/drtao/projects -maxdepth 6 -type f -name model_settings.txt -exec awk 'FNR==1 {files++} /^[[:space:]]*(umax|Umax)[[:space:]:=]+0\.115([^0-9]|$)/ {print FILENAME ":" FNR ":" $0; matches++} END {print "model_settings_files_scanned=" files "; exact_umax0115_matches=" (matches+0)}' {} +
```

返回：`model_settings_files_scanned=477; exact_umax0115_matches=0`；session26886，exit0。
逐文件只读text settings；不读取checkpoint内容。范围/depth/name/field限制使全远程不存在
不能从此推出。无额外磁盘/legacy root查询，没有Windows访问。

排除的本地false candidate：`recovery_monoU02_b6d5610_20260701_141419`，settings明确
umax0.2、cycles1、24个monotonic absolute displacement substeps；0.115是中间加载点。
同case本地checkpoint filenames实际列出step0--16（17个）；settings声明training steps25，
因此该本地copy连预期step0--24的完整coverage也未由本次metadata证据证明。不能从此推断
远程运行一定提前停止或文件损坏。这只说明该单调序列的本地filename coverage，
不是Umax0.115 fatigue trajectory，更不是qualified matched asset。

查找结论：U0.115完整matched PINN qualification目前未建立。已存在FEM并不关闭此缺项。
完整原settings/source路径和下一qualification字段见同目录method review。
