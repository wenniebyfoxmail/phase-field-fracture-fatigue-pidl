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
! paraview_out(...
!     filename, n_nodes, n_elements,...
!     nnds, node, elements,...
!     elem_material_id,...
!     scalar_values, scalar_names,...
!     vector_values, vector_names,...
!     tensor_values, tensor_names...
! );
!======================================================================
! Purpose: Creates a vtk file to visualize: mesh data with optional label field together with scalar, vector and tensor fields.
!
! Inputs:
! filename            -->  MATLAB String with file name
! n_nodes             -->  MATLAB Scalar (Integer) representing the total number of nodes
! n_elements          -->  MATLAB Scalar (Integer) representing the total number of elements
! nnds                -->  MATLAB Scalar (Integer) representing the number of nodes per element
! node                -->  MATLAB Matrix representing the nodes coordinates
! elem                -->  MATLAB Matrix representing the assembly matrix
! elem_material_id (optional) -->  MATLAB Vector representing the elements' material types
! scalar_names        -->  MATLAB Cell, size n_scalars, containing the names of the scalars
! scalar_values       -->  MATLAB Matrix, shape [n_nodes, n_scalars]
! vector_names        -->  MATLAB Cell, size n_vectors, containing the names of the vectors
! vector_values       -->  MATLAB Tensor, shape [n_nodes, 2, n_vectors]
! tensor_names        -->  MATLAB Cell, size n_tensors, containing the names of the tensors
! tensor_values       -->  MATLAB Tensor, shape [n_nodes, 3, n_tensors] containing upper triangular entries (1,1), (2,2) and (1,2) of a symmetric tensor
!
! Outputs:
! No MATLAB outputs. The subroutine creates a vtk file at filename
!
!===============================================================================
!     Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use mod_paraview_out, only: paraview_out
  use mex_utils, only: matrix_real_from_matlab, matrix_integer_from_matlab,&
       integer_from_matlab, vector_integer_from_matlab, dyn_tensor_3_real_from_matlab,&
       dyn_matrix_real_from_matlab, cell_string_from_matlab
  use scalar_utils, only: dp

  implicit none

  !     mexFunction arguments:
  mwPointer plhs(*), prhs(*)
  integer nlhs, nrhs
  !     Function declarations:
  mwPointer mxGetPr
  integer mxGetString

  integer nnds, status, arg_idx
  integer n_nodes, n_elements
  integer n_scalars, n_vectors, n_tensors
  character (len=20), allocatable :: scalar_names(:), vector_names(:), tensor_names(:)
  integer dim, dim2, status_txt
  real(kind=dp), allocatable :: scalar_values(:, :), vector_values(:, :, :), tensor_values(:, :, :)
  integer, dimension(:), allocatable :: elements(:, :)
  integer, allocatable :: elem_material_id(:)
  real(kind=dp), dimension(:), allocatable :: node(:, :)
  character(len=256) :: filename

  !=================================================================
  !**********************************
  !     Check for proper number of arguments.
  if (nrhs .ne. 12 .and. nrhs .ne. 13) then
     call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', '12 or 13 input arguments required.')
  elseif (nlhs .ne. 0) then
     call mexErrMsgIdAndTxt('MATLAB:paraview_out:nOutput', '0 outputs required.')
     plhs(1) = plhs(1) ! Only to suppress warning about unused variable plhs
  end if

  arg_idx = 1
  status = mxGetString(prhs(arg_idx), filename, 256)
  arg_idx = arg_idx + 1
  call integer_from_matlab(n_nodes, mxGetPr(prhs(arg_idx)))
  arg_idx = arg_idx + 1
  call integer_from_matlab(n_elements, mxGetPr(prhs(arg_idx)))
  arg_idx = arg_idx + 1
  call integer_from_matlab(nnds, mxGetPr(prhs(arg_idx)))
  arg_idx = arg_idx + 1
  call matrix_real_from_matlab(node, mxGetPr(prhs(arg_idx)), n_nodes, 2)
  arg_idx = arg_idx + 1
  call matrix_integer_from_matlab(elements, mxGetPr(prhs(arg_idx)), n_elements, nnds)
  arg_idx = arg_idx + 1
  if (nrhs .eq. 13) then
     call vector_integer_from_matlab(elem_material_id, mxGetPr(prhs(arg_idx)), n_elements)
     arg_idx = arg_idx + 1
  end if
  call dyn_matrix_real_from_matlab(scalar_values, prhs(arg_idx+1), dim, n_scalars)
  if (n_scalars .gt. 0 .and. dim .ne. n_nodes) then
     call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', 'Dimension mismatch: scalar_values must have shape [n_nodes,:]')
  end if
  call cell_string_from_matlab(scalar_names, prhs(arg_idx), n_scalars, status_txt)
  arg_idx = arg_idx + 2
  call dyn_tensor_3_real_from_matlab(vector_values, prhs(arg_idx+1), dim, dim2, n_vectors)
  if (n_vectors .gt. 0) then
     if (dim .ne. n_nodes) then
        call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', 'Dimension mismatch: vector_values must have shape [n_nodes,:,:]')
     end if
     if (dim2 .ne. 2) then
        call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', 'Dimension mismatch: vector_values must have shape [:,2,:]')
     end if
  end if
  call cell_string_from_matlab(vector_names, prhs(arg_idx), n_vectors, status_txt)
  arg_idx = arg_idx + 2
  call dyn_tensor_3_real_from_matlab(tensor_values, prhs(arg_idx+1), dim, dim2, n_tensors)
  if (n_tensors .gt. 0) then
     if (dim .ne. n_nodes) then
        call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', 'Dimension mismatch: tensor_values must have shape [n_nodes,:,:]')
     end if
     if (dim2 .ne. 3) then
        call mexErrMsgIdAndTxt('MATLAB:paraview_out:nInput', 'Dimension mismatch: tensor_values must have shape [:,3,:]')
     end if
  end if
  call cell_string_from_matlab(tensor_names, prhs(arg_idx), n_tensors, status_txt)
  arg_idx = arg_idx + 2

  !=================================================================

  call paraview_out(&
       filename, n_nodes, n_elements, nnds, node, elements, elem_material_id, &
       n_scalars, scalar_values, scalar_names, &
       n_vectors, vector_values, vector_names, &
       n_tensors, tensor_values, tensor_names &
       )

  return
end subroutine mexFunction
!******************************************************************
