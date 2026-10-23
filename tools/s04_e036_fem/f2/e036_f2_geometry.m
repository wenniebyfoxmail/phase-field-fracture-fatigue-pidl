function g=e036_f2_geometry(sys)
%E036_F2_GEOMETRY Explicit native-order Q4 geometry for isolated F2 checks.
% Preparation only: not MATLAB-validated or used by the running B/strict code.
c=sys.MESH.elem(:,1:4);p=sys.MESH.node(:,1:2);N=sys.QUADRATURE.Nxi;
assert(size(c,2)==4 && isequal(size(N),[4 4]) && ...
 isequal(size(sys.QUADRATURE.dNdxi),[2 4 4]),'E036F2:Geometry','Native Q4 required');
assert(all(N>0,'all') && max(abs(sum(N,1)-1))<1e-14 && all(sys.QUADRATURE.gauss_W>0));
assert(numel(sys.MAT_CHAR)==1 && sys.GEOM.t>0);
e=size(c,1);x=reshape(p(c(:),1),e,4);y=reshape(p(c(:),2),e,4);
bx=zeros(e,4,4);by=bx;w=zeros(e,4);
for k=1:4
 D=sys.QUADRATURE.dNdxi(:,:,k);
 j11=sum(x.*D(1,:),2);j12=sum(y.*D(1,:),2);
 j21=sum(x.*D(2,:),2);j22=sum(y.*D(2,:),2);detj=j11.*j22-j12.*j21;
 assert(all(isfinite(detj) & detj>0),'E036F2:Geometry','Positive finite Jacobians required');
 bx(:,:,k)=(j22.*D(1,:)-j12.*D(2,:))./detj;
 by(:,:,k)=(-j21.*D(1,:)+j11.*D(2,:))./detj;
 w(:,k)=sys.GEOM.t*sys.QUADRATURE.gauss_W(k)*detj;
end
% Match each element's 4x4 column-major local matrix layout explicitly.
ii=zeros(e,16);jj=ii;at=0;
for j=1:4
 for i=1:4,at=at+1;ii(:,at)=c(:,i);jj(:,at)=c(:,j);end
end
g=struct('cells',c,'n',size(p,1),'N',N,'bx',bx,'by',by,'w',w, ...
 'i',ii,'j',jj,'material',sys.MAT_CHAR,'gp_order','(+,+),(-,+),(+,-),(-,-)');
end
