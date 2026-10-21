function [E,Eh,gradient]=box_q4_pf_energy(alpha,old,driver,mat,g)
% Exact alpha-dependent native AT1 energy at fixed driver/history.
% Inactive elasticity is constant in alpha and omitted from PF line search.
ae=reshape(alpha(g.quads),size(g.quads));he=reshape(old(g.quads),size(g.quads));a=ae*g.N;h=he*g.N;
pen=.5*mat.penalty_irrev*min(a-h,0).^2+.5*mat.penalty_recov*min(a,0).^2;
density=driver.*(1-a).^2+(3*mat.Gc/(8*mat.ell))*a+pen;
if nargout>2,local_gradient=zeros(size(ae));end
for k=1:size(g.N,2)
    gx=sum(g.Bx(:,:,k).*ae,2);gy=sum(g.By(:,:,k).*ae,2);
    density(:,k)=density(:,k)+(3*mat.Gc*mat.ell/8)*(gx.^2+gy.^2);
    if nargout>2
        f=2*driver(:,k).*(a(:,k)-1)+(3*mat.Gc/(8*mat.ell))+mat.penalty_irrev*min(a(:,k)-h(:,k),0)+mat.penalty_recov*min(a(:,k),0);
        local_gradient=local_gradient+g.weights(:,k).*(f*g.N(:,k)'+(3*mat.Gc*mat.ell/4)*(gx.*g.Bx(:,:,k)+gy.*g.By(:,:,k)));
    end
end
Eh=sum(g.weights.*pen,'all');E=sum(g.weights.*density,'all');
if nargout>2,gradient=accumarray(g.quads(:),local_gradient(:),[numel(alpha),1]);end
assert(isfinite(E) && isfinite(Eh),'BOX:Energy','Nonfinite native PF energy');
end
