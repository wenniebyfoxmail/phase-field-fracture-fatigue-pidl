function [lambda,info]=box_q4_ray_step(alpha,direction,old,driver,mat,g,slope)
% Exact fixed-driver/history piecewise-quadratic ray derivative; no assembly.
% Select a feasible initial step only. Native energy Armijo and KKT still decide.
assert(isfinite(slope) && slope<0,'BOX:RaySlope','Expected feasible descent slope');
ae=reshape(alpha(g.quads),size(g.quads));se=reshape(direction(g.quads),size(g.quads));he=reshape(old(g.quads),size(g.quads));
a=ae*g.N;ds=se*g.N;h=he*g.N;
assert(all(isfinite(driver),'all') && all(driver>=0,'all'),'BOX:Driver','Invalid driving energy');
assert(all(isfinite([mat.penalty_irrev,mat.penalty_recov])) && all([mat.penalty_irrev,mat.penalty_recov]>=0),'BOX:Penalty','Invalid original penalty');
gap=a-h;old_ir=min(gap,0);old_rec=min(a,0);
density=2*driver.*ds.^2;
elastic_term=-2*driver.*(1-a).*ds;fracture_term=(3*mat.Gc/(8*mat.ell))*ds;
history_term=mat.penalty_irrev*old_ir.*ds;recovery_term=mat.penalty_recov*old_rec.*ds;
linear_density=elastic_term+fracture_term+history_term+recovery_term;
roundoff_density=abs(elastic_term)+abs(fracture_term)+abs(history_term)+abs(recovery_term);
for k=1:size(g.N,2)
    gx=sum(g.Bx(:,:,k).*se,2);gy=sum(g.By(:,:,k).*se,2);
    density(:,k)=density(:,k)+(3*mat.Gc*mat.ell/4)*(gx.^2+gy.^2);
    ax=sum(g.Bx(:,:,k).*ae,2);ay=sum(g.By(:,:,k).*ae,2);
    gradient_x=(3*mat.Gc*mat.ell/4)*(ax.*gx);gradient_y=(3*mat.Gc*mat.ell/4)*(ay.*gy);
    linear_density(:,k)=linear_density(:,k)+gradient_x+gradient_y;
    roundoff_density(:,k)=roundoff_density(:,k)+abs(gradient_x)+abs(gradient_y);
end
Qbase=sum(g.weights.*density,'all');assert(isfinite(Qbase) && Qbase>=0);
analytic_slope=sum(g.weights.*linear_density,'all');
roundoff_scale=max(abs(slope),sum(abs(g.weights).*roundoff_density,'all'));
assert(isfinite(analytic_slope) && isfinite(roundoff_scale),'BOX:RayFinite','Nonfinite ray slope arithmetic');
assert(abs(analytic_slope-slope)<=1e-10*max(roundoff_scale,realmin),'BOX:RayGradient','Ray derivative and native gradient disagree');
slope_end=ray_derivative(1);iterations=0;
if slope_end<=0
    lambda=1;lo=1;hi=1;
else
    lo=0;hi=1;
    for k=1:48
        mid=(lo+hi)/2;value=ray_derivative(mid);
        if value<=0,lo=mid;else,hi=mid;end
        iterations=k;
    end
    lambda=(lo+hi)/2;
end
assert(isfinite(lambda) && lambda>0 && lambda<=1,'BOX:RayStep','Invalid ray step');
info=struct('Qbase',Qbase,'slope0',slope,'slope1',slope_end,'slope_selected',ray_derivative(lambda),'bisections',iterations,'bracket_lo',lo,'bracket_hi',hi,'analytic_slope0',analytic_slope,'slope_mismatch',abs(analytic_slope-slope));
    function value=ray_derivative(t)
        change=mat.penalty_irrev*(min(gap+t*ds,0)-old_ir)+mat.penalty_recov*(min(a+t*ds,0)-old_rec);
        value=slope+t*Qbase+sum(g.weights.*ds.*change,'all');
        assert(isfinite(value),'BOX:RayFinite','Nonfinite ray derivative');
    end
end
