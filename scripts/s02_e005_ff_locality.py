"""Descriptive FF localisation from frozen increments. No models or fitting."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import resource
import signal
import socket
import subprocess
import sys
import time

import s02_e005_label_sensitivity as prior

PHASES = ['alternating_positive', 'alternating_negative']
EPS = [0, .00214, .00428, .00856, .01712, .03424, .06848]


def check(ok, message):
    if not ok:
        raise ValueError(message)


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def csv_rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def low_set(rows, key, count):
    return {r['origin_cycle'] for r in sorted(rows, key=lambda r: (r[key], r['origin_cycle']))[:count]}


def projection(x):
    return 'before' if x < 22.5 else ('over_projection' if x <= 27.5 else 'after')


def interval_distance(y, q0, q1):
    lo, hi = sorted([q0, q1])
    return max(lo-y, y-hi, 0.)


def edge_values(row, errors):
    y, q0, q1 = (row[k] for k in ['target_dx_mm', 'M0_dx_mm', 'M1_dx_mm'])
    delta = errors[row['target_cycle']] - errors[row['origin_cycle']]
    d0 = abs(q1-y)-abs(q0-y)
    de = abs(q1-y-delta)-abs(q0-y-delta)
    shift = de-d0
    return d0, de, shift, max(-shift, 0.), max(shift, 0.), delta


def validate_config(c):
    expected = {'experiment_id':'S02-E005', 'amendment_id':'S02-E005-A002',
        'revision':'v1', 'run_id':'S02-E005-R003', 'epsilon_mm':EPS,
        'primary_epsilon_mm':.06848, 'scenarios':PHASES,
        'hole_center_mm':[25,0], 'hole_radius_mm':2.5,
        'projection_band_mm':[22.5,27.5], 'low_growth_count':11, 'top_k':5,
        'tolerance_mm':1e-10, 'training':False, 'fitting':False,
        'model_forward':False, 'original_negative_unchanged':True,
        'wall_seconds':60, 'observed_rss_limit_mb':1024}
    for k, v in expected.items():
        check(c[k] == v, 'config contract: '+k)


def exact_cycle(text):
    value=Decimal(text)
    check(value.is_finite() and value==value.to_integral_value(), 'noninteger source cycle')
    return int(value)


def tip_map(path):
    tips={}
    for r in csv_rows(path):
        n=exact_cycle(r['n [cycle]'])
        check(n not in tips, 'duplicate source cycle')
        xy=(float(r['x [mm]']), float(r['y [mm]']))
        check(all(math.isfinite(v) for v in xy), 'nonfinite source coordinate')
        tips[n]=xy
    return tips


def localise(rows, tips, previous_scenarios, cfg):
    check(len(rows)==33, 'FF row count')
    tol=cfg['tolerance_mm']
    low_past=low_set(rows, 'B1_dx_mm', 11)
    low_realised=low_set(rows, 'target_dx_mm', 11)
    details=[]
    for epsilon in EPS:
        errors={p:prior.node_errors(prior.nodes(rows), epsilon, p) for p in PHASES}
        for row in rows:
            n,t=row['origin_cycle'],row['target_cycle']
            check(n in tips and t in tips, 'missing exact coordinate key')
            x,y=tips[n]; tx,ty=tips[t]
            check(abs(x-row['current_x_mm'])<=tol and abs(tx-x-row['target_dx_mm'])<=tol,
                  'source coordinate mismatch')
            for p in PHASES:
                d0,de,shift,lower,offset,dy=edge_values(row, errors[p])
                details.append({'epsilon_mm':epsilon, 'scenario':p, **row,
                    'origin_y_mm':y, 'target_x_mm':tx, 'target_y_mm':ty,
                    'origin_hole_projection':projection(x),
                    'origin_hole_edge_distance_mm':math.hypot(x-25,y)-2.5,
                    'low_past_growth':n in low_past, 'low_realised_growth':n in low_realised,
                    'label_increment_shift_mm':dy, 'd0_mm':d0, 'd_phase_mm':de,
                    'signed_shift_mm':shift, 'lowering_mm':lower, 'offset_mm':offset,
                    'target_to_prediction_interval_mm':interval_distance(row['target_dx_mm'],row['M0_dx_mm'],row['M1_dx_mm'])})
        for p in PHASES:
            rs=[r for r in details if r['epsilon_mm']==epsilon and r['scenario']==p]
            old=[r for r in previous_scenarios if r['record']=='FF' and float(r['epsilon_mm'])==epsilon and r['scenario']==p]
            check(len(rs)==33 and len(old)==1, 'scenario identity/count')
            check(abs(math.fsum(r['d_phase_mm'] for r in rs)/33-float(old[0]['D_mm']))<=tol,
                  'R002 D reproduction failed')
            for arm in prior.ARMS:
                sc=prior.scores(rows,errors[p])
                check(abs(sc[arm]-float(old[0][arm]))<=tol, 'R002 arm reproduction failed')
            check(abs(math.fsum(r['signed_shift_mm'] for r in rs)-
                      (math.fsum(r['offset_mm'] for r in rs)-math.fsum(r['lowering_mm'] for r in rs)))<=tol,
                  'mass decomposition failed')
    primary=[r for r in details if r['epsilon_mm']==cfg['primary_epsilon_mm']]
    by_n={r['origin_cycle']:{} for r in rows}
    for r in primary:
        by_n[r['origin_cycle']][r['scenario']]=r
    ranking=[]
    for n, ps in by_n.items():
        a,b=(ps[p] for p in PHASES)
        ranking.append({k:a[k] for k in ['origin_cycle','target_cycle','current_x_mm','origin_y_mm',
            'target_x_mm','target_y_mm','origin_hole_projection','origin_hole_edge_distance_mm',
            'B1_dx_mm','target_dx_mm','low_past_growth','low_realised_growth','M0_dx_mm','M1_dx_mm',
            'target_to_prediction_interval_mm']} | {
            'mean_lowering_mm':(a['lowering_mm']+b['lowering_mm'])/2,
            'positive_phase_shift_mm':a['signed_shift_mm'],
            'negative_phase_shift_mm':b['signed_shift_mm'],
            'd0_mm':a['d0_mm']})
    ranking.sort(key=lambda r:(-r['mean_lowering_mm'],r['origin_cycle']))
    for j,r in enumerate(ranking,1):
        r['rank']=j
    group_table=[]
    for p in PHASES:
        rs=[r for r in primary if r['scenario']==p]
        total=math.fsum(r['lowering_mm'] for r in rs)
        sets=[('all',rs)]
        sets += [('hole_'+g,[r for r in rs if r['origin_hole_projection']==g]) for g in ['before','over_projection','after']]
        sets += [('low_past',[r for r in rs if r['low_past_growth']]),
                 ('other_past',[r for r in rs if not r['low_past_growth']]),
                 ('low_realised_retrospective',[r for r in rs if r['low_realised_growth']]),
                 ('other_realised_retrospective',[r for r in rs if not r['low_realised_growth']])]
        for name,gs in sets:
            lowering=math.fsum(r['lowering_mm'] for r in gs)
            share=lowering/total if total else 0.
            group_table.append({'scenario':p,'group':name,'count':len(gs),'window_share':len(gs)/33,
                'lowering_sum_mm':lowering,'offset_sum_mm':math.fsum(r['offset_mm'] for r in gs),
                'lowering_share':share,'mean_lowering_mm':lowering/len(gs) if gs else None,
                'share_over_window_share':share/(len(gs)/33) if gs else None,
                'baseline_mean_d_mm':math.fsum(r['d0_mm'] for r in gs)/len(gs) if gs else None})
    phase_summaries={}
    top={r['origin_cycle'] for r in ranking[:5]}
    for p in PHASES:
        rs=[r for r in primary if r['scenario']==p]
        lo=math.fsum(r['lowering_mm'] for r in rs); up=math.fsum(r['offset_mm'] for r in rs)
        phase_summaries[p]={'D0_mm':math.fsum(r['d0_mm'] for r in rs)/33,
            'D_phase_mm':math.fsum(r['d_phase_mm'] for r in rs)/33,
            'net_shift_mm':(up-lo)/33,'lowering_sum_mm':lo,'offset_sum_mm':up,
            'lowering_window_count':sum(r['lowering_mm']>tol for r in rs),
            'changed_window_count':sum(abs(r['signed_shift_mm'])>tol for r in rs),
            'top5_lowering_share':math.fsum(r['lowering_mm'] for r in rs if r['origin_cycle'] in top)/lo}
    total_v=math.fsum(r['mean_lowering_mm'] for r in ranking)
    summary={'run_id':cfg['run_id'],'amendment':cfg['amendment_id'],'diagnostic':'post-result descriptive only',
        'epsilon_mm':cfg['primary_epsilon_mm'],'phases':phase_summaries,
        'top5':ranking[:5], 'top5_mean_lowering_share':math.fsum(r['mean_lowering_mm'] for r in ranking[:5])/total_v,
        'low_past_max_mm':max(r['B1_dx_mm'] for r in rows if r['origin_cycle'] in low_past),
        'low_realised_max_mm':max(r['target_dx_mm'] for r in rows if r['origin_cycle'] in low_realised),
        'low_set_overlap_count':len(low_past & low_realised),
        'source_join':'exact original cycle keys; both x endpoints verified',
        'r002_reproduced':True,'original_negative_unchanged':True,
        'training':False,'fitting':False,'model_forward':False,'uncertainty_calibrated':False}
    return details,ranking,group_table,summary


def plot(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    rs=csv_rows(out/'windows_ranked.csv')
    for r in rs:
        for k in ['origin_cycle','current_x_mm','origin_y_mm','target_dx_mm','B1_dx_mm','M0_dx_mm','M1_dx_mm',
                  'mean_lowering_mm','positive_phase_shift_mm','negative_phase_shift_mm']:
            r[k]=float(r[k])
    rs.sort(key=lambda r:r['origin_cycle'])
    fig,axs=plt.subplots(2,2,figsize=(14,9))
    cycles=[r['origin_cycle']/1000 for r in rs]
    for key,c,marker,label in [('target_dx_mm','#222222','o','Observed target'),('B1_dx_mm','#009E73','+','B1 past secant'),
                               ('M0_dx_mm','#0072B2','s','M0'),('M1_dx_mm','#D55E00','^','M1 history')]:
        axs[0,0].scatter(cycles,[r[key] for r in rs],s=24,color=c,marker=marker,label=label)
    axs[0,0].set(xlabel='Origin cycle (thousands)',ylabel='1000-cycle increment (mm)',title='A | All 33 frozen evaluation windows')
    axs[0,0].legend(fontsize=8)
    for key,c,marker,label in [('positive_phase_shift_mm','#0072B2','o','Alternating + phase'),
                               ('negative_phase_shift_mm','#D55E00','^','Alternating - phase')]:
        axs[0,1].scatter(cycles,[r[key]*1000 for r in rs],color=c,s=26,marker=marker,label=label)
    axs[0,1].axhline(0,color='black',lw=.7)
    axs[0,1].set(xlabel='Origin cycle (thousands)',ylabel='Change in per-window d (micrometres)',title='B | Negative shifts lower M1-minus-M0')
    axs[0,1].legend(fontsize=8)
    ax=axs[1,0]
    ax.add_patch(Circle((25,0),2.5,facecolor='#dddddd',edgecolor='#555555'))
    ax.axvspan(22.5,27.5,color='#cccccc',alpha=.18,label='Hole x projection')
    points=ax.scatter([r['current_x_mm'] for r in rs],[r['origin_y_mm'] for r in rs],
                      c=[r['mean_lowering_mm']*1000 for r in rs],s=48,cmap='viridis',vmin=0)
    ax.set(xlabel='Origin tip x (mm)',ylabel='Origin tip y (mm)',title='C | Actual origin coordinates; hole centre (25, 0)')
    ax.set_aspect('equal',adjustable='datalim')
    fig.colorbar(points,ax=ax,label='Mean gross lowering, two phases (micrometres)',shrink=.8)
    ax.legend(fontsize=8,loc='lower left')
    for r in rs:
        if int(r['rank'])<=5:
            ax.annotate(str(int(r['origin_cycle'])),(r['current_x_mm'],r['origin_y_mm']),xytext=(2,5),textcoords='offset points',fontsize=7)
    ax=axs[1,1]
    for low,c,label in [('True','#0072B2','Lowest 11 past increments'),('False','#777777','Other 22 past increments')]:
        subset=[r for r in rs if r['low_past_growth']==low]
        ax.scatter([r['B1_dx_mm'] for r in subset],[r['mean_lowering_mm']*1000 for r in subset],c=c,s=30,label=label)
    ax.set(xlabel='Frozen B1 past 1000-cycle increment (mm)',ylabel='Mean gross lowering (micrometres)',title='D | Evaluation-relative low growth; descriptive')
    ax.legend(fontsize=8)
    for ax in axs.flat:
        ax.grid(alpha=.15)
    fig.suptitle('S02-E005-R003 | FF frozen-prediction sensitivity localisation | epsilon = 68.48 micrometres\n'
        'Development-exposed labels; both existing phases; no refit; hypothetical errors; original negative unchanged',fontsize=11)
    fig.tight_layout(rect=[0,0,1,.92])
    fig.savefig(out/'ff_locality.png',dpi=170)
    plt.close(fig)


def report(s, groups):
    lines=['# FF frozen-prediction sensitivity localisation','',
        'Question: where do the two existing FF alternating-error reversals arise, and how do they co-occur with position and growth?',
        'Evidence: R001 frozen predictions and published labels; R002 fixed seven radii and both alternating phases; A002 v1. Controlled experiment, one FF specimen, all33 development-exposed evaluation windows. No refit or model forward.', '',
        'Read: ff_locality.png A (observed and frozen B1/M0/M1), B (both signed shifts), C (public CSV coordinates and hole), D (past growth). Exact values: windows_ranked.csv, all_radius_windows.csv and groups.csv.', '',
        '## Contributions at the existing maximum radius','',
        '| Phase | Original D mm | Perturbed D mm | Gross lowering sum mm | Offsetting sum mm | Top5 lowering share |',
        '|---|---:|---:|---:|---:|---:|']
    for p,r in s['phases'].items():
        lines.append(f"| {p} | {r['D0_mm']:.9f} | {r['D_phase_mm']:.9f} | {r['lowering_sum_mm']:.9f} | {r['offset_sum_mm']:.9f} | {r['top5_lowering_share']:.2%} |")
    lines+=['','Top5 rule: mean gross lowering over BOTH phases, fixed k=5, origin-cycle tie break. Shares use gross lowering rather than net shift. All33 remain scored.','',
        '| Origin -> target | Origin x mm | Past dx mm | Target dx mm | Mean lowering mm | Origin hole projection |',
        '|---|---:|---:|---:|---:|---|']
    for r in s['top5']:
        lines.append(f"| {r['origin_cycle']} -> {r['target_cycle']} | {r['current_x_mm']:.4f} | {r['B1_dx_mm']:.4f} | {r['target_dx_mm']:.4f} | {r['mean_lowering_mm']:.9f} | {r['origin_hole_projection']} |")
    lines+=['','## Geometry and growth comparisons','',
        '| Phase | Group | N | Window share | Gross lowering share | Share / window share |',
        '|---|---|---:|---:|---:|---:|']
    for r in groups:
        ratio='NA' if r['share_over_window_share'] is None else f"{r['share_over_window_share']:.3f}"
        lines.append(f"| {r['scenario']} | {r['group']} | {r['count']} | {r['window_share']:.2%} | {r['lowering_share']:.2%} | {ratio} |")
    lines += ['',f"Low past cutoff (relative lowest11/33)={s['low_past_max_mm']:.9f} mm; retrospective target cutoff={s['low_realised_max_mm']:.9f} mm; overlap={s['low_set_overlap_count']}/11.", '',
        '## Allowed and blocked conclusions; storyline impact','',
        'These tables localise a deterministic scoring phenomenon on the existing FF tail. Larger lowering share than window share indicates descriptive concentration only. Time, position and growth co-vary in this single dependent trajectory; no causal or population inference is identifiable.',
        'Projection overlap [22.5,27.5] is defined from origin x and does not mean proximity to the physical hole edge. The CSV gives Euclidean origin-tip-to-hole-edge distance separately. Target geometry is retrospective, not input context.',
        'The low-growth groups are exposed evaluation-tail ranks, not a calibrated physical regime or new predictor. The realised target group is retrospective and mathematically related to label-error sensitivity; it cannot independently establish a growth mechanism.',
        'Per-edge d(y) is constant outside the interval of the two predictions on either side. Moving a hypothetical label through that interval changes the score difference. Prediction spacing, target alignment and error phase can explain concentration algebraically, without evidence that actual labels are noisy.',
        'The assumed 68.48 micrometre coordinate bound is uncalibrated. Alternation is a witness, not a measured or likely error process. No label correction, removal of windows, retraining benefit, physical hole effect, true tip accuracy or road generalisation follows.',
        'R001 negative verdict, R002 results and equal-record primary criterion remain unchanged. Stop after the fixed descriptive diagnostic; await author timing/processing and repeatability evidence before any physical attribution or new modelling.', '']
    return '\n'.join(lines)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',type=Path,required=True)
    ap.add_argument('--authorization',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    cfg=prior.read_json(args.config); validate_config(cfg)
    auth=prior.read_json(args.authorization)
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    check(auth['code_commit']==head and auth['code_review']=='CODE_REVIEW_PASS' and
          auth['protocol_review']=='PROTOCOL_REVIEW_PASS' and
          auth['scope']=='frozen_FF_localisation_only' and auth['training_authorized'] is False,'review/authority absent')
    check(not subprocess.check_output(['git','status','--porcelain'],text=True).strip(),'dirty worktree')
    out=args.out.resolve()
    check(not out.exists(),'output exists')
    source=Path(cfg['input_root']); old=Path(cfg['r002_root']); data=Path(cfg['source_data'])
    for root in [source,old,data]:
        check(root!=out and root not in out.parents and out not in root.parents,'input-output overlap')
    start=time.monotonic(); started=datetime.now(timezone.utc).isoformat()
    def timeout(*_):
        raise TimeoutError('60 second analysis cap')
    signal.signal(signal.SIGALRM,timeout); signal.alarm(60)
    paths=[source/n for n in ['predictions.csv','prepared.json','summary.json']]
    paths += [old/n for n in ['scenarios.csv','bounds.csv','summary.json','execution_receipt.json']]
    paths += [data/n for n in prior.read_json(Path(cfg['data_lock']))]
    originals={p:p.read_bytes() for p in paths}
    pc=prior.read_json(Path(cfg['prior_config'])); prior.validate_config(pc)
    groups=prior.validate_inputs(source,pc,data,prior.read_json(Path(cfg['data_lock'])))
    details,ranked,gt,summary=localise(groups['FF'],tip_map(data/'FF-cracktip.csv'),csv_rows(old/'scenarios.csv'),cfg)
    out.mkdir(parents=True)
    write_csv(out/'all_radius_windows.csv',details)
    write_csv(out/'windows_ranked.csv',ranked)
    write_csv(out/'groups.csv',gt)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    plot(out)
    text=report(summary,gt)
    (out/'README_analysis.md').write_text(text)
    (out/'ff_locality.md').write_text(text)
    for p,raw in originals.items():
        check(p.read_bytes()==raw,'source modified: '+str(p))
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
    check(rss<=1024,'observed memory budget exceeded')
    receipt={'run_id':cfg['run_id'],'code_commit':head,'dirty_status':'clean at launch',
        'hostname':socket.gethostname(),'pid':os.getpid(),'producer':'Mac local CPU deterministic analysis',
        'start_utc':started,'elapsed_seconds':time.monotonic()-start,'peak_rss_mb':rss,
        'command':sys.argv,'python':sys.version,'authorization':auth,
        'input_paths':[str(p) for p in paths],'input_files_unchanged':True,
        'input_files_checked':len(paths),'execution_status':'succeeded','retrieval':'local verified',
        'all_radius_rows':len(details),'ranking_rows':len(ranked),'group_rows':len(gt),
        'out':str(out),'training':False,'fitting':False,'model_forward':False,
        'budget':'60s alarm; peak RSS observed after execution, not OS hard cap'}
    (out/'execution_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
