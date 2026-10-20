"""Three future fixed figures. Never used for the sealed diagnostic.
Font-manager's ONE known cache-build log is routed to an owned dependency log
before import. Any other warning/error record raises; Python warnings remain fatal.
"""
from pathlib import Path
import json,logging

class FontCacheLog(logging.Handler):
 def __init__(self,path):super().__init__(logging.WARNING);self.path=Path(path)
 def emit(self,record):
  text=record.getMessage()
  if record.levelno==logging.WARNING and text=='Matplotlib is building the font cache; this may take a moment.':
   with self.path.open('a') as f:f.write(text+'\n');f.flush()
  else:raise RuntimeError('unexpected font dependency log: '+text)

def render(root):
 root=Path(root);logger=logging.getLogger('matplotlib.font_manager');handler=FontCacheLog(root/'font_dependency.log')
 old_handlers=logger.handlers[:];old_propagate=logger.propagate;logger.handlers=[handler];logger.propagate=False
 try:
  import matplotlib
  matplotlib.use('Agg',force=True)
  import matplotlib.pyplot as plt
  from matplotlib.font_manager import FontProperties
  font=Path(matplotlib.get_data_path())/'fonts/ttf/DejaVuSans.ttf'
  if not font.is_file():raise RuntimeError('bundled DejaVu font missing')
  import hashlib
  from evidence import write,read_fields
  from engine import ARMS
  import numpy as np
  write(root/'plot_dependency.json',{'matplotlib':matplotlib.__version__,'backend':matplotlib.get_backend(),'font_file_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'font_policy':'only exact font-manager cache-build logging routed to font_dependency.log; other dependency warning/error fatal; no Python warning suppression'},True)
  plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8})
  info=json.loads((root/'group_horizon_results.json').read_text());pairs=info['paired'];groups=sorted({r['group'] for r in pairs});hs=sorted({r['H'] for r in pairs})
  values=np.asarray([[next(r['primary_C_minus_A'] for r in pairs if (r['group'],r['H'])==(g,h)) for h in hs] for g in groups])
  fig,ax=plt.subplots(figsize=(12,7));lim=float(abs(values).max()) or 1.
  im=ax.imshow(values,interpolation='nearest',cmap='RdBu',vmin=-lim,vmax=lim,aspect='auto');ax.set_xticks(range(len(hs)),hs);ax.set_yticks(range(len(groups)),groups);ax.set_title('All evaluated groups: L(simple C27)-L(separate A25); positive favors A');fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(root/'01_primary_groups.png',dpi=100);plt.close(fig)
  fig,ax=plt.subplots(figsize=(12,7))
  for arm in ARMS:
   ax.plot(range(len(pairs)),[r[arm] for r in pairs],marker='.',label=arm)
  ax.set_xticks(range(len(pairs)),[r['group']+'/H'+str(r['H']) for r in pairs],rotation=90,fontsize=6)
  for j,row in enumerate(pairs):
   if row['group'] in ('C_30Deg_20%_#1','C_30Deg_20%_#2','C_30Deg_20%_#3'):ax.axvspan(j-.4,j+.4,color='#D55E00',alpha=.12)
  ax.set(xlabel='All group/H cells; orange bands mark C30 published labels',ylabel='Native balanced normalized MAE',title=f'Seven arms; every evaluated group/H retained ({len(groups)} groups)');ax.legend(ncol=2);fig.tight_layout();fig.savefig(root/'02_seven_arm_losses.png',dpi=100);plt.close(fig)
  selected=min(pairs,key=lambda r:(r['primary_C_minus_A'],r['group'],r['H']));case=selected['worst_selected_A_case'];H=selected['H']
  fields,target,anchor,entry=read_fields(root,case,H);fig,axes=plt.subplots(4,8,figsize=(16,9));ranges={}
  for ch in (0,1):
   arrays=[target[ch]]+[p[ch] for p in fields];lo=min(float(x.min()) for x in arrays);hi=max(float(x.max()) for x in arrays)
   emax=max(float(abs(p[ch]-target[ch]).max()) for p in fields) or 1.;ranges[ch]={'native_field':[lo,hi],'signed_error':[-emax,emax]}
   for col,(label,a) in enumerate(zip(('Reference',)+ARMS,arrays)):
    axes[2*ch,col].imshow(a,interpolation='nearest',cmap='viridis',vmin=lo,vmax=hi);axes[2*ch,col].set_title(label);axes[2*ch,col].set_xticks([]);axes[2*ch,col].set_yticks([])
    axes[2*ch+1,col].imshow(np.zeros_like(a) if col==0 else a-target[ch],interpolation='nearest',cmap='RdBu',vmin=-emax,vmax=emax);axes[2*ch+1,col].set_xticks([]);axes[2*ch+1,col].set_yticks([])
   axes[2*ch,0].set_ylabel(f'ch{ch}: field [{lo:.3g},{hi:.3g}]');axes[2*ch+1,0].set_ylabel(f'error +/-{emax:.3g}')
  fig.suptitle(f'Declared failure view: worst primary group/H, then worst A loss case; {selected["group"]}, H{H}, case{case}');fig.tight_layout();fig.savefig(root/'03_failure_all_fields.png',dpi=100);plt.close(fig)
  for stem,question,reading in [('01_primary_groups','Does separate calibration beat the strong simple selector?','Rows: every released group; columns: both H. Common symmetric zero scale; positive C27-A25 favors separate calibration.'),('02_seven_arm_losses','How do all arms behave in every group/H cell?','Seven named lines; all group/H cells in stored paired order. C30 groups and negative results remain in the table; no case exclusion.'),('03_failure_all_fields','Where does the separate selector fail in the predefined worst view?','Columns: reference plus seven arms; rows: native field/signed error for each of two channels. Field limits shared within each channel; error limits symmetric within channel. Selection is worst primary group/H then highest A-loss origin; tie is lexical group/H then lowest case index.')]:
   text=f'# {question}\n\nSource: this new comparison outputs, group_horizon_results.json and self-contained float32 anchors/targets +float64 base fields +weights. Array schema and input provenance are frozen alongside these files.\n\n{reading}\n\nNumerical context: scope={'full19 completed comparison' if len(groups)==19 else 'component only; not the full19 result'}; primary equal-group/H C27-A25 mean={info["primary_mean"]:.9g}; all{len(groups)} groups and{len(hs)}H retained. Selected example case={case}, H={H}; native/error plotting ranges by channel={ranges}.\n\nLimits: exposed groups/unknown physical independence; fixed-alpha output-calibration experiment, not R003 exact replay; release-step/current anchor; original R003 warning breach retained. No input-identifiability, physical-memory, causal-error-share or road claim. G/S are separate increment descriptors, not additive native errors. Fixed-corner comparisons bound any two-weight claim.\n'
   (root/(stem+'.md')).write_text(text)
  for p in root.glob('0[123]_*.png'):
   if p.stat().st_size>8*2**20:raise RuntimeError('per-figure8MiB evidence budget')
 finally:
  logger.handlers=old_handlers;logger.propagate=old_propagate;handler.close()
