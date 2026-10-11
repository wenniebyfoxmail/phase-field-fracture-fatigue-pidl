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
!===============================================================================
! [...
!     D_RHS_tract ...
! ] = ...
! D_tract_assembly(MESH, DOFS, t, QUADRATURE, BOUNDARY_CONDS)
!===============================================================================
! Purpose: Assembly of the nodal force vector due to an increment in the surface tractions
!
! Inputs:
!! MESH          --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS           --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t              --> MATLAB Scalar representing the specimen thickness
! QUADRATURE     --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives...
! BOUNDARY_CONDS --> MATLAB Structure array with boundary conditions parameters: load increments, Dirichlet and Neumann nodes, ... 
!
! Outputs:
! D_RHS_tract    --> MATLAB Vector representing the nodal force vector associated to an increment in surface tractions.
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use mod_d_tract_assembly, only: d_tract_assembly
  use array_utils, only: distance2d
  use mex_utils, only: BOUNDARY_CONDS_t, QUADRATURE_t, MESH_t, DOF_t, real_from_matlab,&
       dof_from_matlab, mesh_from_matlab, quadrature_from_matlab,&
       boundary_conds_from_matlab
  use scalar_utils, only: dp

  implicit none

  integer nlhs, nrhs
  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)
  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr
  !     Pointers to output mxArrays:
  mwPointer D_RHS_tract_pr

  !Allocate memory for variable
  !Dynamic allocation INPUT PARAMETERS
  type(MESH_t) :: MESH
  type(DOF_t) :: DOF
  type(QUADRATURE_t) :: QUADRATURE
  type(BOUNDARY_CONDS_t) :: BOUNDARY_CONDS

  real(kind=dp) t
  real(kind=dp) i_step

  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: D_RHS_tract(:)

  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 6) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nInput', '6 inputs required.')
  elseif (nlhs .ne. 1) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '1 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  call dof_from_matlab(DOF, prhs(2))
  call real_from_matlab(t, mxGetPr(prhs(3)))
  call quadrature_from_matlab(QUADRATURE, prhs(4))
  call boundary_conds_from_matlab(BOUNDARY_CONDS, prhs(5), MESH%num_elem, MESH%nel)
  call real_from_matlab(i_step, mxGetPr(prhs(6)))
  !=================================================================
  allocate (D_RHS_tract(DOF%num_dof))

  call d_tract_assembly(MESH, DOF, t, QUADRATURE, BOUNDARY_CONDS, i_step, &
       D_RHS_tract)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(DOF%num_dof, 1, 0) !D_RHS_tract vector

  D_RHS_tract_pr = mxGetPr(plhs(1))

  call mxCopyReal8ToPtr(D_RHS_tract, D_RHS_tract_pr, DOF%num_dof)

  return
end subroutine
