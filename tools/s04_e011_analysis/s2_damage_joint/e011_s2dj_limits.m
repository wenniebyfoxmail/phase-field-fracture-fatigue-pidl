function limits=e011_s2dj_limits(P,J)
assert(isscalar(P) && isscalar(J) && ismember(P,[0 1]) && ismember(J,[0 1]));
if P,dtol=4e-6;else,dtol=4e-4;end
if J,utol=1e-8;jtol=4e-6;outeru=1e-8;else,utol=1e-6;jtol=4e-4;outeru=4e-4;end
limits=struct('max_u',248,'max_d',248,'max_outer',20,'u_tol',utol,'d_tol',dtol,'joint_tol',jtol,'outer_u_tol',outeru);
end
