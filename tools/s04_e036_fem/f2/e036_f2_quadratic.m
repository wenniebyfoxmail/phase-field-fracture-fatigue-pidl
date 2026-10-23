function [H,r,energy,meta,b]=e036_f2_quadratic(g,d,raw,f,lower)
%E036_F2_QUADRATIC Fixed raw/f AT1 energy on the exact E036 nodal box.
% Same coefficients as native at1_penalty_fatigue.f90:113-126. No df/dd term.
% GP penalty values/gradients vanish on this domain. Their kink Hessian is
% intentionally NOT copied from an unchecked native anchor matrix.
d=d(:);lower=lower(:);m=g.material;c=g.cells;e=size(c,1);
assert(numel(d)==g.n && numel(lower)==g.n && all(isfinite(d)) && ...
 all(isfinite(lower)) && all(lower>=0 & lower<=d & d<=1),'E036F2:Box','Exact nodal box required');
assert(isequal(size(raw),[e 4]) && isequal(size(f),[e 4]) && ...
 all(isfinite(raw) & raw>=0,'all') && all(isfinite(f) & f>=0 & f<=1,'all'));
de=d(c);oe=lower(c);A=zeros(e,16);linear=zeros(e,4);energy=0;
minimum_gp=inf;minimum_increment=inf;
for k=1:4
 N=g.N(:,k)';B1=g.bx(:,:,k);B2=g.by(:,:,k);weight=g.w(:,k);
 dg=sum(de.*N,2);og=sum(oe.*N,2);gx=sum(de.*B1,2);gy=sum(de.*B2,2);
 minimum_gp=min(minimum_gp,min(dg));minimum_increment=min(minimum_increment,min(dg-og));
 assert(all(dg>=0 & dg>=og),'E036F2:PenaltyBranch', ...
  'Frozen physical quadratic must stay on the zero-penalty feasible branch');
 mass=2*raw(:,k);grad=.75*f(:,k)*m.Gc*m.ell;
 q=weight.*(-2*raw(:,k)+.375*f(:,k)*m.Gc/m.ell);
 linear=linear+q.*N;
 at=0;
 for j=1:4
  for i=1:4
   at=at+1;
   A(:,at)=A(:,at)+weight.*(mass*N(i)*N(j)+grad.*(B1(:,i).*B1(:,j)+B2(:,i).*B2(:,j)));
  end
 end
 energy=energy+sum(weight.*(((1-dg).^2+m.res_stiff).*raw(:,k)+ ...
  .375*f(:,k)*m.Gc.*(dg/m.ell+m.ell*(gx.^2+gy.^2))));
end
H=sparse(g.i(:),g.j(:),A(:),g.n,g.n);
b=accumarray(c(:),linear(:),[g.n 1]);r=H*d+b;
assert(all(isfinite(nonzeros(H))) && all(isfinite(r)) && isfinite(energy));
meta=struct('minimum_gp_damage',minimum_gp,'minimum_gp_increment',minimum_increment, ...
 'gp_irreversibility_penalty_active',false,'gp_recovery_penalty_active',false, ...
 'penalty_irrev',m.penalty_irrev,'penalty_recov',m.penalty_recov, ...
 'coefficient_semantics','raw and GP f frozen inside this quadratic; no trial history commit');
end
