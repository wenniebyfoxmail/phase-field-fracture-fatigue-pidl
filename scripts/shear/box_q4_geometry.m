function g=box_q4_geometry(nodes,quads,quad,t)
% Reuse EXACT native quadrature/order, no independent point convention.
n=size(quads,1);X=reshape(nodes(quads,1),size(quads));Y=reshape(nodes(quads,2),size(quads));
g.N=quad.Nxi;g.weights=zeros(n,quad.num_gauss_pts);
g.Bx=zeros(n,4,quad.num_gauss_pts);g.By=g.Bx;
for k=1:quad.num_gauss_pts
    D=quad.dNdxi(:,:,k);j11=X*D(1,:)';j12=Y*D(1,:)';j21=X*D(2,:)';j22=Y*D(2,:)';detJ=j11.*j22-j12.*j21;
    assert(all(isfinite(detJ) & detJ>0),'BOX:Jacobian','Invalid Q4 geometry');
    g.weights(:,k)=quad.gauss_W(k)*t*detJ;
    g.Bx(:,:,k)=(j22.*D(1,:)-j12.*D(2,:))./detJ;
    g.By(:,:,k)=(-j21.*D(1,:)+j11.*D(2,:))./detJ;
end
g.quads=quads;
end
