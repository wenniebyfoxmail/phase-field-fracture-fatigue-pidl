function policy=e036_policy(name,phase_semantics)
%E036_POLICY Explicit numerical controls, not physical qualification criteria.
assert(ismember(string(name),["fresh_original_tolerances","fresh_strict_e011"]), ...
 'E036:Policy','Choose a named tolerance policy');
assert(ismember(string(phase_semantics),["soft_penalty_equations","nodal_box_kkt"]), ...
 'E036:Semantics','Explicit phase equation/constraint semantics required');
policy=struct('name',string(name),'phase_semantics',string(phase_semantics), ...
 'bound_tol',1e-8,'active_tol',1e-10,'history_tol',1e-10);
policy.expected_material=struct('E',1,'ni',.3,'Gc',.01,'ell',.01, ...
 'res_stiff',0,'alpha_T',.5,'p',2,'penalty_irrev',421875,'penalty_recov',13781.25);
if string(name)=="fresh_original_tolerances"
 policy.joint_tol=4e-4;policy.u_tol=1e-6;
else
 policy.joint_tol=4e-6;policy.u_tol=1e-8;
end
end
