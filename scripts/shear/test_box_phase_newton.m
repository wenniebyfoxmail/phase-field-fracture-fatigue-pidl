function test_box_phase_newton()
% Tiny analytic convex constrained fixtures, not a PDE pilot.
opts=struct('max_iter',30,'res_tol',1e-12,'check',@()[]);
K=[3,1,.2;1,4,1;.2,1,3];expected=[0;.4;1];g=[1;0;-2];b=K*expected-g;
[a,c,r]=box_phase_newton(@assemble,@(A,f)A\f,[.5;.5;.5],(1:3)',opts);
assert(r.ok && norm(a-expected)<1e-12 && isequal(a([1,3]),[0;1]));
[kr,kn]=box_kkt_residual(a,c.R,(1:3)');assert(kn<1e-12 && norm(c.R)>1);
% Fixed crack excluded; active lifting must include its off-diagonal coupling.
b=K*[1;.25;0]-[9;0;1];
[a,~,r]=box_phase_newton(@assemble,@(A,f)A\f,[1;.7;.4],[2;3],opts);
assert(r.ok && a(1)==1 && abs(a(2)-.25)<1e-12 && a(3)==0);
% Wrong face signs remain residuals; tiny interior distance does NOT hide R.
[~,v]=box_kkt_residual([0;1;1e-15],[-2;3;4],(1:3)');assert(abs(v-sqrt(29))<1e-12);
[~,v]=box_kkt_residual([-eps;1],[0;0],(1:2)');assert(isinf(v));
% Piecewise soft-history energy, independently known solution .6 at node1.
K=eye(2);b=[.2;2];old=[.8;.3];gamma=2;
[a,~,r]=box_phase_newton(@history_assemble,@(A,f)A\f,[0;0],(1:2)',opts);
assert(r.ok && abs(a(1)-.6)<1e-12 && a(2)==1 && r.backtracks>0);
% Actual Q4 energy geometry: constant/affine field closed-form integrals.
quad.num_gauss_pts=4;quad.gauss_W=ones(4,1);z=[-1,-1;1,-1;1,1;-1,1]/sqrt(3);sx=[-1;1;1;-1];sy=[-1;-1;1;1];
quad.Nxi=zeros(4);quad.dNdxi=zeros(2,4,4);
for j=1:4
    quad.Nxi(:,j)=(1+sx*z(j,1)).*(1+sy*z(j,2))/4;
    quad.dNdxi(:,:,j)=[(sx.*(1+sy*z(j,2)))';(sy.*(1+sx*z(j,1)))']/4;
end
gm=box_q4_geometry([0,0;1,0;1,1;0,1],[1,2,3,4],quad,1);
mt=struct('Gc',.01,'ell',.01,'penalty_irrev',3,'penalty_recov',5);
[eng,eh,eg]=box_q4_pf_energy(.4*ones(4,1),.6*ones(4,1),2*ones(1,4),mt,gm);
assert(abs(sum(eg)+2.625)<1e-12);
assert(abs(eng-.93)<1e-12 && abs(eh-.06)<1e-12 && abs(sum(gm.weights,'all')-1)<1e-12);
ep=box_q4_pf_energy((.4+1e-6)*ones(4,1),.6*ones(4,1),2*ones(1,4),mt,gm);
em=box_q4_pf_energy((.4-1e-6)*ones(4,1),.6*ones(4,1),2*ones(1,4),mt,gm);
assert(abs((ep-em)/2e-6+2.625)<1e-8);
af=[.2;.3;.6;.5];
for j=1:4
    assert(abs(sum(gm.Bx(:,:,j).*af',2)-.1)<1e-12);
    assert(abs(sum(gm.By(:,:,j).*af',2)-.3)<1e-12);
end
fprintf('BOX_FIXTURES_PASS: active lifting, crack exclusion, KKT signs, no tiny-step artifact, soft history\n');
    function c=assemble(x)
        c=struct('u',x,'K',K,'R',K*x-b,'energy',.5*x'*K*x-b'*x);
    end
    function c=history_assemble(x)
        h=x-old;H=diag(double(h<0));
        c=struct('u',x,'K',K+gamma*H,'R',K*x-b+gamma*min(h,0),'energy',.5*x'*K*x-b'*x+.5*gamma*sum(min(h,0).^2));
    end
end
