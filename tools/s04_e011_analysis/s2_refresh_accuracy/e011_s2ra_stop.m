function [value,eligible]=e011_s2ra_stop(ur,cached,fresh,limits,refresh,outer)
% Same formula/eligibility for all cells; only the chosen residual changes.
if refresh,dr=fresh;else,dr=cached;end
value=max((ur+dr)/limits.joint_tol,ur/limits.outer_u_tol);
eligible=outer>=1 && value<=1;
end
