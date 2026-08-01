classdef ToyRoadRecoverySystem < handle
    properties
        MAT_CHAR
        GEOM
        QUADRATURE
        DOFS
        NODE_BOUNDARIES
        SOL_STEP_PAR
        MESH
        stress_state
        diss_fct
        STIFFNESS_MATRIX
        damage_at_construction
    end

    methods
        function self = ToyRoadRecoverySystem(matChar, geom, quadrature, dofs, ...
                nodeBoundaries, solStepPar, mesh, stressState, pField, dissFct, ...
                stiffnessMatrix)
            self.MAT_CHAR = matChar;
            self.GEOM = geom;
            self.QUADRATURE = quadrature;
            self.DOFS = dofs;
            self.NODE_BOUNDARIES = nodeBoundaries;
            self.SOL_STEP_PAR = solStepPar;
            self.MESH = mesh;
            self.stress_state = stressState;
            self.diss_fct = dissFct;
            self.STIFFNESS_MATRIX = stiffnessMatrix;
            self.damage_at_construction = pField;
        end
    end
end
