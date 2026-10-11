! Copyright (C) 2021-2023 ETH Zurich, SIS ID and CompMech D-MAVT
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
! [K_vect, res_displ, history_vars_new] = AMOR(...
!     MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC,...
!     field_vars, displ, field_vars_coupling,
!     stress_state,...
!     history_vars_old...
! );
!===============================================================================
! Purpose: Calculation of the non zero entries of the tangent stiffness matrix, the undamaged strain energy 
! at every Gauss Point and the displacement residual vector. The H. Amor (voumetric-deviatoric) damage split is applied.
!
! Inputs:
! MESH          --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS          --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t             --> MATLAB Scalar representing the specimen thickness
! QUADRATURE    --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives ...
! MAT_CHAR      --> MATLAB Matrix with materials' parameters: Young Modulus, Poisson ratio, Fracture toughness ...
! CC            --> MATLAB Matrix representing the undamaged stiffness tensor in Voigt notation
! displ         --> MATLAB Vector representing the displacement field at the nodes
! field_vars_old  --> MATLAB Vector representing the damage field at the nodes at the previous time step
! field_vars_coupling    --> MATLAB Vector representing the damage field at the nodes
! stress_state  --> MATLAB Scalar (Integer) representing the PlaneStrain (1) or PlaneStress (2)
! history_vars_old --> Not used in this routine
!
! Outputs:
! K_vect          --> MATLAB Vector representing the nonzero entries of the tangent stiffness matrix
! res_displ       --> MATRAL Vector representing the displacement residual vector
! history_vars_new --> MATALB array, (:,:,1) is unchanged history_vars_old(:,:,1), (:,:,2) represents the strain energy at every Gauss point i! history_vars_new
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t, DOF_t
  use mod_equilibrium_amor, only: equilibrium_amor
  use mex_utils, only: &
       real_from_matlab, vector_real_from_matlab, &
       integer_from_matlab, vector_integer_from_matlab, &
       matrix_real_from_matlab, tensor_3_real_from_matlab, &
       dof_from_matlab, mesh_from_matlab, quadrature_from_matlab, &
       CC_from_matlab, vector_MAT_CHAR_from_matlab, &
       mex_double_array_3
  use scalar_utils, only: dp

  implicit none

  integer nlhs, nrhs

  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)

  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr, mxDuplicateArray

  !     Pointers to output mxArrays:
  mwPointer KK_pr, res_displ_pr, strain_en_undgr_pr

  !Allocate memory for variable
  type(MESH_t) :: MESH
  type(DOF_t) :: DOF
  type(QUADRATURE_t) :: QUADRATURE
  type(MAT_CHAR_t), dimension(:), allocatable :: MAT_CHAR
  real(kind=dp) t
  integer num_entries

  !Dynamic allocation INPUT PARAMETERS

  real(kind=dp), allocatable :: CC_mat(:, :, :)
  real(kind=dp), allocatable :: pfield(:), displ(:)

  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: KK_vector(:), res_displ(:, :), strain_en_undgr(:, :)

  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 11) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nInput', '11 inputs required.')
  elseif (nlhs .ne. 4) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '4 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  call dof_from_matlab(DOF, prhs(2))
  call real_from_matlab(t, mxGetPr(prhs(3)))
  call quadrature_from_matlab(QUADRATURE, prhs(4))
  call vector_MAT_CHAR_from_matlab(MAT_CHAR, prhs(5))
  call CC_from_matlab(CC_mat, mxGetPr(prhs(6)), MESH%tensors, size(MAT_CHAR))
  call vector_real_from_matlab(displ, mxGetPr(prhs(7)), DOF%num_dof)
  ! field_vars_old not used
  call vector_real_from_matlab(pfield, mxGetPr(prhs(9)), MESH%num_node)
  ! stress_state not used
  ! history_vars_old not used

  !=================================================================
  num_entries = MESH%nel * DOF%num_dof_node * MESH%nel * DOF%num_dof_node
  allocate (KK_vector(MESH%num_elem*num_entries))
  allocate (res_displ(DOF%num_dof, 1))
  allocate (strain_en_undgr(MESH%num_elem, QUADRATURE%num_gauss_pts))

  ! history_vars(:, :, 2) is strain_en_undgr
  call equilibrium_amor(MESH, DOF, t, QUADRATURE, MAT_CHAR, &
       CC_mat, pfield, displ, num_entries, &
       KK_vector, res_displ, strain_en_undgr)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(MESH%num_elem*num_entries, 1, 0)
  plhs(2) = mxCreateDoubleMatrix(DOF%num_dof, 1, 0)
  plhs(3) = mxCreateDoubleMatrix(MESH%num_elem, QUADRATURE%num_gauss_pts, 0)
  plhs(4) = mxDuplicateArray(prhs(11))
  
  KK_pr = mxGetPr(plhs(1))
  res_displ_pr = mxGetPr(plhs(2))
  strain_en_undgr_pr = mxGetPr(plhs(3))
  
  call mxCopyReal8ToPtr(KK_vector, KK_pr, MESH%num_elem*num_entries)
  call mxCopyReal8ToPtr(res_displ, res_displ_pr, DOF%num_dof)
  call mxCopyReal8ToPtr(strain_en_undgr, strain_en_undgr_pr, MESH%num_elem*QUADRATURE%num_gauss_pts)

  return
end subroutine mexFunction
