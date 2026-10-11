! Copyright (C) 2026 ETH Zurich, SIS ID and CompMech D-MAVT
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
! [K_d_vect, res_field_vars, history_vars_new] = PF_CZM_FATIGUE(...
!     MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, ...
!     field_vars, field_vars_old, strain_en_undgr,...
!     stress_state,...
!     history_vars_old...
! );
!===============================================================================
! Wu PF-CZM phase-field + Carrara unidirectional fatigue (Wu 2017 IJSS /
! Baktheer 2024). Rational-fraction degradation g(d), geometric function
! alpha(d) = 2d - d^2 with c_alpha = pi. Driving force is the Wu Y = <sigma_1>_+^2
! / (2 E_0) supplied via strain_en_undgr from PF_CZM equilibrium kernel.
!
! Carrara fatigue uses degraded driving force g(d)*Y for Δᾱ accumulator;
! fat_deg = (2*alpha_T / (alpha_bar + alpha_T))^p multiplies the geometric
! G_c terms only (Baktheer 2024 Eq. 38 + page-9 prose).
!
! history_vars convention (4 slots per element/Gauss-point):
!   k=1 : H (max Y over time, initialize to H_min = f_t^2/(2*E) in driver)
!   k=2 : alpha_bar (Carrara accumulator)
!   k=3 : g(d_prev) * Y_prev (for Carrara Δᾱ computation)
!   k=4 : fat_deg = f(alpha_bar)
!
! Author: Windows-FEM (FEM-9 Task G, 2026-05-12)
! Pattern: identical to AT2_HISTORY_FATIGUE.f90 wrapper.
!===============================================================================
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
  use mod_pf_pf_czm_fatigue, only: pf_pf_czm_fatigue
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

  ! mexFunction arguments:
  mwPointer plhs(*), prhs(*)

  ! Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr, mxDuplicateArray, mxCreateNumericArray
  integer*4 mxClassIDFromClassName

  ! Pointers to output mxArrays:
  mwPointer KK_d_pr, res_p_field_pr, history_vars_new_pr

  ! Dynamic allocation INPUT PARAMETERS
  type(MESH_t) :: MESH
  type(QUADRATURE_t) :: QUADRATURE
  type(MAT_CHAR_t), dimension(:), allocatable :: MAT_CHAR

  real(kind=dp), allocatable :: strain_en_undgr(:, :), history_vars_old(:, :, :), pfield(:)
  integer :: dims(3)

  real(kind=dp) t

  ! Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: KK_d_vector(:), res_p_field(:), history_vars_new(:, :, :)

  !=================================================================
  ! Check for proper number of arguments.
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
  allocate (history_vars_new(MESH%num_elem, QUADRATURE%num_gauss_pts, 4))

  call pf_pf_czm_fatigue(MESH, t, QUADRATURE, MAT_CHAR, strain_en_undgr, &
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
