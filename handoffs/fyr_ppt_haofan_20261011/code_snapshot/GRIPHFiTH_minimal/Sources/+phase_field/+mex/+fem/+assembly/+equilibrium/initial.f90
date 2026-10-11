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
!===============================================================================
! [ ...
!     K_vect, i_row, j_col, M_vector, i_row_sig, j_col_sig, ...
!     eps_vector, i_row_eps, j_col_eps, sig0_vector, i_row_pf, j_col_pf ...
! ] =
! initial(MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, field_vars)
!===============================================================================
! Purpose: Initial calculation of the nonzero entries of the tangent stiffness matrix K, the L2 interpolation matrix M (Smoothing matrix), 
! and the strains/stresses right hand side vectors for required for L2 interpolation. 
!
! Inputs:
! MESH          --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS          --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t             --> MATLAB Scalar representing the specimen thickness
! QUADRATURE  --> MATLAB Structure array with Quadrature parameters: Gauss points, weights, shape functions, their derivatives...
! MAT_CHAR      --> MATLAB Matrix with materials' parameters: Young Modulus, Poisson ratio, Fracture toughness ...
! CC          --> MATLAB Matrix representing the stiffness tensor in Voigt Notation
! field_vars  --> MATLAB Vector representing the damage field at the nodes
!
! Outputs:   
! K_vect      --> MATLAB Vector representing the nonzero entries of the tangent stiffness matrix
! i_row       --> MATLAB Vector representing the row indexes of the nonzero entries of the tangent stiffness matrix
! j_col       --> MATLAB Vector representing the column indexes of the nonzero entries of the tangent stiffness matrix
! M_vector    --> MATLAB Vector representing the nonzero entries of the L2 interpolation matrix
! i_row_sig   --> MATLAB Vector representing the row indexes of the nonzero entries of the L2 interpolation matrix
! j_col_sig   --> MATLAB Vector representing the column indexes of the nonzero entries of the L2 interpolation matrix
! eps_vector  --> MATLAB Vector representing the nonzeros entries of the strains calculated at the gauss points, used with M to interpolate the strains to the nodes
! i_row_eps   --> MATLAB Vector representing the row indexes of the nonzero entries of the eps_vector 
! j_col_eps   --> MATLAB Vector representing the column indexes of the nonzero entries of the eps_vector 
! sig0_vector --> MATLAB Vector representing the nonzeros entries of the Stresses calculated at the gauss points, used with M to interpolate the stresses to the nodes
! i_row_pf    --> MATLAB Vector representing the row indexes of the nonzero entries of the sig0_vector
! j_col_pf    --> MATLAB Vector representing the column indexes of the nonzero entries of the sig0_vector
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t, DOF_t
  use mod_equilibrium_initial, only: equilibrium_initial
  use matrix_utils, only: m22inv, m33inv
  use mex_utils, only: &
       real_from_matlab, vector_real_from_matlab, &
       integer_from_matlab, vector_integer_from_matlab, &
       dof_from_matlab, mesh_from_matlab, quadrature_from_matlab, &
       CC_from_matlab, vector_MAT_CHAR_from_matlab
  use scalar_utils, only: dp

  implicit none

  integer nlhs, nrhs

  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)

  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr

  !     Pointers to output mxArrays:
  mwPointer KK_pr, i_row_pr, j_col_pr, sig0_pr, i_row_pf_pr, j_col_pf_pr, &
       M_pr, i_row_sig_pr, j_col_sig_pr, eps_pr, i_row_eps_pr, j_col_eps_pr

  !Allocate memory for variable
  type(MESH_t) :: MESH
  type(DOF_t) :: DOF
  type(QUADRATURE_t) :: QUADRATURE
  type(MAT_CHAR_t), dimension(:), allocatable :: MAT_CHAR
  real(kind=dp) t

  !Dynamic allocation INPUT PARAMETERS

  real(kind=dp), allocatable :: CC_mat(:, :, :)
  real(kind=dp), allocatable :: field_vars(:)

  !Dynamic allocation REAL-TO-INT PARAMETERS
  real(kind=dp), allocatable :: db_i_row(:), db_j_col(:), db_i_row_sig(:), &
       db_j_col_sig(:), db_i_row_eps(:), db_j_col_eps(:), db_i_row_pf(:), db_j_col_pf(:)

  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  integer, allocatable :: i_row(:), j_col(:), i_row_sig(:), j_col_sig(:), &
       i_row_eps(:), j_col_eps(:), i_row_pf(:), j_col_pf(:)
  real(kind=dp), allocatable :: KK_vector(:), &
       M_vector(:), eps_vector(:), sig0_vector(:)

  integer num_entries

  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 7) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nInput', '7 inputs required.')
  elseif (nlhs .ne. 12) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '12 outputs required.')
  end if


  call mesh_from_matlab(MESH, prhs(1))
  call dof_from_matlab(DOF, prhs(2))
  call real_from_matlab(t, mxGetPr(prhs(3)))
  call quadrature_from_matlab(QUADRATURE, prhs(4))
  call vector_MAT_CHAR_from_matlab(MAT_CHAR, prhs(5))
  call CC_from_matlab(CC_mat, mxGetPr(prhs(6)), MESH%tensors, size(MAT_CHAR))
  call vector_real_from_matlab(field_vars, mxGetPr(prhs(7)), MESH%num_node)

  !=================================================================
  num_entries = MESH%nel * DOF%num_dof_node * MESH%nel * DOF%num_dof_node
  allocate (KK_vector(MESH%num_elem*num_entries))
  allocate (i_row(MESH%num_elem*num_entries))
  allocate (j_col(MESH%num_elem*num_entries))
  allocate (M_vector(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel))
  allocate (i_row_sig(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel))
  allocate (j_col_sig(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel))
  allocate (eps_vector(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (sig0_vector(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (i_row_eps(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (j_col_eps(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (i_row_pf(MESH%num_elem*MESH%nel*MESH%nel))
  allocate (j_col_pf(MESH%num_elem*MESH%nel*MESH%nel))

  call equilibrium_initial(MESH, DOF, t, QUADRATURE, MAT_CHAR, CC_mat, field_vars, num_entries, &
       KK_vector, i_row, j_col, M_vector, &
       i_row_sig, j_col_sig, eps_vector, &
       i_row_eps, j_col_eps, &
       sig0_vector, &
       i_row_pf, j_col_pf)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(MESH%num_elem*num_entries, 1, 0) !KK vector
  plhs(2) = mxCreateDoubleMatrix(MESH%num_elem*num_entries, 1, 0) !row indices for KK vector
  plhs(3) = mxCreateDoubleMatrix(MESH%num_elem*num_entries, 1, 0) !col indices for KK vector
  plhs(4) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel, 1, 0) !M vector
  plhs(5) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel, 1, 0) !row indeces for M vector
  plhs(6) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel, 1, 0) !col indices for M vector
  plhs(7) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node, 1, 0) !eps vector
  plhs(8) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node, 1, 0) !row indices for eps vector
  plhs(9) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node, 1, 0) !col indices for eps vector
  plhs(10) = mxCreateDoubleMatrix(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node, 1, 0) !sig0 vector
  plhs(11) = mxCreateDoubleMatrix(MESH%num_elem*MESH%nel*MESH%nel, 1, 0) !row indeces for KK_d vector
  plhs(12) = mxCreateDoubleMatrix(MESH%num_elem*MESH%nel*MESH%nel, 1, 0) !col indices for KK_d vector

  KK_pr = mxGetPr(plhs(1))
  i_row_pr = mxGetPr(plhs(2))
  j_col_pr = mxGetPr(plhs(3))
  M_pr = mxGetPr(plhs(4))
  i_row_sig_pr = mxGetPr(plhs(5))
  j_col_sig_pr = mxGetPr(plhs(6))
  eps_pr = mxGetPr(plhs(7))
  i_row_eps_pr = mxGetPr(plhs(8))
  j_col_eps_pr = mxGetPr(plhs(9))
  sig0_pr = mxGetPr(plhs(10))
  i_row_pf_pr = mxGetPr(plhs(11))
  j_col_pf_pr = mxGetPr(plhs(12))

  allocate (db_i_row(MESH%num_elem*num_entries))
  allocate (db_j_col(MESH%num_elem*num_entries))
  allocate (db_i_row_sig(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel))
  allocate (db_j_col_sig(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel))
  allocate (db_i_row_eps(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (db_j_col_eps(MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node))
  allocate (db_i_row_pf(MESH%num_elem*MESH%nel*MESH%nel))
  allocate (db_j_col_pf(MESH%num_elem*MESH%nel*MESH%nel))

  db_i_row = real(i_row, 8)
  db_j_col = real(j_col, 8)
  db_i_row_sig = real(i_row_sig, 8)
  db_j_col_sig = real(j_col_sig, 8)
  db_i_row_eps = real(i_row_eps, 8)
  db_j_col_eps = real(j_col_eps, 8)
  db_i_row_pf = real(i_row_pf, 8)
  db_j_col_pf = real(j_col_pf, 8)

  deallocate (i_row, j_col, i_row_sig, j_col_sig, i_row_eps, j_col_eps, i_row_pf, j_col_pf)

  call mxCopyReal8ToPtr(KK_vector, KK_pr, MESH%num_elem*num_entries)
  call mxCopyReal8ToPtr(db_i_row, i_row_pr, MESH%num_elem*num_entries)
  call mxCopyReal8ToPtr(db_j_col, j_col_pr, MESH%num_elem*num_entries)
  call mxCopyReal8ToPtr(M_vector, M_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel)
  call mxCopyReal8ToPtr(db_i_row_sig, i_row_sig_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel)
  call mxCopyReal8ToPtr(db_j_col_sig, j_col_sig_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel)
  call mxCopyReal8ToPtr(eps_vector, eps_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node)
  call mxCopyReal8ToPtr(db_i_row_eps, i_row_eps_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node)
  call mxCopyReal8ToPtr(db_j_col_eps, j_col_eps_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node)
  call mxCopyReal8ToPtr(sig0_vector, sig0_pr, MESH%num_elem*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node)
  call mxCopyReal8ToPtr(db_i_row_pf, i_row_pf_pr, MESH%num_elem*MESH%nel*MESH%nel)
  call mxCopyReal8ToPtr(db_j_col_pf, j_col_pf_pr, MESH%num_elem*MESH%nel*MESH%nel)

  return
end subroutine mexFunction
