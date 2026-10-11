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

module mod_dat_output
  public dat_output
contains
  !===============================================================================
  ! Purpose: Output a text file (path: `filename`) with integer columns
  ! `index_columns` and numeric columns `columns`. If file does not exist, write
  ! a header and write data. Otherwise only append data.
  !
  ! Inputs:
  ! index_columns       --> Integer values, 2d array (row,col)
  ! index_column_header --> Captions for the integer columns
  ! n_index_cols        --> 2nd Dimension of index_columns
  ! columns             --> Numeric values, 2d array (row,col)
  ! column_header       --> Captions for the columns
  ! n_cols              --> 2nd Dimension of columns
  ! n_rows              --> 1nd Dimension of index_columns, columns
  ! filename            --> Output path
  !
  !===============================================================================
  subroutine dat_output(index_columns, index_column_header, n_index_cols, columns, column_header, n_cols, n_rows, filename)

    use scalar_utils, only: dp

    implicit none

    integer, intent(in) :: n_index_cols, n_cols, n_rows
    integer, intent(in) :: index_columns(:,:)
    real(kind=dp), intent(in) :: columns(:,:)
    character (len=20), intent(in) :: index_column_header(:), column_header(:)
    character (len=256), intent(in) :: filename

    logical :: file_exists
    integer status
    integer i, j

    inquire (file=filename, exist=file_exists, iostat=status)

    open (unit=20, file=filename, access='sequential', position='append')

    ! header
    if (.not. file_exists) then
       do j = 1, n_index_cols
          write (unit=20, fmt=917, advance='no') trim(index_column_header(j))
          if (j .ne. n_index_cols) then
             write (unit=20, fmt=920, advance='no') ' '
          end if
       end do
       if (n_cols .ne. 0) then
          write (unit=20, fmt=920, advance='no') ' '
       end if
       do j = 1, n_cols
          write (unit=20, fmt=917, advance='no') trim(column_header(j))
          if (j .ne. n_cols) then
             write (unit=20, fmt=920, advance='no') ' '
          end if
       end do
       write (unit=20, fmt=920, advance='yes')
    end if

    ! data
    do i = 1, n_rows
       do j = 1, n_index_cols
          write (unit=20, fmt=918, advance='no') index_columns(i, j)
          if (j .ne. n_index_cols) then
             write (unit=20, fmt=920, advance='no') ' '
          end if
       end do
       if (n_cols .ne. 0) then
          write (unit=20, fmt=920, advance='no') ' '
       end if
       do j = 1, n_cols
          write (unit=20, fmt=919, advance='no') columns(i, j)
          if (j .ne. n_cols) then
             write (unit=20, fmt=920, advance='no') ' '
          end if
       end do
       write (unit=20, fmt=917, advance='yes')
    end do

    close (unit=20)

917 format(A15)
918 format(I15)
919 format(8E15.6E3)
920 format(A1)

    return
  end subroutine dat_output
endmodule mod_dat_output
