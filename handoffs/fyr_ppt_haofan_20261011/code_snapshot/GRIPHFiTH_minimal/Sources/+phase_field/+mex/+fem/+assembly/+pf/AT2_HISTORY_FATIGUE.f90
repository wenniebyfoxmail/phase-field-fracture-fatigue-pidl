! Copyright (C) 2021-2022 ETH Zurich, SIS ID and CompMech D-MAVT
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
! [K_d_vect, res_field_vars, history_vars_new] = AT2_HISTORY(...
!     MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, ...
!     field_vars, field_vars_old, field_vars_coupling,...
!     stress_state,...
!     history_vars_old...
! );
!===============================================================================
! Purpose: Calculation of the non zero entries of the damage (phase-field) tangent stiffness matrix and the damage (phase-field) residual vector, 
! using 'AT2' for the energy dissipation function and 'History variable method' for the irreversibility
!
! Inputs:
! MESH             --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS             --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t                --> MATLAB Scalar representing the specimen thickness
! QUADRATURE       --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives ...
! MAT_CHAR         --> MATLAB Matrix with materials' parameters: Young Modulus, Poisson ratio, Fracture toughness ...
! CC               --> MATLAB Matrix representing the undamaged stiffness tensor in Voigt notation
! field_vars       --> MATLAB Vector representing the damage field at the nodes
! field_vars_old   --> MATLAB Vector representing the damage field at the nodes at the previous time step
! field_vars_coupling  --> MATLAB Vector coupling field vars
! stress_state     --> MATLAB Scalar (Integer) representing the PlaneStrain (1) or PlaneStress (2)
! history_vars_old --> MATALB Matrix representing the history variable at every Gauss point in the system
!
! Outputs:
! K_d_vect         --> MATLAB Vector representing the nonzero entries of the damage (phase-field) tangent stiffness matrix
! res_field_vars   --> MATLAB Vector representing the damage (phase-field) residual vector
! history_vars_new --> Copy of history_vars_old
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
  use mod_pf_at2_history_fatigue, only: pf_at2_history_fatigue
  use mex_utils, only: &
       real_from_matlab, vector_real_from_matlab, &
       integer_from_matlab, vector_integer_from_matlab, &
       matrix_real_from_matlab, &
       tensor_3_real_from_matlab, &
       mesh_from_matlab, quadrature_from_matlab, &
       vector_MAT_CHAR_from_matlab, &
       cp_struct_field_matrix_real_alloc
  use scalar_utils, only: dp

  implicit none

  integer nlhs, nrhs

  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)

  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr, mxDuplicateArray, mxCreateNumericArray
  integer*4 mxClassIDFromClassName

  !     Pointers to output mxArrays:
  mwPointer KK_d_pr, res_p_field_pr, history_vars_new_pr

  !Allocate memory for variable
  !Dynamic allocation INPUT PARAMETERS
  type(MESH_t) :: MESH
  type(QUADRATURE_t) :: QUADRATURE
  type(MAT_CHAR_t), dimension(:), allocatable :: MAT_CHAR

  real(kind=dp), allocatable :: strain_en_undgr(:, :), history_vars_old(:, :, :), pfield(:)
  integer :: dims(3)

  real(kind=dp) t

  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: KK_d_vector(:), res_p_field(:), history_vars_new(:, :, :)


  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 11) then
     call mexErrMsgIdAndTxt('MATLAB:prhs_assembly:nInput', '11 inputs required.')
  elseif (nlhs .ne. 4) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '4 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  ! DOFS not used
  call real_from_matlab(t, mxGetPr(prhs(3)))
  call quadrature_from_matlab(QUADRATURE, prhs(4))
  call vector_MAT_CHAR_from_matlab(MAT_CHAR, prhs(5))
  ! CC not used
  call vector_real_from_matlab(pfield, mxGetPr(prhs(7)), MESH%num_node)
  ! pfield_old not used
  call matrix_real_from_matlab(strain_en_undgr, mxGetPr(prhs(9)), MESH%num_elem, QUADRATURE%num_gauss_pts)
  ! stress_state not used
  call tensor_3_real_from_matlab(history_vars_old, prhs(11), MESH%num_elem, QUADRATURE%num_gauss_pts, 4)

  !=================================================================
  allocate (KK_d_vector(MESH%num_elem*MESH%nel*MESH%nel))
  allocate (res_p_field(MESH%num_node))
  allocate (history_vars_new(MESH%num_elem,QUADRATURE%num_gauss_pts,4))

  call pf_at2_history_fatigue(MESH, t, QUADRATURE, MAT_CHAR, strain_en_undgr, &
       history_vars_old, pfield, KK_d_vector, res_p_field, history_vars_new)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(MESH%num_elem*MESH%nel*MESH%nel, 1, 0)
  plhs(2) = mxCreateDoubleMatrix(MESH%num_node, 1, 0)
  plhs(3) = mxDuplicateArray(prhs(7))
  dims(1) = MESH%num_elem
  dims(2) = QUADRATURE%num_gauss_pts
  dims(3) = 4
  plhs(4) = mxCreateNumericArray(3, dims, mxClassIDFromClassName('double'), 0)
  
  KK_d_pr = mxGetPr(plhs(1))
  res_p_field_pr = mxGetPr(plhs(2))
  history_vars_new_pr = mxGetPr(plhs(4))
  
  call mxCopyReal8ToPtr(KK_d_vector, KK_d_pr, MESH%num_elem*MESH%nel*MESH%nel)
  call mxCopyReal8ToPtr(res_p_field, res_p_field_pr, MESH%num_node)
  call mxCopyReal8ToPtr(history_vars_new, history_vars_new_pr, dims(1)*dims(2)*dims(3))
  
  return
end subroutine mexFunction
