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
module array_utils

    use scalar_utils, only: dp

    implicit none
    ! The `implicit none` statement works for all subroutines/functions in a module

    private
    public distance2d, mean, int_zeros, zeros

contains

    !---------------------------------------------------------------------------
    ! Distance between two 2D points
    !---------------------------------------------------------------------------
    function distance2d(pt_2, pt_1) result(d)
        real(kind=dp), intent(in) :: pt_1(2), pt_2(2)
        real(kind=dp) :: d

        d = sqrt(((pt_1(1) - pt_2(1))**2) + ((pt_1(2) - pt_2(2))**2))
    end function

    !---------------------------------------------------------------------------
    ! Mean value of array elements
    !---------------------------------------------------------------------------
    function mean(a, n) result(m)
        integer, intent(in) :: n
        real(kind=dp), intent(in) :: a(n)
        real(kind=dp) :: m

        integer :: i

        m = 0.0
        do i = 1, n
            m = m + a(i)
        end do
        m = m/n
    end function

    !---------------------------------------------------------------------------
    !      Purpose: Zero-out integer array of data
    !      Inputs:
    !         v(n) - Integer array
    !         n    - Length of array
    !      Outputs:
    !         v(*) - Integer array with zero values
    !---------------------------------------------------------------------------
    subroutine int_zeros(v, n)
        integer, intent(in) :: n
        integer, intent(inout) :: v(n)

        integer :: i

        save

        do i = 1, n
            v(i) = 0
        end do
    end subroutine

    !---------------------------------------------------------------------------
    !      Purpose: Zero-out real array of data
    !      Inputs:
    !         v(n) - Real array
    !         n    - Length of array
    !      Outputs:
    !         v(n) - Real array with zero values
    !---------------------------------------------------------------------------
    subroutine zeros(v, n)
        integer, intent(in) :: n
        real(kind=dp), intent(inout) :: v(n)

        integer:: i

        save

        do i = 1, n
            v(i) = 0.0d0
        end do
    end subroutine

end module
