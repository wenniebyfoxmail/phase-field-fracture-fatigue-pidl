! Copyright (C) 2022 ETH Zurich, SIS ID and CompMech D-MAVT
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

module system_factors

    use scalar_utils, only: H_p, dp
    use matrix_utils, only: m22inv, m33inv

    implicit none
    ! The `implicit none` statement works for all subroutines/functions in a module

    public BtB_detJ, NtN_GP

contains

    !---------------------------------------------------------------------------
    !      Purpose: Compute the global part of the dissipation density
    !      Inputs:
    !         dNdxi - Derivatives of the shape functions at the Gauss points
    !         el_coord - Coordinates of the nodes of the element
    !         dim - Physical dimension of the problem
    !         nel - Number of nodes per element
    !      Outputs:
    !         BtB - BtB factor (dNtdN)
    !         det_jac - Determinant of the jacobian 
    !---------------------------------------------------------------------------
  subroutine BtB_detJ(dNdxi, el_coord, dim, nel, sys_factor, det_jac)
    real(kind=dp), dimension(:, :), intent(in) :: dNdxi, el_coord
    integer, intent(in) :: dim, nel
    real(kind=dp), dimension(:, :), intent(out) :: sys_factor
    real(kind=dp), intent(out) :: det_jac

    real(kind=dp), dimension(:, :), allocatable :: jac, inv_jac, dN_glob
    logical ok_flag

    allocate (jac(dim, dim))
    allocate (inv_jac(dim, dim))
    allocate (dN_glob(dim, nel))

    jac = matmul(dNdxi, el_coord);
    if (dim == 2) then
       call m22inv(jac, inv_jac, det_jac, ok_flag)
    else if (dim == 3) then
       call m33inv(jac, inv_jac, det_jac, ok_flag)
    end if
    dN_glob = matmul(inv_jac, dNdxi);
    sys_factor = matmul(transpose(dN_glob), dN_glob);
  end subroutine BtB_detJ

    !---------------------------------------------------------------------------
    !      Purpose: Compute the local part of the dissipation density
    !      Inputs:
    !         Nxi - Shape functions at the Gauss points
    !         nel - Number of nodes per element
    !      Outputs:
    !         NtN - NtN factor (mass matrix)
    !---------------------------------------------------------------------------
  subroutine NtN_GP(Nxi, nel, sys_factor)
    real(kind=dp), dimension(:), intent(in) :: Nxi
    integer, intent(in) :: nel
    real(kind=dp), dimension(:, :), intent(out) :: sys_factor

    sys_factor = matmul(reshape(Nxi, (/nel, 1/)), reshape(Nxi, (/1, nel/)));
  end subroutine NtN_GP


end module
