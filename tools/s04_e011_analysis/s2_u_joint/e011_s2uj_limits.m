function limits=e011_s2uj_limits(U,J)
assert(isscalar(U) && isscalar(J) && ismember(U,[0 1]) && ismember(J,[0 1]));
if U,utol=1e-8;else,utol=1e-6;end
if J,jtol=4e-6;outeru=1e-8;else,jtol=4e-4;outeru=4e-4;end
limits=struct('max_u',248,'max_d',248,'max_outer',20,'u_tol',utol,'d_tol',4e-6,'joint_tol',jtol,'outer_u_tol',outeru);
end
