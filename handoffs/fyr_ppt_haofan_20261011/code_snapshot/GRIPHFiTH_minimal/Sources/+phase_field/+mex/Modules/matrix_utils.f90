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
module matrix_utils

    use scalar_utils, only: dp

    implicit none

    ! The `implicit none` statement works for all subroutines/functions in a module
    private
    public diasym, m22inv, m33inv, minv

contains

    !---------------------------------------------------------------------------
    ! DIASYM - Wrapper for the LAPACK diagonalization subroutine DSYEV
    !
    ! Inputs:
    !   - a(n,n) = real symmetric matrix to be diagonalized
    !   - n      = size of a
    !
    ! Outputs:
    !   - a(n,n) = orthonormal eigenvectors of input a
    !   - eig(n) = eigenvalues of a in ascending order
    !---------------------------------------------------------------------------
    subroutine diasym(a, eig, n)
        integer, intent(in) :: n
        real(kind=dp), intent(inout) :: a(n, n)
        real(kind=dp), intent(out) :: eig(n)

        integer :: l, inf
        real(kind=dp) :: work(n*(3 + n/2))

        l = n*(3 + n/2)
        call dsyev('V', 'U', n, a, n, eig, work, l, inf)
    end subroutine

    !---------------------------------------------------------------------------
    !  M22INV  - Compute the inverse of a 2x2 matrix.
    !
    !  a       = (input) 2x2 matrix to be inverted
    !  ainv    = (output) 2x2 inverse of matrix a
    !  ok_flag = (output) .true. if the input matrix could be inverted, and
    !            .false. if the input matrix is singular.
    !  det     = (output) determinant of the matrix
    !---------------------------------------------------------------------------
    subroutine m22inv(a, ainv, det, ok_flag)
        real(kind=dp), intent(in)  :: a(2, 2)
        real(kind=dp), intent(out) :: ainv(2, 2)
        real(kind=dp), intent(out) :: det
        logical, intent(out) :: ok_flag

        real(kind=dp), parameter :: eps = 1.0d-10
        real(kind=dp) :: cofactor(2, 2)

        det = a(1, 1)*a(2, 2) - a(1, 2)*a(2, 1)

        if (abs(det) .le. eps) then
            ainv = 0.0d0
            ok_flag = .false.
            return
        end if

        cofactor(1, 1) = +a(2, 2)
        cofactor(1, 2) = -a(2, 1)
        cofactor(2, 1) = -a(1, 2)
        cofactor(2, 2) = +a(1, 1)

        ainv = transpose(cofactor)/det

        ok_flag = .true.
    end subroutine

    !---------------------------------------------------------------------------
    !  M33INV  - Compute the inverse of a 3x3 matrix.
    !
    !  a       = (input) 3x3 matrix to be inverted
    !  ainv    = (output) 3x3 inverse of matrix a
    !  ok_flag = (output) .true. if the input matrix could be inverted, and
    !            .false. if the input matrix is singular.
    !  det     = (output) determinant of the matrix
    !---------------------------------------------------------------------------
    subroutine m33inv(a, ainv, det, ok_flag)

        real(kind=dp), intent(in)  :: a(3, 3)
        real(kind=dp), intent(out) :: ainv(3, 3)
        real(kind=dp), intent(out) :: det
        logical, intent(out) :: ok_flag

        real(kind=dp), parameter :: eps = 1.0d-10
        real(kind=dp) :: cofactor(3, 3)

        det = a(1, 1)*a(2, 2)*a(3, 3) &
              - a(1, 1)*a(2, 3)*a(3, 2) &
              - a(1, 2)*a(2, 1)*a(3, 3) &
              + a(1, 2)*a(2, 3)*a(3, 1) &
              + a(1, 3)*a(2, 1)*a(3, 2) &
              - a(1, 3)*a(2, 2)*a(3, 1)

        if (abs(det) .le. eps) then
            ainv = 0.0d0
            ok_flag = .false.
            return
        end if

        cofactor(1, 1) = +(a(2, 2)*a(3, 3) - a(2, 3)*a(3, 2))
        cofactor(1, 2) = -(a(2, 1)*a(3, 3) - a(2, 3)*a(3, 1))
        cofactor(1, 3) = +(a(2, 1)*a(3, 2) - a(2, 2)*a(3, 1))
        cofactor(2, 1) = -(a(1, 2)*a(3, 3) - a(1, 3)*a(3, 2))
        cofactor(2, 2) = +(a(1, 1)*a(3, 3) - a(1, 3)*a(3, 1))
        cofactor(2, 3) = -(a(1, 1)*a(3, 2) - a(1, 2)*a(3, 1))
        cofactor(3, 1) = +(a(1, 2)*a(2, 3) - a(1, 3)*a(2, 2))
        cofactor(3, 2) = -(a(1, 1)*a(2, 3) - a(1, 3)*a(2, 1))
        cofactor(3, 3) = +(a(1, 1)*a(2, 2) - a(1, 2)*a(2, 1))

        ainv = transpose(cofactor)/det

        ok_flag = .true.
    end subroutine

    !---------------------------------------------------------------------------
    ! INV - Calculate inverse of a matrix by finding the LU decomposition.
    !       Depends on LAPACK.
    !
    ! Inputs:
    !   - A = Square matrix to be inverted
    !   - n = Size of the matrix
    !
    ! Outputs:
    !   - Ainv = Inverse of the matrix
    !---------------------------------------------------------------------------
    subroutine minv(A, n, Ainv)
        integer, intent(in) :: n
        real(kind=dp), intent(in) :: A(n, n)
        real(kind=dp), intent(out) :: Ainv(n, n)

        integer :: info
        real(kind=dp) :: work(n)  ! work array for LAPACK
        integer :: ipiv(n)   ! pivot indices

        ! External procedures defined in LAPACK
        external DGETRF
        external DGETRI

        ! Store A in Ainv to prevent it from being overwritten by LAPACK
        Ainv = A

        ! DGETRF computes an LU factorization of a general M-by-N matrix A
        ! using partial pivoting with row interchanges.
        call DGETRF(n, n, Ainv, n, ipiv, info)

        if (info /= 0) then
            stop 'Matrix is numerically singular!'
        end if

        ! DGETRI computes the inverse of a matrix using the LU factorization
        ! computed by DGETRF.
        call DGETRI(n, Ainv, n, ipiv, work, n, info)

        if (info /= 0) then
            stop 'Matrix inversion failed!'
        end if
    end subroutine

end module
