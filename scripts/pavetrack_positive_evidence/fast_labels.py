"""Exact singleton insertion using per-image replay and atomic score-group search.

Matching is independent across images. Only the insertion image changes roles;
other images keep their original match identities. No approximate FP shortcut.
"""
from bisect import bisect_right,bisect_left
from collections import defaultdict
import math

def key(r):return (-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']))
def replay(rows,targets,iou):
    available=set(range(len(targets)));out=[]
    for r in sorted(rows,key=key):
        value,j=max(((iou(r['box_xyxy'],targets[i]),i) for i in available),default=(0.,-1))
        hit=j if value>=.5 else None
        if hit is not None:available.remove(hit)
        out.append((r,hit))
    return out

def curve(out):
    scores=[];fps=[0];hits=[];hit_scores=[]
    for row,hit in out:
        scores.append(-row['score']);fps.append(fps[-1]+int(hit is None))
        if hit is not None:hits.append((row['image_id'],hit));hit_scores.append(-row['score'])
    return scores,fps,hits,hit_scores

def prefix_fp(curve_,score):return curve_[1][bisect_right(curve_[0],-score)]
def prefix_hits(curve_,score):
    if score is None:return set()
    return set(curve_[2][:bisect_right(curve_[3],-score)])

class Context:
    def __init__(self,data,locations,metric,iou,check=lambda:None):
        self.iou=iou;self.targets={im:t for im,t in data['targets'].items() if data['locations'][im] in locations};self.images=defaultdict(list)
        self.rows=[r for r in data['originals'] if r['image_id'] in self.targets]
        for r in self.rows:self.images[r['image_id']].append(r)
        self.metric=metric(self.rows,self.targets,{im:data['locations'][im] for im in self.targets},'score')
        self.budget=len(self.targets);self.curves={};all_out=[]
        for im in self.targets:
            check();out=replay(self.images[im],self.targets[im],iou);self.curves[im]=curve(out);all_out.extend(out)
        all_out.sort(key=lambda pair:key(pair[0]));self.global_curve=curve(all_out)
        self.groups=sorted({-r['score'] for r in self.rows});self.cutoff=self.metric['global_score_threshold']
        self.hits=prefix_hits(self.global_curve,self.cutoff);self.hit_count=len(self.hits)
        if self.hit_count!=sum(t['true_positives'] for t in self.metric['locations']):raise ValueError('baseline match replay')
        excluded=[r['score'] for r in self.rows if self.cutoff is None or r['score']<self.cutoff]
        self.first_excluded=max(excluded,default=None)
    def label(self,row):
        score=row['score'];im=row['image_id']
        if self.first_excluded is not None and score<self.first_excluded:
            return dict(new=0,lost=0,FP=0,U=0,new_identities=[],lost_identities=[],admitted=False,cutoff=self.cutoff)
        old=self.curves[im];new_out=replay(self.images[im]+[row],self.targets[im],self.iou);new=curve(new_out)
        ins=bisect_left(self.groups,-score);unique=ins==len(self.groups) or self.groups[ins]!=-score;size=len(self.groups)+int(unique)
        def threshold(j):return score if unique and j==ins else -self.groups[j-int(unique and j>ins)]
        lo,hi=0,size
        while lo<hi:
            mid=(lo+hi)//2;t=threshold(mid)
            fp=prefix_fp(self.global_curve,t)+prefix_fp(new,t)-prefix_fp(old,t)
            if fp<=self.budget:lo=mid+1
            else:hi=mid
        cutoff=None if lo==0 else threshold(lo-1)
        # Changes in unchanged images are just a slice of the old TP sequence.
        new_count=0 if cutoff is None else bisect_right(self.global_curve[3],-cutoff)
        gained=set(self.global_curve[2][self.hit_count:new_count]) if new_count>=self.hit_count else set()
        lost=set(self.global_curve[2][new_count:self.hit_count]) if new_count<self.hit_count else set()
        gained={h for h in gained if h[0]!=im};lost={h for h in lost if h[0]!=im}
        before=prefix_hits(old,self.cutoff);after=prefix_hits(new,cutoff);gained|=after-before;lost|=before-after
        admitted=cutoff is not None and score>=cutoff
        role=next(h for r,h in new_out if r is row)
        fp=int(admitted and role is None)
        return dict(new=len(gained),lost=len(lost),FP=fp,U=len(gained)-len(lost)-fp,new_identities=[list(h) for h in sorted(gained)],lost_identities=[list(h) for h in sorted(lost)],admitted=admitted,cutoff=cutoff)
