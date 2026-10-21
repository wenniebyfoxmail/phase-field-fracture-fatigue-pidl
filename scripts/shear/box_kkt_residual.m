function [r, value] = box_kkt_residual(alpha, gradient, free)
% Normal-cone residual in ORIGINAL nondimensional energy-gradient units.
% No projection step, diagonal scale, normalized norm or bound tolerance.
r=gradient(:);a=alpha(:);
assert(all(isfinite(a)) && all(isfinite(r)),'BOX:Nonfinite','Nonfinite KKT input');
lo=(a==0);hi=(a==1);
r(lo)=min(r(lo),0);r(hi)=max(r(hi),0);
r=r(free);value=norm(r);
if any(a(free)<0 | a(free)>1),value=Inf;end
end
