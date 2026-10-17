"""Render fixed six endpoint diagnostic outputs; never load/update model weights."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

STATES=('c20s4','c60s4','c83s4')
COLORS={'E022':'#27825c','E023':'#984ea3'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.case/'results/summary.json').read_text());rr=data['results'];assert len(rr)==6
    out=a.case/'analysis';out.mkdir(exist_ok=True)
    rows=[];heads=[];gradients=[];activations=[]
    for r in rr:
        h={x['region']:x for x in r['head'] if x['coordinate']=='physical'};g={x['group']:x for x in r['gradients'] if x['coordinate']=='actual'}
        act=next(x for x in r['activations'] if x['layer']==7 and x['region']=='damage')
        rows.append(dict(state=r['state'],arm=r['arm'],full_rms=r['full_rms'],damage_rms=r['regional_rms']['damage'],inside_background_rms=r['regional_rms']['background_inside'],
            damage_effective_ever_units=act['effective_ever_units'],damage_active_fraction=act['active_fraction'],damage_gram_rank_1e_8=h['damage']['rank_relative_1e_8'],damage_gram_entropy=h['damage']['entropy_rank'],
            head_scaled_normal_full=h['full']['scaled_normal_residual'],head_scaled_normal_damage=h['damage']['scaled_normal_residual'],head_scaled_normal_inside=h['background_inside']['scaled_normal_residual'],head_max_feature_correlation=h['full']['max_feature_residual_correlation'],
            all_damage_inside_cos=g['all']['damage_inside_cosine'],hidden_damage_inside_cos=g['hidden']['damage_inside_cosine'],head_damage_inside_cos=g['head']['damage_inside_cosine'],
            all_damage_norm=g['all']['damage_norm'],all_inside_norm=g['all']['inside_background_norm'],head_full_norm=g['head']['full_norm'],hidden_full_norm=g['hidden']['full_norm'],
            all_damage_dot_full=g['all']['damage_dot_full_gradient'],all_inside_dot_full=g['all']['inside_background_dot_full_gradient'],damage_outside_nodes=r['damage_outside_nodes'],damage_outside_loss=r['damage_outside_loss_contribution'],peak_rss_bytes=r['peak_rss_bytes']))
        for x in r['head']:heads.append(dict(state=r['state'],arm=r['arm'],**{k:v for k,v in x.items() if k!='eigenvalues'}))
        gradients.extend(dict(state=r['state'],arm=r['arm'],**x) for x in r['gradients'])
        activations.extend(dict(state=r['state'],arm=r['arm'],**x) for x in r['activations'])
    for name,table in [('diagnostic_summary',rows),('head_stationarity',heads),('regional_gradients',gradients),('activations',activations)]:
        with (out/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for i,state in enumerate(STATES):
        for arm,col in COLORS.items():
            r=next(x for x in rr if x['state']==state and x['arm']==arm)
            head={x['region']:x for x in r['head'] if x['coordinate']=='physical'};grad={x['group']:x for x in r['gradients'] if x['coordinate']=='actual'}
            axes[0,i].plot(range(3),[head[k]['scaled_normal_residual'] for k in ('damage','background_inside','full')],'o-',color=col,label=arm+' physical')
            actual={x['region']:x for x in r['head'] if x['coordinate']=='actual'}
            axes[0,i].plot(range(3),[actual[k]['scaled_normal_residual'] for k in ('damage','background_inside','full')],'x--',color=col,label=arm+' actual')
            axes[1,i].plot(range(3),[grad[k]['damage_inside_cosine'] for k in ('all','hidden','head')],'o-',color=col,label=arm+' actual')
            physical={x['group']:x for x in r['gradients'] if x['coordinate']=='physical'}
            axes[1,i].plot(range(3),[physical[k]['damage_inside_cosine'] for k in ('all','hidden','head')],'x--',color=col,label=arm+' physical')
        axes[0,i].set(title=state+': output-head residual',xticks=range(3),xticklabels=['damage','inside bg','full'],yscale='log',ylabel='||R|| / sqrt(trace(H) L)')
        axes[1,i].set(title=state+': regional gradient alignment',xticks=range(3),xticklabels=['all','hidden','head'],ylim=(-1.05,1.05),ylabel='cos(g_damage, g_inside-bg)')
        axes[1,i].axhline(0,color='black',ls=':',lw=.8)
        for ax in axes[:,i]:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('E022/E023 six saved endpoints | original mass objective | no fitting or updates')
    for ext in ('png','pdf'):fig.savefig(out/f'head_and_regional_gradients.{ext}',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(11,10),layout='constrained')
    for i,state in enumerate(STATES):
        for arm,col in COLORS.items():
            r=next(x for x in rr if x['state']==state and x['arm']==arm)
            for reg,style in [('damage','-'),('background_inside','--')]:
                act=[x for x in r['activations'] if x['region']==reg]
                axes[i,0].plot(range(1,9),[x['active_fraction'] for x in act],style,color=col,label=arm+' '+reg)
                h=next(x for x in r['head'] if x['region']==reg and x['coordinate']=='physical');ev=np.maximum(np.array(h['eigenvalues']),0)
                axes[i,1].plot(range(1,len(ev)+1),np.maximum(ev/ev[0],1e-16),style,color=col,label=arm+' '+reg)
        axes[i,0].set(title=state+': actual positive activation',xlabel='Hidden layer',ylabel='Conditional mass-weighted fraction',yscale='log',xticks=range(1,9))
        axes[i,1].set(title=state+': effective head feature Gram',xlabel='Eigenvalue index',ylabel='Eigenvalue / maximum (floor 1e-16)',yscale='log',ylim=(1e-16,2))
        for ax in axes[i]:ax.grid(alpha=.2);ax.legend(fontsize=6)
    for ext in ('png','pdf'):fig.savefig(out/f'activation_and_feature_spectrum.{ext}',dpi=170)
    plt.close(fig)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
