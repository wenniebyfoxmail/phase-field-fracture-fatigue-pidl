from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
r=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent
a=json.loads((r/'analysis.json').read_text())
order=['span_only','span_progress','current_response','history_response','global_history','centered_history','rich_history','compact_noclock','rich_noclock','persistence','secant']
labels={'span_only':'Span history','span_progress':'Span + progress','current_response':'+ current response','history_response':'+ response history','global_history':'+ global means history','centered_history':'+ centered stats history','rich_history':'+ rich field history','compact_noclock':'Compact, no progress','rich_noclock':'Rich, no progress','persistence':'Persistence','secant':'Secant'}
c={'span_only':'#999999','span_progress':'#555555','current_response':'#0072B2','history_response':'#009E73','global_history':'#E69F00','centered_history':'#CC79A7','rich_history':'#56B4E9','compact_noclock':'#88BDB0','rich_noclock':'#9ACFE8','persistence':'#111111','secant':'#D55E00'}
fig,ax=plt.subplots(2,2,figsize=(15,11),constrained_layout=True)
vals=[a['primary'][k] for k in order];ax[0,0].barh([labels[k] for k in order],vals,color=[c[k] for k in order],height=.68);ax[0,0].invert_yaxis();ax[0,0].set_xlim(0,max(vals)*1.16)
for i,v in enumerate(vals):ax[0,0].text(v+.012,i,f'{v:.4f}',va='center',fontsize=9)
ax[0,0].set_xlabel('Balanced normalized MAE (lower is better)');ax[0,0].set_title('(a) Primary score: equal release-group / horizon weights',loc='left')
for key,col,label,marker in [('current_response minus span_progress',c['current_response'],'Current response minus span+progress','o'),('history_response minus span_progress',c['history_response'],'Response history minus span+progress','s'),('history_response minus current_response','#CC79A7','History minus current response','^')]:
 ds=a['contrasts'][key]['paired_group_delta'];ax[0,1].scatter(np.arange(1,20),[ds[g] for g in a['groups']],label=label,c=col,marker=marker,s=27,alpha=.85)
ax[0,1].axhline(0,c='#777777',lw=.8);ax[0,1].set_xticks(range(1,20,2));ax[0,1].set_xlabel('Released group (alphabetical index)');ax[0,1].set_ylabel('Paired score difference (negative favors added info)');ax[0,1].legend(fontsize=8);ax[0,1].set_title('(b) Planned information contrasts, by released group',loc='left')
keys=['span_progress','current_response','history_response','global_history','centered_history','rich_history','persistence','secant']
for k in keys:ax[1,0].plot([10,40],[a['by_horizon'][str(h)][k] for h in (10,40)],marker='o',lw=1.5,c=c[k],label=labels[k])
ax[1,0].set_xticks([10,40]);ax[1,0].set_xlabel('Horizon in release stages (not verified machine cycles)');ax[1,0].set_ylabel('Balanced normalized MAE');ax[1,0].legend(fontsize=8,ncol=2);ax[1,0].set_title('(c) Information value across forecast horizons',loc='left')
for k in keys:ax[1,1].plot(range(3),[a['by_release_origin_third_not_physical_lifetime'][k][str(t)] for t in range(3)],marker='o',lw=1.5,c=c[k])
ax[1,1].set_xticks(range(3),['Early','Middle','Late']);ax[1,1].set_xlabel('Thirds of retained release origins (not physical lifetime)');ax[1,1].set_ylabel('Balanced normalized MAE');ax[1,1].set_title('(d) Descriptive release-position variation',loc='left')
for q in ax.flat:q.spines[['top','right']].set_visible(False);q.grid(axis='y',alpha=.15);q.set_axisbelow(True)
fig.suptitle('Response-state information value | 19 exposed groups | common native current-field output anchor',fontsize=13)
fig.savefig(r/'IU_R002_response_state_value.png',dpi=180);fig.savefig(r/'IU_R002_response_state_value.pdf');plt.close(fig)
print('FIGURE_COMPLETE')
