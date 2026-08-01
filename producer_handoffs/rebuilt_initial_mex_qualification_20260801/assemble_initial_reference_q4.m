function [K_vect, i_row, j_col, M_vector, i_row_sig, j_col_sig, ...
    eps_vector, i_row_eps, j_col_eps, sig0_vector, i_row_pf, j_col_pf] = ...
    assemble_initial_reference_q4(MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, field_vars)
%ASSEMBLE_INITIAL_REFERENCE_Q4 Independent MATLAB translation of initial.f90.

localValidateInputs(MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, field_vars);

nel = MESH.nel;
numNodes = MESH.num_node;
numElements = MESH.num_elem;
numDofNode = DOFS.num_dof_node;
tensors = MESH.tensors;
elementDofs = nel * numDofNode;
numEntries = elementDofs^2;

K_vect = zeros(numElements * numEntries, 1);
i_row = zeros(size(K_vect));
j_col = zeros(size(K_vect));
M_vector = zeros(numElements * tensors * nel^2, 1);
i_row_sig = zeros(size(M_vector));
j_col_sig = zeros(size(M_vector));
operatorCount = numElements * tensors * nel^2 * numDofNode;
eps_vector = zeros(operatorCount, 1);
i_row_eps = zeros(operatorCount, 1);
j_col_eps = zeros(operatorCount, 1);
sig0_vector = zeros(operatorCount, 1);
i_row_pf = zeros(numElements * nel^2, 1);
j_col_pf = zeros(size(i_row_pf));

for element = 1:numElements
    elNodes = MESH.elem(element, 1:nel).';
    elCoord = MESH.node(elNodes, 1:2);
    elDamage = field_vars(elNodes);
    materialId = MESH.elem_material_id(element);
    materialCC = localMaterialCC(CC, materialId);
    residualStiffness = MAT_CHAR(materialId).res_stiff;

    elK = zeros(elementDofs);
    elM = zeros(nel);
    elEps = zeros(tensors * nel, elementDofs);
    elSig = zeros(tensors * nel, elementDofs);
    for gaussPoint = 1:QUADRATURE.num_gauss_pts
        naturalDerivatives = QUADRATURE.dNdxi(:, :, gaussPoint);
        jacobian = naturalDerivatives * elCoord;
        detJacobian = det(jacobian);
        if ~isfinite(detJacobian) || detJacobian <= 0
            error('rebuiltMexQ1:NonpositiveJacobian', ...
                'Element %d Gauss point %d has det(J) = %.17g.', ...
                element, gaussPoint, detJacobian);
        end
        globalDerivatives = jacobian \ naturalDerivatives;
        B = zeros(tensors, elementDofs);
        B(1, 1:nel) = globalDerivatives(1, :);
        B(2, nel + 1:2 * nel) = globalDerivatives(2, :);
        B(3, :) = [globalDerivatives(2, :), globalDerivatives(1, :)];

        shape = QUADRATURE.Nxi(:, gaussPoint);
        shapeBlock = zeros(tensors, tensors * nel);
        for component = 1:tensors
            columns = (component - 1) * nel + (1:nel);
            shapeBlock(component, columns) = shape.';
        end
        damageAtGaussPoint = shape.' * elDamage;
        degradedCC = ((1 - damageAtGaussPoint)^2 + residualStiffness) * materialCC;
        scale = t * QUADRATURE.gauss_W(gaussPoint) * detJacobian;
        elK = elK + scale * (B.' * degradedCC * B);
        elM = elM + scale * (shape * shape.');
        elEps = elEps + scale * (shapeBlock.' * B);
        elSig = elSig + scale * (shapeBlock.' * materialCC * B);
    end

    dofIdx = [elNodes; elNodes + numNodes];
    sigIdx = [elNodes; elNodes + numNodes; elNodes + 2 * numNodes];
    kRange = (element - 1) * numEntries + (1:numEntries);
    K_vect(kRange) = elK(:);
    for column = 1:elementDofs
        range = (element - 1) * numEntries + ...
            (column - 1) * elementDofs + (1:elementDofs);
        i_row(range) = dofIdx;
        j_col(range) = dofIdx(column);

        operatorRange = (element - 1) * tensors * nel * elementDofs + ...
            (column - 1) * tensors * nel + (1:tensors * nel);
        i_row_eps(operatorRange) = sigIdx;
        j_col_eps(operatorRange) = dofIdx(column);
    end

    mRange = (element - 1) * tensors * nel^2 + (1:tensors * nel^2);
    M_vector(mRange) = repmat(elM(:), tensors, 1);
    operatorRange = (element - 1) * tensors * nel * elementDofs + ...
        (1:tensors * nel * elementDofs);
    eps_vector(operatorRange) = elEps(:);
    sig0_vector(operatorRange) = elSig(:);

    for component = 1:tensors
        for column = 1:nel
            range = (element - 1) * tensors * nel^2 + ...
                (component - 1) * nel^2 + (column - 1) * nel + (1:nel);
            i_row_sig(range) = elNodes(column) + (component - 1) * numNodes;
            j_col_sig(range) = elNodes + (component - 1) * numNodes;
        end
    end
    for column = 1:nel
        range = (element - 1) * nel^2 + (column - 1) * nel + (1:nel);
        i_row_pf(range) = elNodes;
        j_col_pf(range) = elNodes(column);
    end
end
end

function localValidateInputs(MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, fieldVars)
requiredMesh = {'num_node', 'num_elem', 'nel', 'dim', 'tensors', ...
    'node', 'elem', 'elem_material_id'};
requiredDofs = {'num_dof_node', 'num_dof'};
requiredQuadrature = {'num_gauss_pts', 'gauss_W', 'dNdxi', 'Nxi'};
localRequireStructFields(MESH, requiredMesh);
localRequireStructFields(DOFS, requiredDofs);
localRequireStructFields(QUADRATURE, requiredQuadrature);
localRequire(localIntegerScalar(MESH.num_node) && localIntegerScalar(MESH.num_elem) && ...
    MESH.nel == 4 && MESH.dim == 2 && MESH.tensors == 3, ...
    'Only finite 2D Q4 meshes with three Voigt components are accepted.');
localRequire(localIntegerScalar(DOFS.num_dof_node) && DOFS.num_dof_node == 2 && ...
    DOFS.num_dof == 2 * MESH.num_node, 'DOF metadata is inconsistent.');
localRequire(isnumeric(MESH.node) && isreal(MESH.node) && ...
    size(MESH.node, 1) == MESH.num_node && size(MESH.node, 2) >= 2 && ...
    all(isfinite(MESH.node(:, 1:2)), 'all'), 'Node coordinates are invalid.');
localRequire(isnumeric(MESH.elem) && isreal(MESH.elem) && ...
    size(MESH.elem, 1) == MESH.num_elem && size(MESH.elem, 2) >= 4 && ...
    all(isfinite(MESH.elem(:, 1:4)), 'all') && ...
    all(MESH.elem(:, 1:4) == fix(MESH.elem(:, 1:4)), 'all') && ...
    all(MESH.elem(:, 1:4) >= 1 & MESH.elem(:, 1:4) <= MESH.num_node, 'all'), ...
    'Connectivity is invalid.');
localRequire(all(arrayfun(@(row) numel(unique(MESH.elem(row, 1:4))) == 4, ...
    (1:MESH.num_elem).')), 'Connectivity contains a repeated Q4 node.');
localRequire(isnumeric(MESH.elem_material_id) && ...
    numel(MESH.elem_material_id) == MESH.num_elem && ...
    all(isfinite(MESH.elem_material_id), 'all') && ...
    all(MESH.elem_material_id == fix(MESH.elem_material_id), 'all') && ...
    all(MESH.elem_material_id >= 1 & MESH.elem_material_id <= numel(MAT_CHAR), 'all'), ...
    'Material IDs are invalid.');
localRequire(isnumeric(t) && isreal(t) && isscalar(t) && isfinite(t) && t > 0, ...
    'Thickness must be a positive finite scalar.');
localRequire(isstruct(MAT_CHAR) && ~isempty(MAT_CHAR) && ...
    all(isfield(MAT_CHAR, 'res_stiff')), 'Material metadata is invalid.');
residuals = [MAT_CHAR.res_stiff];
localRequire(isreal(residuals) && all(isfinite(residuals)) && all(residuals >= 0), ...
    'Residual stiffness is invalid.');
localRequire(isnumeric(CC) && isreal(CC) && all(isfinite(CC), 'all') && ...
    size(CC, 1) == 3 && size(CC, 2) == 3 && ...
    (ndims(CC) == 2 || size(CC, 3) == numel(MAT_CHAR)), ...
    'Constitutive data are invalid.');
localRequire(isnumeric(fieldVars) && isreal(fieldVars) && iscolumn(fieldVars) && ...
    numel(fieldVars) == MESH.num_node && all(isfinite(fieldVars)), ...
    'Damage field is invalid.');
localRequire(localIntegerScalar(QUADRATURE.num_gauss_pts) && ...
    QUADRATURE.num_gauss_pts >= 1, 'Quadrature count is invalid.');
localRequire(isnumeric(QUADRATURE.gauss_W) && isreal(QUADRATURE.gauss_W) && ...
    numel(QUADRATURE.gauss_W) == QUADRATURE.num_gauss_pts && ...
    all(isfinite(QUADRATURE.gauss_W)) && all(QUADRATURE.gauss_W > 0), ...
    'Quadrature weights are invalid.');
localRequire(isnumeric(QUADRATURE.dNdxi) && isreal(QUADRATURE.dNdxi) && ...
    size(QUADRATURE.dNdxi, 1) == 2 && size(QUADRATURE.dNdxi, 2) == 4 && ...
    size(QUADRATURE.dNdxi, 3) == QUADRATURE.num_gauss_pts && ...
    all(isfinite(QUADRATURE.dNdxi), 'all') && ...
    all(abs(sum(QUADRATURE.dNdxi, 2)) <= 1e-14, 'all'), ...
    'Shape derivatives are invalid.');
localRequire(isnumeric(QUADRATURE.Nxi) && isreal(QUADRATURE.Nxi) && ...
    isequal(size(QUADRATURE.Nxi), [4 QUADRATURE.num_gauss_pts]) && ...
    all(isfinite(QUADRATURE.Nxi), 'all') && ...
    all(abs(sum(QUADRATURE.Nxi, 1) - 1) <= 1e-14), ...
    'Shape functions are invalid.');
end

function value = localMaterialCC(CC, materialId)
if ndims(CC) == 2
    value = CC;
else
    value = CC(:, :, materialId);
end
end

function localRequireStructFields(value, names)
localRequire(isstruct(value) && isscalar(value) && all(isfield(value, names)), ...
    'Required structure fields are missing.');
end

function value = localIntegerScalar(number)
value = isnumeric(number) && isreal(number) && isscalar(number) && ...
    isfinite(number) && number == fix(number) && number >= 1;
end

function localRequire(condition, message)
if ~condition
    error('rebuiltMexQ1:InvalidInput', '%s', message);
end
end
