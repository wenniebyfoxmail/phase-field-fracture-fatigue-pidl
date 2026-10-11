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
! fract_en = phase_field.mex.fem.processing.fracture_energy(...
!     MESH, t, QUADRATURE, MAT_CHAR, CC, p_field, c_w, order...
! );
!======================================================================
! Purpose: Calculation of the total fracture energy of the system 
!
! Inputs:
! MESH            --> MATLAB Structure array with mesh parameters: number of nodes, number of elements, number of elements on Neumann boundary ...
! DOFS            --> MATLAB Structure array with degrees of freedom (dof) parameters: number of dof, number of dof per node, number of dof on Neumann boundary ...
! t               --> MATLAB Scalar representing the specimen thickness
! QUADRATURE      --> MATLAB Structure array with quadrature parameters: Gauss points, weights, shape functions, their derivatives...
! MAT_CHAR        --> MATLAB Matrix with materials' parameters: Young Modulus, Poisson ratio, Fracture toughness ...
! CC              --> MATLAB Matrix representing the stiffness tensor in Voigt Notation
! p_field         --> MATLAB Vector representing the damage field at the nodes
! c_w: prefactor, should be chosen to be 8/3 for AT1 or 2 for AT2.
! order: integer power of the dot product dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield)
!        involved in the computation, should be chosen to be 1 for AT1 or 2 for AT2.
!
! Outputs:
! fract_en     --> MATLAB Scalar representing the total fracture energy of the system
!===============================================================================
!-----
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
  use mod_fracture_energy, only: fracture_energy
  use mex_utils, only:&
       CC_from_matlab, vector_MAT_CHAR_from_matlab,&
       real_from_matlab,integer_from_matlab,&
       vector_real_from_matlab, vector_integer_from_matlab,&
       mesh_from_matlab, quadrature_from_matlab
  use scalar_utils, only: dp

  implicit none

  integer nlhs, nrhs
  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)
  !     Function declarations:
  mwPointer mxGetPr, mxCreateDoubleScalar

  !Allocate memory for variable
  type(MESH_t) :: MESH
  type(QUADRATURE_t) :: QUADRATURE
  type(MAT_CHAR_t), dimension(:), allocatable :: MAT_CHAR
  real(kind=dp) t, c_w, fract_en
  integer order

  real(kind=dp), allocatable :: CC_mat(:, :, :), pfield(:)


  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 8) then
     call mexErrMsgIdAndTxt('MATLAB:fracture_energy:nInput', '8 inputs required.')
  elseif (nlhs .ne. 1) then
     call mexErrMsgIdAndTxt('MATLAB:fracture_energy:nOutput', '1 outputs required.')
  end if

  call mesh_from_matlab(MESH, prhs(1))
  call real_from_matlab(t, mxGetPr(prhs(2)))
  call quadrature_from_matlab(QUADRATURE, prhs(3))
  call vector_MAT_CHAR_from_matlab(MAT_CHAR, prhs(4))
  call CC_from_matlab(CC_mat, mxGetPr(prhs(5)), MESH%tensors, size(MAT_CHAR))
  call vector_real_from_matlab(pfield, mxGetPr(prhs(6)), MESH%num_node)
  call real_from_matlab(c_w, mxGetPr(prhs(7)))
  call integer_from_matlab(order, mxGetPr(prhs(8)))

  !=================================================================

  call fracture_energy(MESH, t, QUADRATURE, MAT_CHAR, &
       CC_mat, pfield, c_w, order, &
       fract_en)

  ! OUTPUT OF THE RESULTS
  plhs(1) = mxCreateDoubleScalar(fract_en) !fracture energy

  return
end subroutine mexFunction
