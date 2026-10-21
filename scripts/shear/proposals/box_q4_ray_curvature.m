function Q=box_q4_ray_curvature(alpha,direction,old,driver,mat,g)
% PROPOSAL ONLY. Upper Hessian quadratic form over the feasible segment.
% Same energy/penalties: maximum reachable branch curvature, no factor/solve.
ae=reshape(alpha(g.quads),size(g.quads));se=reshape(direction(g.quads),size(g.quads));he=reshape(old(g.quads),size(g.quads));
a=ae*g.N;ds=se*g.N;h=he*g.N;
healing=(min(a-h,a+ds-h)<0);negative=(min(a,a+ds)<0);
assert(all(isfinite(driver),'all') && all(driver>=0,'all'),'BOX:Driver','Invalid nonnegative fixed driving energy');
density=(2*driver+mat.penalty_irrev*healing+mat.penalty_recov*negative).*ds.^2;
for k=1:size(g.N,2)
    gx=sum(g.Bx(:,:,k).*se,2);gy=sum(g.By(:,:,k).*se,2);
    density(:,k)=density(:,k)+(3*mat.Gc*mat.ell/4)*(gx.^2+gy.^2);
end
Q=sum(g.weights.*density,'all');
assert(isfinite(Q) && Q>=0,'BOX:Curvature','Invalid exact-energy curvature bound');
end
