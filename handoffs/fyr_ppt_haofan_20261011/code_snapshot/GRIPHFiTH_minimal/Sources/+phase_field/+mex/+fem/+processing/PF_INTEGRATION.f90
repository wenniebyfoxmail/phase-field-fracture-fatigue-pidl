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
! int_d = phase_field.mex.fem.processing.PF_INTEGRATION(
!    sys.MESH,
!    sys.GEOM.t,
!    sys.QUADRATURE,
!    p_field,
!    CRACK_PAR.rel_pf);
!===============================================================================
! Purpose: integration of the phase-field integral (with d>d_rel) for the smeared crack length concept
!
! Inputs:
! MESH            --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! t               --> MATLAB Scalar representing the specimen thickness
! QUADRATURE      --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives ...
! p_field         --> MATLAB Vector representing the damage field at the nodes
!
! Outputs:
! d_int           --> MATLAB Scalar for the integrated phase-field over the whole domain
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
  use mod_pf_integration, only: pf_integration
  use mex_utils, only: &
       real_from_matlab, vector_real_from_matlab, &
       integer_from_matlab, vector_integer_from_matlab, &
       matrix_real_from_matlab, &
       mesh_from_matlab, quadrature_from_matlab, &
       vector_MAT_CHAR_from_matlab
  use scalar_utils, only: dp
  
  implicit none

  integer nlhs, nrhs

  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)

  !     Function declarations:
  mwPointer mxCreateDoubleMatrix, mxGetPr

  !     Pointers to output mxArrays:
  mwPointer d_int_pr

  !Allocate memory for variable
  !Dynamic allocation INPUT PARAMETERS
  type(MESH_t) :: MESH
  type(QUADRATURE_t) :: QUADRATURE
  real(kind=dp), allocatable :: pfield(:)
  real(kind=dp) t, rel_pf
  
  !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
  real(kind=dp), allocatable :: d_int(:)


  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 5) then
     call mexErrMsgIdAndTxt('MATLAB:prhs_assembly:nInput', '5 inputs required.')
  elseif (nlhs .ne. 1) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '1 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  call real_from_matlab(t, mxGetPr(prhs(2)))
  call quadrature_from_matlab(QUADRATURE, prhs(3))
  call vector_real_from_matlab(pfield, mxGetPr(prhs(4)), MESH%num_node)
  call real_from_matlab(rel_pf, mxGetPr(prhs(5)))

  !=================================================================
  allocate (d_int(1))

  call pf_integration(MESH, t, QUADRATURE, pfield, rel_pf, d_int)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleMatrix(1, 1, 0) !d_int

  d_int_pr = mxGetPr(plhs(1))

  call mxCopyReal8ToPtr(d_int, d_int_pr, 1)

  return
end subroutine mexFunction
