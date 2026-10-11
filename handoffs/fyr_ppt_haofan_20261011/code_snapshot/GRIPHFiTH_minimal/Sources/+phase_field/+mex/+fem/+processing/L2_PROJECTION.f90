! Copyright (C) 2021 ETH Zurich, SIS ID and CompMech D-MAVT
!
! Licensed under the Apache License, Version 2.0 (the "License");
! you may not use this file except in compliance with the License.
! You may obtain a copy of the License at
!
!    http://www.apache.org/licenses/LICENSE-2.0
!
! Unless required by applicable law or agreed to in writing, software
! distributed under the License is distributed on an "AS IS" BASIS,
! WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
! See the License for the specific language governing permissions and
! limitations under the License.
#include "fintrf.h"
!======================================================================
! [hist, history_p_field, stress_L2] = ...
! phase_field.mex.fem.processing.post_processing(...
!     MESH, DOFS, t, num_materials, QUADRATURE, CC, p_field,...
!     strain_en_undgr, history_p_field...
! );
!======================================================================
! Purpose: Construct the right hand side vectors for L2 interpolation of the History variable  and the Stresses
!
! Inputs:
! MESH            --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS            --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t               --> MATLAB Scalar representing the specimen thickness
! num_materials   --> MATLAB Scalar (Integer) representing the number of material types
! QUADRATURE      --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives ...
! CC              --> MATLAB Matrix representing the stiffness tensor in Voigt Notation
! p_field         --> MATLAB Vector representing the damage field at the nodes
! history_p_field --> MATALB Matrix representing the history variable at every Gauss point in the system
!
! Outputs:
! hist            --> MATLAB Vector representing the right hand side vector needed to interpolate the history variable to the nodes
! history_p_field --> MATALB Matrix representing the history variable at every Gauss point in the system
! stress_L2      --> MATLAB Matrix representing the right hand side vector needed to interpolate the stresses to the nodes
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: QUADRATURE_t, MESH_t, DOF_t
  use mod_l2_projection, only: l2_projection
  use mex_utils, only: &
       CC_from_matlab, vector_MAT_CHAR_from_matlab, &
       vector_real_from_matlab, &
       real_from_matlab, integer_from_matlab, &
       matrix_real_from_matlab, vector_integer_from_matlab, &
       tensor_3_real_from_matlab, &
       dof_from_matlab, mesh_from_matlab, quadrature_from_matlab
  use scalar_utils, only: dp
  use matrix_utils, only: m22inv, m33inv

  implicit none

  integer nlhs, nrhs
  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)
  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr
  !     Pointers to output mxArrays:
  mwPointer stress_L2_pr, history_vars_L2_pr

  !Allocate memory for variable
  type(MESH_t) :: MESH
  type(DOF_t) :: DOF
  type(QUADRATURE_t) :: QUADRATURE
  real(kind=dp) t

  !Dynamic allocation INPUT PARAMETERS
  real(kind=dp), allocatable :: CC_mat(:, :, :)
  real(kind=dp), allocatable :: pfield(:)

  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: history_vars(:, :, :), stress_L2(:), history_vars_L2(:, :)

  integer num_materials, num_history_vars

  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 9) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nInput', '9 inputs required.')
  elseif (nlhs .ne. 2) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '3 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  call dof_from_matlab(DOF, prhs(2))
  call real_from_matlab(t, mxGetPr(prhs(3)))
  call integer_from_matlab(num_materials, mxGetPr(prhs(4)))
  call quadrature_from_matlab(QUADRATURE, prhs(5))
  call CC_from_matlab(CC_mat, mxGetPr(prhs(6)), MESH%tensors, num_materials)
  call vector_real_from_matlab(pfield, mxGetPr(prhs(7)), MESH%num_node)
  call integer_from_matlab(num_history_vars, mxGetPr(prhs(8)))
  call tensor_3_real_from_matlab(history_vars, prhs(9), MESH%num_elem, QUADRATURE%num_gauss_pts, num_history_vars)

  !=================================================================
  allocate (stress_L2(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (history_vars_L2(MESH%num_node, num_history_vars))

  call l2_projection(MESH, DOF, t, QUADRATURE, CC_mat, &
       pfield, num_history_vars, history_vars, history_vars_L2, stress_L2)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(MESH%num_node, num_history_vars, 0)
  plhs(2) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node, 1, 0)

  history_vars_L2_pr = mxGetPr(plhs(1))
  stress_L2_pr = mxGetPr(plhs(2))

  call mxCopyReal8ToPtr(history_vars_L2, history_vars_L2_pr, MESH%num_node*num_history_vars)
  call mxCopyReal8ToPtr(stress_L2, stress_L2_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node)

  return
end subroutine mexFunction
