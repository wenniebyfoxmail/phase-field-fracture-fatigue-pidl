classdef rebuiltMexQ1ReferenceTest < matlab.unittest.TestCase
    methods (Test)
        function testOneElementMatchesLockedFortranOrdering(testCase)
            input = oneElementInput();
            outputs = callReference(input);

            nodes = (1:4).';
            dofs = [nodes; nodes + 4];
            sig = [nodes; nodes + 4; nodes + 8];
            expectedB = [ ...
                -0.5  0.5  0.5 -0.5  0    0    0    0; ...
                 0    0    0    0   -0.5 -0.5  0.5  0.5; ...
                -0.5 -0.5  0.5  0.5 -0.5  0.5  0.5 -0.5];
            integrationScale = 2.0;
            degradedCC = 0.59 * diag([2 3 4]);
            expectedK = integrationScale * expectedB.' * degradedCC * expectedB;
            expectedMBlock = 0.125 * ones(4);
            nBlock = blkdiag(0.25 * ones(1, 4), ...
                0.25 * ones(1, 4), 0.25 * ones(1, 4));
            expectedEps = integrationScale * nBlock.' * expectedB;
            expectedSig = integrationScale * nBlock.' * diag([2 3 4]) * expectedB;

            verifyEqual(testCase, outputs.K_vect, expectedK(:), 'AbsTol', 1e-14);
            verifyEqual(testCase, outputs.i_row, repmat(dofs, 8, 1));
            verifyEqual(testCase, outputs.j_col, repelem(dofs, 8));
            expectedMVector = repmat(expectedMBlock(:), 3, 1);
            verifyEqual(testCase, outputs.M_vector, expectedMVector, 'AbsTol', 1e-14);
            verifyEqual(testCase, outputs.eps_vector, expectedEps(:), 'AbsTol', 1e-14);
            verifyEqual(testCase, outputs.sig0_vector, expectedSig(:), 'AbsTol', 1e-14);
            verifyEqual(testCase, outputs.i_row_eps, repmat(sig, 8, 1));
            verifyEqual(testCase, outputs.j_col_eps, repelem(dofs, 12));

            expectedMRows = zeros(48, 1);
            expectedMCols = zeros(48, 1);
            offset = 0;
            for component = 0:2
                for column = 1:4
                    range = offset + (column - 1) * 4 + (1:4);
                    expectedMRows(range) = nodes(column) + component * 4;
                    expectedMCols(range) = nodes + component * 4;
                end
                offset = offset + 16;
            end
            verifyEqual(testCase, outputs.i_row_sig, expectedMRows);
            verifyEqual(testCase, outputs.j_col_sig, expectedMCols);
            verifyEqual(testCase, outputs.i_row_pf, repmat(nodes, 4, 1));
            verifyEqual(testCase, outputs.j_col_pf, repelem(nodes, 4));
            verifyEqual(testCase, fieldnames(outputs), outputNames());
            verifyTrue(testCase, all(structfun(@iscolumn, outputs)));
        end

        function testTwoElementTripletsPreserveElementConcatenation(testCase)
            input = twoElementInput();
            outputs = callReference(input);

            firstDofs = [1; 2; 5; 4; 7; 8; 11; 10];
            secondDofs = [2; 3; 6; 5; 8; 9; 12; 11];
            verifyEqual(testCase, outputs.i_row(1:64), repmat(firstDofs, 8, 1));
            verifyEqual(testCase, outputs.j_col(1:64), repelem(firstDofs, 8));
            verifyEqual(testCase, outputs.i_row(65:128), repmat(secondDofs, 8, 1));
            verifyEqual(testCase, outputs.j_col(65:128), repelem(secondDofs, 8));
            verifyEqual(testCase, outputs.i_row_pf(1:16), repmat([1;2;5;4], 4, 1));
            verifyEqual(testCase, outputs.j_col_pf(17:32), repelem([2;3;6;5], 4));
            verifySize(testCase, outputs.M_vector, [96 1]);
            verifySize(testCase, outputs.eps_vector, [192 1]);
        end

        function testRejectsNonpositiveJacobian(testCase)
            input = oneElementInput();
            input.MESH.elem = [1 4 3 2];
            verifyError(testCase, @() callReference(input), ...
                'rebuiltMexQ1:NonpositiveJacobian');
        end

        function testRejectsMalformedInputsBeforeAssembly(testCase)
            input = oneElementInput();
            input.field_vars(2) = NaN;
            verifyError(testCase, @() callReference(input), ...
                'rebuiltMexQ1:InvalidInput');

            input = oneElementInput();
            input.MESH.elem(1) = 0;
            verifyError(testCase, @() callReference(input), ...
                'rebuiltMexQ1:InvalidInput');

            input = oneElementInput();
            input.QUADRATURE.Nxi(:, 1) = 0.2;
            verifyError(testCase, @() callReference(input), ...
                'rebuiltMexQ1:InvalidInput');
        end
    end
end

function outputs = callReference(input)
[values{1:12}] = assemble_initial_reference_q4(input.MESH, input.DOFS, ...
    input.t, input.QUADRATURE, input.MAT_CHAR, input.CC, input.field_vars);
names = outputNames();
outputs = cell2struct(values(:), names, 1);
end

function names = outputNames()
names = {'K_vect'; 'i_row'; 'j_col'; 'M_vector'; 'i_row_sig'; ...
    'j_col_sig'; 'eps_vector'; 'i_row_eps'; 'j_col_eps'; ...
    'sig0_vector'; 'i_row_pf'; 'j_col_pf'};
end

function input = oneElementInput()
mesh = struct('num_node', 4, 'num_elem', 1, 'nel', 4, 'dim', 2, ...
    'tensors', 3, 'node', [0 0; 1 0; 1 1; 0 1], ...
    'elem', [1 2 3 4], 'elem_material_id', 1);
dofs = struct('num_dof_node', 2, 'num_dof', 8);
quadrature = struct('num_gauss_pts', 1, 'gauss_W', 4, ...
    'dNdxi', reshape([-0.25 0.25 0.25 -0.25; ...
                      -0.25 -0.25 0.25 0.25], 2, 4, 1), ...
    'Nxi', 0.25 * ones(4, 1));
input = struct('MESH', mesh, 'DOFS', dofs, 't', 2, ...
    'QUADRATURE', quadrature, 'MAT_CHAR', struct('res_stiff', 0.1), ...
    'CC', diag([2 3 4]), 'field_vars', [0; 0.2; 0.4; 0.6]);
end

function input = twoElementInput()
input = oneElementInput();
input.MESH.num_node = 6;
input.MESH.num_elem = 2;
input.MESH.node = [0 0; 1 0; 2 0; 0 1; 1 1; 2 1];
input.MESH.elem = [1 2 5 4; 2 3 6 5];
input.MESH.elem_material_id = [1; 1];
input.DOFS.num_dof = 12;
input.field_vars = [0; 0.1; 0.2; 0.3; 0.4; 0.5];
end
