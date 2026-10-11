! Copyright (C) 2022-2023 ETH Zurich, SIS ID and CompMech D-MAVT
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

module mod_paraview_out
  public paraview_out
contains
  !===============================================================================
  ! Purpose: ...
  !
  ! Inputs:
  ! ...
  !
  ! Outputs:
  ! ...
  !===============================================================================
  subroutine paraview_out(&
       filename, n_nodes, n_elements, nnds, node, elements, label, &
       n_scalars, scalar_values, scalar_names, &
       n_vectors, vector_values, vector_names, &
       n_tensors, tensor_values, tensor_names &
       )

    use scalar_utils, only: dp

    implicit none

    character(len=256), intent(in) :: filename
    integer, intent(in) :: n_nodes, n_elements
    integer, intent(in) :: nnds
    real(kind=dp), intent(in) :: node(:, :)
    integer, intent(in) :: elements(:, :)
    integer, intent(in), optional :: label(:)
    integer, intent(in) :: n_scalars, n_vectors, n_tensors
    character (len=20), intent(in) :: scalar_names(:), vector_names(:), tensor_names(:)
    real(kind=dp), intent(in) :: scalar_values(:, :), vector_values(:, :, :), tensor_values(:, :, :)
    

    integer cnt, i, j

    !=================================================================

    !****************   ParaView Post-Processing   ********************
    open (unit=20, file=filename, access='sequential')

    write (20, 910) '# vtk DataFile Version 3.0'
    write (20, 910) 'Solution'
    write (20, 910) 'ASCII'
    
    !------ Mesh data
    write (20, 910) 'DATASET UNSTRUCTURED_GRID'
    write (20, 911) 'POINTS ', n_nodes, ' float'

    cnt = 1;
    do i = 1, n_nodes
       write (20, *) node(i, 1), node(i, 2), 0.0d0
    end do

    write (20, 913) 'CELLS ', n_elements, n_elements*(nnds + 1)
    do i = 1, n_elements
       write (unit=20, fmt=918, advance='no') nnds
       do j = 1, nnds
          write (unit=20, fmt=918, advance='no') elements(i, j) - 1
       end do
       write (unit=20, fmt=910, advance='yes')
    end do

    write (20, 914) 'CELL_TYPES ', n_elements
    do i = 1, n_elements
       write (20, *) 9
    end do

    if (present(label)) then
       write (20, 914) 'CELL_DATA ', n_elements
       write (20, 910) 'SCALARS MAT_ID int 1'
       write (20, 910) 'LOOKUP_TABLE default'
       do i = 1, n_elements
          write (20, 917) label(i)
       end do
    end if

    !------ fields
    write (20, 914) 'POINT_DATA ', n_nodes

    do i = 1, n_scalars
       write (20, 919) 'SCALARS ', trim(scalar_names(i)),' float 1'
       write (20, 910) 'LOOKUP_TABLE default'
       do j = 1, n_nodes
          write (20, 916) scalar_values(j, i)
       end do
    end do

    do i = 1, n_vectors
       write (20, 919) 'VECTORS ', trim(vector_names(i)),' float'
       do j = 1, n_nodes
          write (20, 912) vector_values(j, 1, i), vector_values(j, 2, i), 0.d0
       end do
    end do

    do i = 1, n_tensors
       write (20, 919) 'TENSORS ', trim(tensor_names(i)),' float'
       do j = 1, n_nodes
          write (20, *) tensor_values(j, 1, i), tensor_values(j, 3, i), 0.d0
          write (20, *) tensor_values(j, 3, i), tensor_values(j, 2, i), 0.d0
          write (20, *) 0.0d0, 0.0d0, 0.0d0
          write (20, *)
       end do
    end do

    close (unit=20)

910 format(A)
911 format(A, I8, A)
912 format(F30.15, F30.15, F30.15)
913 format(A, I8, ' ', I8)
914 format(A, I8)
916 format(F30.15)
917 format(I3)
918 format(I21)
919 format(3A)

    return
  end subroutine paraview_out
endmodule mod_paraview_out
