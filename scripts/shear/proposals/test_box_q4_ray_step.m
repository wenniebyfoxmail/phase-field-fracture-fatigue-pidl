function test_box_q4_ray_step()
% Scalar uniform-Q4 ray, known exact minimizer across the original soft hinge.
g=struct('quads',[1,2,3,4],'N',ones(4,1)/4,'Bx',zeros(1,4,1),'By',zeros(1,4,1),'weights',1);
mat=struct('Gc',.8*8*.01/3,'ell',.01,'penalty_irrev',1e6,'penalty_recov',0);
a=.6*ones(4,1);s=-.4*ones(4,1);h=.4*ones(4,1);driver=.5;slope=(.6-.2)*(-.4);
[t,info]=box_q4_ray_step(a,s,h,driver,mat,g,slope);
optimum=(.2+mat.penalty_irrev*.4)/(1+mat.penalty_irrev);expected=(.6-optimum)/.4;
assert(abs(t-expected)<1e-12 && abs(info.slope_selected)<1e-8 && info.bisections==48);
Qfull=box_q4_ray_curvature(a,s,h,driver,mat,g);old_step=min(1,(1-1e-4)*(-slope)/Qfull);
assert(t>1e5*old_step,'Expected conservative full-ray bound in this fixture');
mat.penalty_irrev=0;[t,~]=box_q4_ray_step(a,s,h,driver,mat,g,slope);assert(abs(t-1)<1e-12);
[t,info]=box_q4_ray_step(a,s,h,0,mat,g,-.32);assert(t==1 && info.Qbase==0);
% Actual existing Q4 analytic gradient at both ends and selected point.
mat.penalty_irrev=1e6;
for cfg=1:3
    if cfg==1,a=.6*ones(4,1);s=-.4*ones(4,1);end
    if cfg==2,a=.2*ones(4,1);s=.4*ones(4,1);end
    if cfg==3,a=.4*ones(4,1);s=-.2*ones(4,1);end
    [~,~,grad0]=box_q4_pf_energy(a,h,.5,mat,g);S=grad0'*s;
    [t,info]=box_q4_ray_step(a,s,h,.5,mat,g,S);
    [~,~,grad1]=box_q4_pf_energy(a+s,h,.5,mat,g);
    [~,~,gradt]=box_q4_pf_energy(a+t*s,h,.5,mat,g);
    assert(abs(grad1'*s-info.slope1)<1e-8 && abs(gradt'*s-info.slope_selected)<1e-8);
    expected=((.2+1e6*.4)/(1+1e6)-a(1))/s(1);
    assert(abs(t-expected)<1e-12);
end
mat.Gc=0;a=.2*ones(4,1);s=.4*ones(4,1);
[~,~,grad]=box_q4_pf_energy(a,h,0,mat,g);[t,info]=box_q4_ray_step(a,s,h,0,mat,g,grad'*s);assert(t>=.5-1e-12 && t<=1 && abs(info.slope1)<1e-8 && abs(info.slope_selected)<1e-8);
fprintf('RAY_STEP_FIXTURES_PASS: history branch on/off/kink, analytic Q4 gradient, endpoint, linear and flat rays\n');
end
