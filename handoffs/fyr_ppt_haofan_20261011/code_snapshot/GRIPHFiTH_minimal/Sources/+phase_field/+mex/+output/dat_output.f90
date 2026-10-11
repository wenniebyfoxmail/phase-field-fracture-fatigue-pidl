! Copyright (C) 2023 ETH Zurich, SIS ID and CompMech D-MAVT
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
! dat_output(...
!     index_columns, index_column_header, columns, column_header, filename...
! );
!======================================================================
! Purpose: Output a text file (path: `filename`) with integer columns
! `index_columns` and numeric columns `columns`.
!
! Inputs:
! index_columns       --> MATLAB integers, 2d array (row,col)
! index_column_header --> MATLAB cell of captions for the integer columns
! columns             --> MATLAB reals, 2d array (row,col)
! column_header       --> MATLAB cell of captions for the columns
! filename            --> MATLAB String with file name
! Outputs:
! No MATLAB outputs.
!
!===============================================================================
!   Gateway routine
subroutine mexFunction(nlhs, plhs, nrhs, prhs)

  use mod_dat_output, only: dat_output
  use mex_utils, only: dyn_matrix_integer_from_matlab, dyn_matrix_real_from_matlab, cell_string_from_matlab
  use scalar_utils, only: dp

  implicit none

  !   mexFunction arguments:
  mwPointer plhs(*), prhs(*)
  integer nlhs, nrhs
  !   Function declarations:
  integer mxGetString

  integer :: n_index_cols, n_cols, n_rows, tmp
  character (len=20), allocatable :: index_column_header(:), column_header(:)
  integer, allocatable :: index_columns(:,:)
  real(kind=dp), allocatable :: columns(:,:)
  integer status_txt
  character (len=256) filename

  !=================================================================
  !**********************************
  !   Check for proper number of arguments.
  if (nrhs .ne. 5) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nInput', '5 inputs required.')
  elseif (nlhs .ne. 0) then
     call mexErrMsgIdAndTxt('MATLAB:matsq:nOutput', '0 outputs required.')
     plhs(1) = plhs(1)  ! Only to suppress warning about unused variable plhs
  end if

  call dyn_matrix_integer_from_matlab(index_columns, prhs(1), n_rows, n_index_cols)
  call cell_string_from_matlab(index_column_header, prhs(2), n_index_cols, status_txt)

  if (status_txt .ne. 0) then
     call mexErrMsgIdAndTxt('MATLAB:dat_output', 'index_columns and index_column_header must have same number of cols')
  end if

  call dyn_matrix_real_from_matlab(columns, prhs(3), tmp, n_cols)

  if (tmp .ne. n_rows) then
     call mexErrMsgIdAndTxt('MATLAB:dat_output', 'columns and index_columns must have same number of rows')
  end if

  call cell_string_from_matlab(column_header, prhs(4), n_cols, status_txt)

  if (status_txt .ne. 0) then
     call mexErrMsgIdAndTxt('MATLAB:dat_output', 'columns and column_header must have same number of cols')
  end if

  status_txt = mxGetString(prhs(5), filename, 256)

  call dat_output(index_columns, index_column_header, n_index_cols, columns, column_header, n_cols, n_rows, filename)
  return
end subroutine mexFunction
