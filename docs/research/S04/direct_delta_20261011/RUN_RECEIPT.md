# S04-direct-delta-D003：本地描述性诊断 receipt

- Owner / primary storyline：S04 direct-Delta preparation；非claim-changing模型实验。
- Branch/base：`codex/s04-direct-delta-audit-20261011` / `5b1eec29d2bed37d42baab5850ceb9c57ae16249`。
- Producer/runtime：Mac本地，Python3.12，NumPy/Matplotlib；`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`。
- Runner：`SENS_tensile/audit_direct_delta_cycles.py`，runtime SHA256与hostname/start time见下述immutable archive receipt。
- Command：`python3 -W error SENS_tensile/audit_direct_delta_cycles.py --input-lock '/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/research/S04/S04-E013/input_lock.json' --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis`。
- Execution/retrieval：succeeded / local verified；elapsed12.546seconds。工具等待session22033已返回exit0。
- Scientific verdict：无新模型科学verdict，描述数据与修订设计；independent Code/Evidence Ready review未进行。
- Inputs：11个旧external data-lock文件SHA匹配；3Umax；264配对cycle；86,408共同Q4cells。
- Outputs：264row paired_cycle_index、1320row cycle_delta_metrics、15row pre-event_summary、
  coverage/bounds/nonlinear-reduction tables、两张图和cycle图PDF。
- Archive：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/receipt.json`。
- Preceding diagnostics：D001原max色轴不能清晰看history；D002调整显示色限并增加source index；
  D003增加mapping-contained/fallback分层。它们均无训练，所有旧输出保留。
- Validation：weighted RMS/correlation/Carrara函数的analytical checks；warnings-as-errors全流程；
  output264唯一cycle keys、每physical/raw-log channel264rows、finite contained-RMSE；图实际打开核查。
- Protected scope：未访问Windows、U0.1175payload、旧c64partial或U0.125；无producer/train启动。
- Next action：development配对timing/reduction和U0.115既有PINNcheckpoint可用性审计，详见protocol。
