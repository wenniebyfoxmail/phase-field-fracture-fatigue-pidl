function result=e011_raw_equivalence(points,c,u,raw,ur,rr,q)
%E011_RAW_EQUIVALENCE Read-only independent Q4/Amor consistency and response.
% No assembly callback, stiffness getter, solve, cache or state assignment.
if nargin==0
 result=selftest();return;
end
n=size(points,1);ne=size(c,1);tau=1e-10;
assert(size(points,2)==2 && size(c,2)==4 && isequal(size(raw),[ne,4]) && isequal(size(rr),[ne,4]));
assert(numel(u)==2*n && numel(ur)==2*n && all(isfinite([u(:);ur(:);raw(:);rr(:);points(:)])));
assert(all(c>=1 & c<=n & c==fix(c),'all'));
expected=quadrature_contract();
assert(isequal(size(q.gauss_pts),[4,2]) && max(abs(q.gauss_pts-expected.gauss_pts),[],'all')<=1e-15,'E011:RawGeometry','Wrong GP order');
assert(isequal(size(q.Nxi),[4,4]) && max(abs(q.Nxi-expected.Nxi),[],'all')<=1e-14,'E011:RawGeometry','Wrong Q4 basis');
assert(isequal(size(q.dNdxi),[2,4,4]) && max(abs(q.dNdxi-expected.dNdxi),[],'all')<=1e-14,'E011:RawGeometry','Wrong Q4 derivative');
assert(numel(q.gauss_W)==4 && all(q.gauss_W==1),'E011:RawGeometry','Wrong quadrature weights');
mu=1/2.6;bulk=1/1.2;D=2*mu*[2/3,-1/3,0;-1/3,2/3,0;0,0,.5];L=2*mu+2*bulk;
u=u(:);ur=ur(:);delta=u-ur;
x=reshape(points(c(:),1),ne,4);y=reshape(points(c(:),2),ne,4);
uc=reshape(u(c(:)),ne,4);vc=reshape(u(n+c(:)),ne,4);
uf=reshape(ur(c(:)),ne,4);vf=reshape(ur(n+c(:)),ne,4);
ud=reshape(delta(c(:)),ne,4);vd=reshape(delta(n+c(:)),ne,4);
pc=zeros(ne,4);pr=pc;bound=pc;strain_roundoff=0;branch_changes=0;
for g=1:4
 dref=expected.dNdxi(:,:,g);
 j11=x*dref(1,:)';j12=y*dref(1,:)';j21=x*dref(2,:)';j22=y*dref(2,:)';
 detj=j11.*j22-j12.*j21;assert(all(isfinite(detj) & detj>0),'E011:RawGeometry','Non-positive Jacobian');
 dx=(j22.*dref(1,:)-j12.*dref(2,:))./detj;
 dy=(-j21.*dref(1,:)+j11.*dref(2,:))./detj;
 ec=[sum(dx.*uc,2),sum(dy.*vc,2),sum(dy.*uc+dx.*vc,2)];
 er=[sum(dx.*uf,2),sum(dy.*vf,2),sum(dy.*uf+dx.*vf,2)];
 de=[sum(dx.*ud,2),sum(dy.*vd,2),sum(dy.*ud+dx.*vd,2)];
 tc=ec(:,1)+ec(:,2);tr=er(:,1)+er(:,2);
 pc(:,g)=energy(ec,D,bulk);pr(:,g)=energy(er,D,bulk);
 stress=er*D;stress(:,1:2)=stress(:,1:2)+bulk*max(tr,0);
 s=sqrt(sum(de.^2,2));bound(:,g)=sqrt(sum(stress.^2,2)).*s+.5*L*s.^2;
 strain_roundoff=max(strain_roundoff,max(abs((ec-er)-de),[],'all'));
 branch_changes=branch_changes+sum((tc>=0)~=(tr>=0));
end
sc=max(1,abs(pc));sr=max(1,abs(pr));ecerr=abs(raw-pc);ererr=abs(rr-pr);
allowance=bound+tau*sc+tau*sr;
result=struct('schema','raw_response_r4','tau',tau,'L',L, ...
 'candidate_own_scaled_maxerr',max(ecerr./sc,[],'all'), ...
 'reference_own_scaled_maxerr',max(ererr./sr,[],'all'), ...
 'legacy_raw_scaled_maxerr',max(abs(raw-rr)./max(1,abs(rr)),[],'all'), ...
 'response_ratio_max',max(abs(raw-rr)./allowance,[],'all'), ...
 'strain_subtraction_roundoff_max',strain_roundoff,'trace_branch_changes',branch_changes, ...
 'candidate_replayed',pc,'reference_replayed',pr,'analytic_response_bound',bound, ...
 'candidate_own_pass',all(ecerr<=tau*sc,'all'), ...
 'reference_own_pass',all(ererr<=tau*sr,'all'), ...
 'response_pass',all(abs(raw-rr)<=allowance,'all'));
result.pass=result.candidate_own_pass && result.reference_own_pass && result.response_pass;
assert(all(isfinite([pc(:);pr(:);bound(:);allowance(:)])));
end
function psi=energy(e,D,K)
psi=.5*sum((e*D).*e,2)+.5*K*max(e(:,1)+e(:,2),0).^2;
end
function q=quadrature_contract()
g=.577350269189626;q=struct('gauss_pts',g*[1,1;-1,1;1,-1;-1,-1],'gauss_W',ones(4,1),'Nxi',zeros(4,4),'dNdxi',zeros(2,4,4));
for k=1:4
 xi=q.gauss_pts(k,1);eta=q.gauss_pts(k,2);
 q.Nxi(:,k)=.25*[(1-xi)*(1-eta);(1+xi)*(1-eta);(1+xi)*(1+eta);(1-xi)*(1+eta)];
 q.dNdxi(:,:,k)=.25*[-(1-eta),1-eta,1+eta,-(1+eta);-(1-xi),-(1+xi),1+xi,1-xi];
end
end
function result=selftest()
p=[0,0;1.2,.1;1.05,1.1;-.1,.9];c=1:4;q=quadrature_contract();
u=[.1*p(:,1);.2*p(:,2)];r=e011_raw_equivalence(p,c,u,zeros(1,4),u,zeros(1,4),q);raw=r.candidate_replayed;
r=e011_raw_equivalence(p,c,u,raw,u,raw,q);assert(r.pass);names=cell(1,12);ncase=1;names{ncase}='affine';
t=u+[ones(4,1)*.01;ones(4,1)*-.02];r=e011_raw_equivalence(p,c,t,raw,u,raw,q);assert(r.pass);ncase=ncase+1;names{ncase}='rigid_translation';
for sign_value=[-1,1]
 v=sign_value*u;z=e011_raw_equivalence(p,c,v,zeros(1,4),-v,zeros(1,4),q);
 r=e011_raw_equivalence(p,c,v,z.candidate_replayed,-v,z.reference_replayed,q);assert(r.pass && r.trace_branch_changes==4);
 ncase=ncase+1;names{ncase}=sprintf('trace_cross_%d',sign_value);
end
v=[.4*p(:,2);zeros(4,1)];r=e011_raw_equivalence(p,c,v,ones(1,4)*(.5/2.6*.4^2),v,ones(1,4)*(.5/2.6*.4^2),q);assert(r.pass);ncase=ncase+1;names{ncase}='engineering_shear';
v=[.2;-.1;.35;.08;-.07;.21;.1;-.13];z=e011_raw_equivalence(p,c,v,zeros(1,4),v,zeros(1,4),q);rv=z.candidate_replayed;
r=e011_raw_equivalence(p,c,v,rv([2,1,4,3]),v,rv,q);assert(~r.pass);ncase=ncase+1;names{ncase}='wrong_gp_rejected';
r=e011_raw_equivalence(p,c,v,rv+1e-5,v,rv+1e-5,q);assert(~r.pass);ncase=ncase+1;names{ncase}='common_offset_rejected';
r=e011_raw_equivalence(p,c,v,raw,u,raw,q);assert(~r.pass);ncase=ncase+1;names{ncase}='stale_raw_rejected';
r=e011_raw_equivalence(p,c,v,1.01*rv,v,1.01*rv,q);assert(~r.pass);ncase=ncase+1;names{ncase}='wrong_material_rejected';
shear=[.4*p(:,2);zeros(4,1)];wrong=ones(1,4)*(.5/2.6*.2^2);r=e011_raw_equivalence(p,c,shear,wrong,shear,wrong,q);assert(~r.pass);ncase=ncase+1;names{ncase}='half_shear_rejected';
pp=p;pp(3,1)=pp(3,1)+.2;r=e011_raw_equivalence(pp,c,v,rv,v,rv,q);assert(~r.pass);ncase=ncase+1;names{ncase}='wrong_geometry_rejected';
r=e011_raw_equivalence(p,c,zeros(8,1),zeros(1,4),zeros(8,1),zeros(1,4),q);assert(r.pass);ncase=ncase+1;names{ncase}='zero_unload';
assert(ncase==12);
result=struct('status','passed','cases',ncase,'names',{names},'native_field_solves',0);
end
