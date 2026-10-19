"""Proposed, unapproved complete storage envelope. All files under run root counted once.
No platform preflight or data access. Stat tolerates disappearance only.
"""
from pathlib import Path
import stat
MIB=2**20
LIMITS={'raw_arrays':490*MIB,'models':16*MIB,'metadata':32*MIB,'figures':24*MIB,
        'logs':16*MIB,'cache':64*MIB,'code':8*MIB,'temporary':16*MIB,'archive':700*MIB}
TOTAL=1536*MIB
ARRAYS={'inner_losses.f64','outer_bases.f64','current_anchors.f32','outer_targets.f32'}

def category(relative):
 p=Path(relative);parts=p.parts
 if p.name in ('results.tar','results.tar.partial'):return 'archive'
 if parts[0]=='code':return 'code'
 if parts[0]=='cache':return 'cache'
 if parts[0]=='logs' or p.name in ('font_dependency.log','launch.stdout','launch.stderr'):return 'logs'
 if parts[0]=='tmp' or p.name.endswith('.partial'):return 'temporary'
 if parts[0]=='outputs' and p.name in ARRAYS:return 'raw_arrays'
 if parts[0]=='outputs' and p.name.startswith('model_') and p.suffix=='.npz':return 'models'
 if p.suffix=='.png':return 'figures'
 return 'metadata'

def storage(root):
 root=Path(root);counts={k:0 for k in LIMITS}
 for p in root.rglob('*'):
  try:s=p.stat()
  except FileNotFoundError:continue
  if stat.S_ISREG(s.st_mode):counts[category(p.relative_to(root))]+=s.st_size
 return counts

def storage_reason(root,limits=None):
 counts=storage(root);limits=LIMITS if limits is None else limits
 for k,cap in limits.items():
  if counts[k]>cap:return 'storage_category_'+k
 if sum(counts.values())>TOTAL:return 'total_storage_budget'
 return None
