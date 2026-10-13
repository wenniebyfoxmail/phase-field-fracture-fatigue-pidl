#!/usr/bin/env python3
"""Summarize independently restarted same-peak control experiments, not a rollout."""
import argparse,json,csv
from pathlib import Path
import numpy as np,matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--report',type=Path);args=ap.parse_args()
    out=args.run/'analysis';out.mkdir(exist_ok=True);rows=[];pending=[]
    for cycle in [1,20,60,76,82,83]:
        p=args.run/f'states/c{cycle}/analysis/summary.json'
        if not p.exists():pending.append(cycle);continue
        s=json.loads(p.read_text());
        if s['physical_cycle']!=cycle:raise ValueError('Summary cycle mismatch')
        b=s['baseline'];f=s['last_completed'];lam=[t['lambda'] for t in s['trial_trace'] if t['accepted']]
        rows.append({'cycle':cycle,'status':s['status'],'baseline_iterations':b['outer_iteration'],'accepted_extras':s['completed_extra_iterations'],'trial_count':s['trial_count'],
          'min_accepted_lambda':min(lam) if lam else None,'residual_baseline':b['projected_sum'],'residual_final':f['projected_sum'],'residual_ratio':s['residual_ratio'],
          'active_gap_baseline':b['active_gap_relative_l2'],'active_gap_final':f['active_gap_relative_l2'],'absolute_active_gap_ratio':s['active_gap_absolute_norm_ratio'],
          'corr_baseline':b['active_gap_correlation'],'corr_final':f['active_gap_correlation'],'damage_max_change':f['damage_max_abs_change']})
    with (out/'grid_metrics.csv').open('w',newline='') as h:
        if rows:wr=csv.DictWriter(h,fieldnames=rows[0]);wr.writeheader();wr.writerows(rows)
    summary={'schema':'independent-peak-control-grid-v1','pending_cycles':pending,'rows':rows,'scope':'same original s3 predecessor per cycle, not a modified propagated trajectory; no history commits, no teacher or truth qualification'}
    (out/'grid_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    if rows:
        x=[r['cycle'] for r in rows];fig,axs=plt.subplots(2,2,figsize=(10,7),sharex=True)
        for name,ax,label in [('residual',axs[0,0],'native feasible residual sum'),('active_gap',axs[0,1],'weighted active relative L2 vs unchanged PIDL')]:
            for suffix,color in [('baseline','#0072B2'),('final','#D55E00')]:
                ax.plot(x,[r[name+'_'+suffix] for r in rows],'-o',color=color,label=suffix)
            ax.set_ylabel(label);ax.legend()
        axs[0,0].set_yscale('log');axs[0,0].axhline(4e-6,color='gray',linestyle='--')
        axs[1,0].plot(x,[r['min_accepted_lambda'] for r in rows],'-o');axs[1,0].set_yscale('log');axs[1,0].set_ylabel('smallest accepted joint step')
        axs[1,1].plot(x,[r['absolute_active_gap_ratio'] for r in rows],'-o');axs[1,1].axhline(1,color='gray',linestyle='--');axs[1,1].set_ylabel('absolute active gap / baseline gap')
        for r in rows:
            if r['cycle']>=76:
                offset=(-28,8) if r['cycle']==76 else ((-32,-17) if r['cycle']==82 else (-30,7))
                axs[1,0].annotate(f"c{r['cycle']}",(r['cycle'],r['min_accepted_lambda']),xytext=offset,textcoords='offset points',fontsize=8)
                axs[1,1].annotate(f"c{r['cycle']}",(r['cycle'],r['absolute_active_gap_ratio']),xytext=offset,textcoords='offset points',fontsize=8)
        for ax in axs.flat:ax.grid(alpha=.25)
        for ax in axs[1]:ax.set_xlabel('independently restarted physical peak cycle')
        fig.suptitle('Native Q4 same-state control sensitivity (no propagated history updates)');fig.tight_layout();fig.savefig(out/'backtrack_cycle_comparison.png',dpi=200);plt.close(fig)
    table='| cycle | 状态 | 接受步数 / trial | 最小λ | M末 / 基线 | active相对场差：前→后 | 绝对场差倍数 |\n|---|---|---:|---:|---:|---:|---:|\n'
    for r in rows:
        ml=f"{r['min_accepted_lambda']:.5g}" if r['min_accepted_lambda'] is not None else '无'
        table+=f"|c{r['cycle']}|{r['status']}|{r['accepted_extras']} / {r['trial_count']}|{ml}|{r['residual_ratio']:.4f}|{100*r['active_gap_baseline']:.2f}%→{100*r['active_gap_final']:.2f}%|{r['absolute_active_gap_ratio']:.4f}|\n"
    text=f'''### 2026-10-13 回溯与早期cycle判别结果（动态核验表）\n\n{table}\n\n待完成或待核验cycle：{pending if pending else '无'}。每个cycle从原始轨迹自己的accepted s3重新开始，仅求s4峰值；这些点不是一条传播了修改history的新轨迹。M为native自由位移＋nodal-monotone可行damage残差和，目标4e-6；PIDL为原Q4同cycle峰值step5c−1。active相对L2用当前FEM作分母，绝对场差倍数固定原基线分母，均用native GP4积分权重。\n\n最小λ=1的case没有触发阻尼，效果来自收紧/继续block solve的组合控制，不能单独归因line-search。NO_ADMISSIBLE_DESCENT表示预定七档无下降，EXTRA_BUDGET_EXHAUSTED表示10步结束；都不等于收敛或无解。原E003/E011输出保留，无history commit。这里只报告已核验完整端点，拒绝trial不混入场比较。\n\n证据：`{args.run}`各states/c*/analysis、retrieval_verification.json；汇总CSV/JSON在analysis/。\n'''
    (out/'decision.md').write_text(text)
    note=f'''# Same-state backtracking cycle comparison\n\nQuestion: how does control sensitivity differ before and near the late event?\n\nData provenance: grid_metrics.csv/grid_summary.json aggregate verified per-state summaries in {args.run}/states/c*/analysis. Source and raw hashes are in those summaries; each restored original baseline passed its own archived iteration/field/residual gate. Pending states {pending} are excluded.\n\nHow to read: top left native M before/after on logscale (gray4e-6 diagnostic screen); top right active relative L2 vs original PIDL at step5c−1; bottom left minimum accepted lambda; bottom right absolute active gap norm ratio relative to original same-cycle baseline (gray1). Blue original, orange control. Connecting lines guide the eye; unsampled cycles are not interpolated evidence.\n\nMain numerical takeaway: {json.dumps(rows)}.\n\nLimitations and claim boundary: sparse original-trajectory restarts, not a forward modified trajectory or independent specimens. Lambda1 means no damping activated; improvements then belong to combined tighter controls/extra iterations. Residual convergence does not imply PIDL alignment or truth. Stalled/exhausted states remain unqualified.\n'''
    (out/'backtrack_cycle_comparison.md').write_text(note)
    if args.report:
        start='<!-- BEGIN backtrack_grid_e8c57e3 -->';end='<!-- END backtrack_grid_e8c57e3 -->';old=args.report.read_text();block=start+'\n'+text+'\n'+end
        if start in old:
            before,rest=old.split(start,1);_,after=rest.split(end,1);new=before+block+after
        else:new=old+'\n\n'+block+'\n'
        args.report.write_text(new)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
