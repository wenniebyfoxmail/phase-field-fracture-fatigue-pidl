function [strain_gp, trace_strain_gp] = strain_at_gauss_points( ...
    node_coords, connectivity, dNdxi, u_node)
%STRAIN_AT_GAUSS_POINTS Engineering strain for Q4 or T3 native GP order.

arguments
    node_coords (:,2) double
    connectivity (:,:) double {mustBeInteger,mustBePositive}
    dNdxi (:,:,:) double
    u_node (:,2) double
end
num_elem = size(connectivity,1);
num_gp = size(dNdxi,3);
num_local = size(connectivity,2);
if size(dNdxi,1) ~= 2 || size(dNdxi,2) ~= num_local || ...
        ~ismember(num_local,[3 4])
    error('phase_field:audit:InvalidNativeGradientShape', ...
        'Expected Q4 or T3 derivative shape [2,arity,num_gp].');
end
strain_gp = zeros(num_elem,num_gp,3);
for elem_index = 1:num_elem
    nodes = connectivity(elem_index,:);
    coords = node_coords(nodes,:);
    u_elem = u_node(nodes,1);
    v_elem = u_node(nodes,2);
    for gp_index = 1:num_gp
        local_grad = dNdxi(:,:,gp_index);
        physical_grad = (local_grad * coords) \ local_grad;
        strain_gp(elem_index,gp_index,:) = [ ...
            physical_grad(1,:) * u_elem, ...
            physical_grad(2,:) * v_elem, ...
            physical_grad(2,:) * u_elem + physical_grad(1,:) * v_elem];
    end
end
trace_strain_gp = strain_gp(:,:,1) + strain_gp(:,:,2);
end
