function C=e011_s2i_stop(ur,feasible,raw,limits,damage_mode,loose)
%E011_S2I_STOP Declared fresh strict vs old-tolerance returned-field rules.
if loose
 if damage_mode==0,C=(ur+raw)/limits.joint_tol;else,C=(ur+feasible)/limits.joint_tol;end
else
 C=max((ur+feasible)/limits.joint_tol,ur/limits.u_tol);
end
end
