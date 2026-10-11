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
module scalar_utils

    implicit none

    ! The `implicit none` statement works for all subroutines/functions in a module

    ! machine-compiler-independent real numbers precision specifiers (`real(kind=...)`)
    integer, parameter, public :: sp = selected_real_kind(6, 37)  ! single, 32-bit
    integer, parameter, public :: dp = selected_real_kind(15, 307)  ! double, 64-bit

    public H_p, H_n, freddi_factor

contains

    !---------------------------------------------------------------------------
    ! Positive Heaviside function for a scalar
    !---------------------------------------------------------------------------
    function H_p(a) result(b)
        real(kind=dp), intent(in) :: a
        real(kind=dp) :: b

        b = 0.5*(a + abs(a))
    end function

    !---------------------------------------------------------------------------
    ! Negative Heaviside function for a scalar
    !---------------------------------------------------------------------------
    function H_n(a) result(b)
        real(kind=dp), intent(in) :: a
        real(kind=dp) :: b

        b = 0.5*(a - abs(a))
    end function

    !---------------------------------------------------------------------------
    ! Freddi coefficient alpha corresponding to stress_state and ni
    !---------------------------------------------------------------------------
    function freddi_factor(stress_state, ni) result(alpha)
        integer, intent(in) :: stress_state
        real(kind=dp), intent(in) :: ni
        real(kind=dp) :: alpha

        if (stress_state == 1) then !PLAIN STRAIN
            alpha = ni/(1 - 2*ni);
        else                     !PLAIN STRESS
            alpha = ni/(1 - ni);
        end if
    end function

end module scalar_utils
