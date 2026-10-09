"""Pure NumPy reference tiling/reconstruction; no model or training entry point."""
import numpy as np
TILE=448
STRIDE=224

def starts(length):
 if not isinstance(length,int) or length<=0:raise ValueError('Positive integer dimension required')
 if length<=TILE:return [0]
 out=list(range(0,length-TILE+1,STRIDE))
 if out[-1]!=length-TILE:out.append(length-TILE)
 return out

def tiles(rgb):
 if rgb.ndim!=3 or rgb.shape[2]!=3 or min(rgb.shape[:2])<=0:raise ValueError('Expected nonempty HWC RGB')
 h,w=rgb.shape[:2]
 for y in starts(h):
  for x in starts(w):
   patch=rgb[y:y+TILE,x:x+TILE];vh,vw=patch.shape[:2]
   patch=np.pad(patch,((0,TILE-vh),(0,TILE-vw),(0,0)),mode='edge')
   yield (y,x,vh,vw),patch

def reconstruct(rgb,predict_probability):
 h,w=rgb.shape[:2];total=np.zeros((h,w),dtype=np.float64);count=np.zeros((h,w),dtype=np.uint32)
 for (y,x,vh,vw),patch in tiles(rgb):
  p=np.asarray(predict_probability(patch),dtype=np.float64)
  if p.shape!=(TILE,TILE) or not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('Invalid tile probabilities')
  total[y:y+vh,x:x+vw]+=p[:vh,:vw];count[y:y+vh,x:x+vw]+=1
 if not (count>0).all():raise ValueError('Uncovered image pixels')
 return total/count
