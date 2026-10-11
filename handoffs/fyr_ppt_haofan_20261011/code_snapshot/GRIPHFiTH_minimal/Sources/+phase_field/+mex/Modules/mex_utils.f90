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
module mex_utils

    use scalar_utils, only: dp
    use types, only: MAT_CHAR_t, DOF_t, MESH_t, QUADRATURE_t, BOUNDARY_CONDS_t

    implicit none
    ! The `implicit none` statement works for all subroutines/functions in a module

    private get_field_pr, numel_struct_field
    private cp_struct_field_real, cp_struct_field_vector_real,&
         cp_struct_field_array3d_real, cp_struct_field_matrix_real
    public cp_struct_field_matrix_real_alloc
    private cp_struct_field_integer, cp_struct_field_vector_integer,&
            cp_struct_field_matrix_integer
    public CC_from_matlab, vector_MAT_CHAR_from_matlab
    public real_from_matlab, vector_real_from_matlab, matrix_real_from_matlab
    public integer_from_matlab, vector_integer_from_matlab, matrix_integer_from_matlab
    public dyn_matrix_integer_from_matlab, dyn_matrix_real_from_matlab
    public dyn_tensor_3_real_from_matlab, tensor_3_real_from_matlab
    public cell_string_from_matlab
    public mex_double_array_3
contains

    !---------------------------------------------------------------------------
    ! Get struct field pointer
    !---------------------------------------------------------------------------
    function get_field_pr(struct_pr, fieldname, struct_idx) result(field_pr)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwIndex, intent(in), optional :: struct_idx
        mwPointer :: field_pr  ! intent(out)

        mwIndex :: idx
        mwPointer :: mxGetField

        if (present(struct_idx)) then
            idx = struct_idx
        else
            idx = 1  ! default: a single structure
        end if

        field_pr = mxGetField(struct_pr, idx, fieldname)
    end function

    !---------------------------------------------------------------------------
    ! Number of elements in a struct field
    !---------------------------------------------------------------------------
    function numel_struct_field(struct_pr, fieldname, struct_idx) result(n)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwIndex, intent(in), optional :: struct_idx
        mwPointer :: n

        mwPointer :: field_pr
        mwPointer :: mxGetNumberOfElements

        field_pr = get_field_pr(struct_pr, fieldname, struct_idx)
        n = mxGetNumberOfElements(field_pr)
    end function


    !---------------------------------------------------------------------------
    ! Copy real-valued struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_real(struct_pr, fieldname, out_val, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        real(kind=dp), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp), dimension(1) :: tmp
        call cp_struct_field_vector_real(struct_pr, fieldname, tmp, 1, struct_idx)
        out_val = tmp(1)
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy real-valued vector struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_vector_real(struct_pr, fieldname, out_val, n, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwSize, intent(in) :: n
        real(kind=dp), dimension(n), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        mwPointer :: field_pr
        mwPointer :: mxGetPr

        field_pr = get_field_pr(struct_pr, fieldname, struct_idx)
        call mxCopyPtrToReal8(mxGetPr(field_pr), out_val, n)
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy real-valued matrix struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_matrix_real(struct_pr, fieldname, out_val, n, m, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwSize, intent(in) :: n, m
        real(kind=dp), dimension(n, m), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp), dimension(n * m) :: tmp
        call cp_struct_field_vector_real(struct_pr, fieldname, tmp, n * m, struct_idx)
        out_val = reshape(tmp, (/n, m/))
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy real-valued matrix struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_matrix_real_alloc(struct_pr, fieldname, out_val, n, m, struct_idx)
      mwPointer, intent(in) :: struct_pr
      character(len=*), intent(in) :: fieldname
      mwSize, intent(in) :: n, m
      real(kind=dp), dimension(:, :), intent(out), allocatable :: out_val
      mwIndex, intent(in), optional :: struct_idx
      allocate (out_val(n, m))
      call cp_struct_field_matrix_real(struct_pr, fieldname, out_val, n, m, struct_idx)
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy real-valued 3D array struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_array3d_real(struct_pr, fieldname, out_val, i, j, k, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwSize, intent(in) :: i, j, k
        real(kind=dp), dimension(i, j, k), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp), dimension(i * j * k) :: tmp
        call cp_struct_field_vector_real(struct_pr, fieldname, tmp, i * j * k, struct_idx)
        out_val = reshape(tmp, (/i, j, k/))
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy integer-valued struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_integer(struct_pr, fieldname, out_val, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        integer, intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp) :: tmp

        call cp_struct_field_real(struct_pr, fieldname, tmp, struct_idx)
        out_val = int(tmp)
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy integer-valued vector struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_vector_integer(struct_pr, fieldname, out_val, n, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwSize, intent(in) :: n
        integer, dimension(n), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp), dimension(n) :: tmp

        call cp_struct_field_vector_real(struct_pr, fieldname, tmp, n, struct_idx)
        out_val = int(tmp)
    end subroutine

    !---------------------------------------------------------------------------
    ! Copy integer-valued matrix struct field.
    !---------------------------------------------------------------------------
    subroutine cp_struct_field_matrix_integer(struct_pr, fieldname, out_val, n, m, struct_idx)
        mwPointer, intent(in) :: struct_pr
        character(len=*), intent(in) :: fieldname
        mwSize, intent(in) :: n, m
        integer, dimension(n, m), intent(out) :: out_val
        mwIndex, intent(in), optional :: struct_idx

        real(kind=dp), dimension(n, m) :: tmp

        call cp_struct_field_matrix_real(struct_pr, fieldname, tmp, n, m, struct_idx)
        out_val = int(tmp)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse MAT_CHAR struct as returned by
    ! `phase_field.init.material_characteristic` MATLAB function.
    !---------------------------------------------------------------------------
    subroutine mat_char_from_matlab(mat_char, struct_pr, struct_idx)
        class(MAT_CHAR_t), intent(inout) :: mat_char
        mwPointer, intent(in) :: struct_pr
        mwIndex, intent(in) :: struct_idx

        call cp_struct_field_real(struct_pr, "E", mat_char%E, struct_idx)
        call cp_struct_field_real(struct_pr, "ni", mat_char%ni, struct_idx)
        call cp_struct_field_real(struct_pr, "G", mat_char%G, struct_idx)
        call cp_struct_field_real(struct_pr, "K", mat_char%K, struct_idx)
        call cp_struct_field_real(struct_pr, "lambda", mat_char%lambda, struct_idx)
        call cp_struct_field_real(struct_pr, "Gc", mat_char%Gc, struct_idx)
        call cp_struct_field_real(struct_pr, "ell", mat_char%ell, struct_idx)
        call cp_struct_field_real(struct_pr, "res_stiff", mat_char%res_stiff, struct_idx)
        call cp_struct_field_real(struct_pr, "alpha_T", mat_char%alpha_T, struct_idx)
        call cp_struct_field_real(struct_pr, "p", mat_char%p, struct_idx)
        call cp_struct_field_real(struct_pr, "penalty_irrev", mat_char%penalty_irrev, struct_idx)
        call cp_struct_field_real(struct_pr, "penalty_recov", mat_char%penalty_recov, struct_idx)
        call cp_struct_field_real(struct_pr, "traction_p", mat_char%traction_p, struct_idx)
        call cp_struct_field_real(struct_pr, "a1", mat_char%a1, struct_idx)
        call cp_struct_field_real(struct_pr, "a2", mat_char%a2, struct_idx)
        call cp_struct_field_real(struct_pr, "a3", mat_char%a3, struct_idx)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse MESH struct as returned by `phase_field.init.mesh` MATLAB
    ! function.
    !---------------------------------------------------------------------------
    subroutine mesh_from_matlab(mesh, struct_pr)
        class(MESH_t), intent(inout) :: mesh
        mwPointer, intent(in) :: struct_pr

        call cp_struct_field_integer(struct_pr, "num_node", mesh%num_node)
        call cp_struct_field_integer(struct_pr, "num_elem", mesh%num_elem)
        call cp_struct_field_integer(struct_pr, "nel", mesh%nel)
        call cp_struct_field_integer(struct_pr, "nel_tract", mesh%nel_tract)
        call cp_struct_field_integer(struct_pr, "dim", mesh%dim)
        call cp_struct_field_integer(struct_pr, "tensors", mesh%tensors)

        call cp_struct_field_matrix_real_alloc(struct_pr, "node", mesh%node, mesh%num_node, mesh%dim)

        allocate (mesh%elem(mesh%num_elem, mesh%nel))
        call cp_struct_field_matrix_integer(struct_pr, "elem", mesh%elem, mesh%num_elem, mesh%nel)
        allocate (mesh%elem_material_id(mesh%num_elem))
        call cp_struct_field_vector_integer(struct_pr, "elem_material_id", mesh%elem_material_id, mesh%num_elem, 1)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse DOF struct as returned by `phase_field.init.dofs` MATLAB
    ! function.
    !---------------------------------------------------------------------------
    subroutine dof_from_matlab(dof, struct_pr)
        class(DOF_t), intent(inout) :: dof
        mwPointer, intent(in) :: struct_pr

        call cp_struct_field_integer(struct_pr, "num_dof_node", dof%num_dof_node)
        call cp_struct_field_integer(struct_pr, "num_dof", dof%num_dof)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse the dimensions of a matlab array returning size(arr, dim_idx) and
    ! asserting that the other dimensions are equal to other_dims.
    ! Example:
    ! For an array of shape (2,3,4), this function will return 3 for a call with
    ! dim_idx=2, other_dims=(/2, 4/) (it would raise an error for
    ! other_dims=(/2, 5/))
    !---------------------------------------------------------------------------
    function tensor_unpack_shape(v_pr, dim_idx, other_dims) result(dim)
      mwPointer, intent(in) :: v_pr
      integer, intent(in) :: dim_idx, other_dims(:)
      integer :: dims(3), dim, i
      call tensor_shape(v_pr, dims, size(other_dims) + 1)
      do i = 1, size(other_dims)
         if (&
              (i .lt. dim_idx .and. dims(i) .ne. other_dims(i)) &
              .or. (i .ge. dim_idx .and. dims(i+1) .ne. other_dims(i))&
              ) then
            call mexErrMsgIdAndTxt('MATLAB:matrix_unpack_shape:nInput', &
                 'Dimension mismatch')
         end if
      end do
      dim = dims(dim_idx)
    end function tensor_unpack_shape
    
    !---------------------------------------------------------------------------
    ! Parse QUADRATURE struct as returned by `phase_field.init.quadrature`
    ! MATLAB function.
    !---------------------------------------------------------------------------
    subroutine quadrature_from_matlab(quadrature, struct_pr)
        class(QUADRATURE_t), intent(inout) :: quadrature
        mwPointer, intent(in) :: struct_pr
        integer :: dim, nel, nel_tract

        call cp_struct_field_integer(struct_pr, "order", quadrature%order)
        call cp_struct_field_integer(struct_pr, "num_gauss_pts", quadrature%num_gauss_pts)

        dim = tensor_unpack_shape(get_field_pr(struct_pr, "gauss_pts", 1), 2, &
             (/ quadrature%num_gauss_pts /))
        call cp_struct_field_matrix_real_alloc(&
            struct_pr, "gauss_pts", quadrature%gauss_pts, quadrature%num_gauss_pts, dim)
        allocate (quadrature%gauss_W(quadrature%num_gauss_pts))
        call cp_struct_field_vector_real(&
            struct_pr, "gauss_W", quadrature%gauss_W, quadrature%num_gauss_pts)

        nel = tensor_unpack_shape(get_field_pr(struct_pr, "dNdxi", 1), 2, (/ dim, quadrature%num_gauss_pts /))
        allocate (quadrature%dNdxi(dim, nel, quadrature%num_gauss_pts))
        call cp_struct_field_array3d_real(&
            struct_pr, "dNdxi", quadrature%dNdxi, dim, nel, quadrature%num_gauss_pts)
        call cp_struct_field_matrix_real_alloc(&
            struct_pr, "Nxi", quadrature%Nxi, nel, quadrature%num_gauss_pts)

        quadrature%num_gauss_pts_tract = quadrature%order * (dim - 1)

        call cp_struct_field_matrix_real_alloc(&
            struct_pr, "gauss_pts_tract", quadrature%gauss_pts_tract, quadrature%num_gauss_pts_tract, dim - 1)
        allocate (quadrature%gauss_W_tract(quadrature%num_gauss_pts_tract))
        call cp_struct_field_vector_real(&
            struct_pr, "gauss_W_tract", quadrature%gauss_W_tract, quadrature%num_gauss_pts_tract)
        ! dNdxi_tract has shape (1, nel_tract, quadrature%num_gauss_pts_tract):
        nel_tract = tensor_unpack_shape(get_field_pr(struct_pr, "dNdxi_tract", 1), 2, &
             (/ 1, quadrature%num_gauss_pts_tract /))
        call cp_struct_field_matrix_real_alloc(&
            struct_pr, "dNdxi_tract", quadrature%dNdxi_tract, nel_tract, quadrature%num_gauss_pts_tract)
        call cp_struct_field_matrix_real_alloc(&
            struct_pr, "Nxi_tract", quadrature%Nxi_tract, nel_tract, quadrature%num_gauss_pts_tract)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse BOUNDARY_CONDS struct as returned by
    ! `phase_field.init.boundary_conditions` MATLAB function.
    !---------------------------------------------------------------------------
    subroutine boundary_conds_from_matlab(boundary_conds, struct_pr, num_elem, nel)
        class(BOUNDARY_CONDS_t), intent(inout) :: boundary_conds
        mwPointer, intent(in) :: struct_pr
        integer, intent(in) ::  num_elem, nel

        boundary_conds%num_conn_tract = numel_struct_field(struct_pr, "conn_tract")
        allocate (boundary_conds%conn_tract(boundary_conds%num_conn_tract))
        call cp_struct_field_vector_integer(&
            struct_pr, "conn_tract", boundary_conds%conn_tract, boundary_conds%num_conn_tract)
        allocate (boundary_conds%flag_tract(num_elem))
        call cp_struct_field_vector_integer(&
            struct_pr, "flag_tract", boundary_conds%flag_tract, num_elem)
        allocate (boundary_conds%tract_face(num_elem, nel))
        call cp_struct_field_matrix_integer(&
            struct_pr, "tract_face", boundary_conds%tract_face, num_elem, nel)
        boundary_conds%num_elem_tract = numel_struct_field(struct_pr, "elem_tract")
        allocate (boundary_conds%elem_tract(boundary_conds%num_elem_tract))
        call cp_struct_field_vector_integer(&
            struct_pr, "elem_tract", boundary_conds%elem_tract, boundary_conds%num_elem_tract)
        boundary_conds%num_non_hom_dirichlet_bc = numel_struct_field(struct_pr, "non_hom_dirichlet_bc")
        allocate (boundary_conds%non_hom_dirichlet_bc(boundary_conds%num_non_hom_dirichlet_bc))
        call cp_struct_field_vector_integer(&
            struct_pr, "non_hom_dirichlet_bc", boundary_conds%non_hom_dirichlet_bc, boundary_conds%num_non_hom_dirichlet_bc)
        boundary_conds%num_dirichlet_bc_pf = numel_struct_field(struct_pr, "dirichlet_bc_pf")
        allocate (boundary_conds%dirichlet_bc_pf(boundary_conds%num_dirichlet_bc_pf))
        call cp_struct_field_vector_integer(&
            struct_pr, "dirichlet_bc_pf", boundary_conds%dirichlet_bc_pf, boundary_conds%num_dirichlet_bc_pf)

        call cp_struct_field_real(struct_pr, "tx_final", boundary_conds%tx_final)
        call cp_struct_field_real(struct_pr, "ty_final", boundary_conds%ty_final)
        call cp_struct_field_real(struct_pr, "tx_increment", boundary_conds%tx_increment)
        call cp_struct_field_real(struct_pr, "ty_increment", boundary_conds%ty_increment)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse CC matrix as returned by
    ! `phase_field.init.elastic_stiffness_matrix` MATLAB function.
    !---------------------------------------------------------------------------
    subroutine CC_from_matlab(CC, mat_pr, tensors, num_materials)
        real(kind=dp), dimension(:, :, :), allocatable, intent(inout) :: CC
        mwPointer, intent(in) :: mat_pr
        integer, intent(in) :: tensors, num_materials

        allocate (CC(tensors, tensors, num_materials))
        call mxCopyPtrToReal8(mat_pr, CC, tensors * tensors * num_materials)
    end subroutine

    !--------------------------------------------------------------------------
    ! Parse an array of MAT_CHAR structs
    !--------------------------------------------------------------------------
    subroutine vector_MAT_CHAR_from_matlab(MAT_CHAR, mat_pr)
        type(MAT_CHAR_t), dimension(:), allocatable, intent(out) :: MAT_CHAR
        mwPointer, intent(in) :: mat_pr
        mwPointer :: mxGetNumberOfElements
        integer :: num_materials

        integer i

        num_materials = mxGetNumberOfElements(mat_pr)
        allocate (MAT_CHAR(num_materials))
        do i = 1, num_materials
           call mat_char_from_matlab(MAT_CHAR(i), mat_pr, i)
        end do
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse real value from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine real_from_matlab(v, v_pr)
        real(kind=dp), intent(inout) :: v
        mwPointer, intent(in) :: v_pr

        real(kind=dp) :: tmp(1)

        call mxCopyPtrToReal8(v_pr, tmp, 1)
        v = tmp(1)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse real-valued vector from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine vector_real_from_matlab(v, v_pr, n)
        real(kind=dp), dimension(:), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n

        allocate (v(n))
        call mxCopyPtrToReal8(v_pr, v, n)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse real-valued matrix from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine matrix_real_from_matlab(v, v_pr, n, m)
        real(kind=dp), dimension(:, :), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n, m

        allocate (v(n, m))
        call mxCopyPtrToReal8(v_pr, v, n * m)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse integer value from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine integer_from_matlab(v, v_pr)
        integer, intent(inout) :: v
        mwPointer, intent(in) :: v_pr

        real(kind=dp) :: tmp(1)

        call mxCopyPtrToReal8(v_pr, tmp, 1)
        v = int(tmp(1))
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse integer-valued vector from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine vector_integer_from_matlab(v, v_pr, n)
        integer, dimension(:), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n

        real(kind=dp), dimension(:), allocatable :: tmp

        call vector_real_from_matlab(tmp, v_pr, n)
        allocate (v(n))
        v = int(tmp)
        deallocate (tmp)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse integer-valued matrix from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine matrix_integer_from_matlab(v, v_pr, n, m)
        integer, dimension(:, :), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n, m

        real(kind=dp), dimension(:, :), allocatable :: tmp

        call matrix_real_from_matlab(tmp, v_pr, n, m)
        allocate (v(n, m))
        v = int(tmp)
        deallocate (tmp)
    end subroutine

    subroutine tensor_shape(v_pr, dims, n_dims)
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n_dims
        integer, intent(out) :: dims(:)
        integer fill_value, i
        mwSize :: n_dims_mw
        mwPointer, dimension(:), allocatable :: dims_mw ! See below, why this is not an int4

        mwPointer :: mxGetDimensions
        mwSize :: mxGetNumberOfDimensions
        n_dims_mw = mxGetNumberOfDimensions(v_pr)
        if ((n_dims .lt. 3 .and. int(n_dims_mw) .ne. n_dims) .or. int(n_dims_mw) .gt. n_dims) then
           call mexErrMsgIdAndTxt('MATLAB:tensor_shape:nInput', 'Dimension mismatch: tensor has incorrect number of dimensions')
        end if
        allocate (dims_mw(n_dims))

        ! Ugly hack to work around incompatibility of 32 and 64 bit systems,
        ! See https://ch.mathworks.com/matlabcentral/answers/93860-why-does-the-fortran-mex-api-function-mxcopyptrtointeger4-return-incorrect-results-on-64-bit-matlab
        call mxCopyPtrToPtrArray(mxGetDimensions(v_pr), dims_mw, n_dims_mw)
        dims(1:int(n_dims_mw)) = int(dims_mw)
        fill_value = 1
        do i=1, int(n_dims_mw)
           if (dims(i) .eq. 0) then
              fill_value = 0
              exit
           end if
        end do
        ! Fill up missing dimensions with 1:
        if (int(n_dims_mw) .lt. n_dims) then
           dims(int(n_dims_mw)+1:n_dims) = fill_value
        end if
        deallocate (dims_mw)
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse real-valued dynamic matrix from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine dyn_matrix_real_from_matlab(v, v_pr, n, m)
        real(kind=dp), dimension(:, :), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(out) :: n, m
        integer dims(2)

        mwPointer :: mxGetPr

        call tensor_shape(v_pr, dims, 2)
        n = dims(1)
        m = dims(2)
        call matrix_real_from_matlab(v, mxGetPr(v_pr), n, m)
    end subroutine
    !---------------------------------------------------------------------------
    ! Parse integer-valued dynamic matrix from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine dyn_matrix_integer_from_matlab(v, v_pr, n, m)
        integer, dimension(:, :), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(out) :: n, m
        integer dims(2)

        mwPointer :: mxGetPr

        call tensor_shape(v_pr, dims, 2)
        n = dims(1)
        m = dims(2)
        call matrix_integer_from_matlab(v, mxGetPr(v_pr), n, m)
    end subroutine dyn_matrix_integer_from_matlab
    !---------------------------------------------------------------------------
    ! Parse real-valued dynamic 3-tensor from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine dyn_tensor_3_real_from_matlab(t, v_pr, n, m, k)
        real(kind=dp), dimension(:, :, :), allocatable, intent(inout) :: t
        mwPointer, intent(in) :: v_pr
        integer, intent(out) :: n, m, k
        integer dims(3)

        mwPointer :: mxGetPr

        call tensor_shape(v_pr, dims, 3)
        allocate (t(dims(1), dims(2), dims(3)))
        call mxCopyPtrToReal8(mxGetPr(v_pr), t, product(dims))
        n = dims(1)
        m = dims(2)
        k = dims(3)
    end subroutine
    !---------------------------------------------------------------------------
    ! Parse real-valued 3-tensor from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine tensor_3_real_from_matlab(t, v_pr, n, m, k)
        real(kind=dp), dimension(:, :, :), allocatable, intent(inout) :: t
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n, m, k
        integer dim_1, dim_2, dim_3

        call dyn_tensor_3_real_from_matlab(t, v_pr, dim_1, dim_2, dim_3)
        if (dim_1 .ne. n) then
           call mexErrMsgIdAndTxt('MATLAB:tensor_3_real_from_matlab:shapeMismatch', 'Expected shape (n,:,:)')
        end if
        if (dim_2 .ne. m) then
           call mexErrMsgIdAndTxt('MATLAB:tensor_3_real_from_matlab:shapeMismatch', 'Expected shape (:,m,:)')
        end if
        if (dim_3 .ne. k) then
           call mexErrMsgIdAndTxt('MATLAB:tensor_3_real_from_matlab:shapeMismatch', 'Expected shape (:,:,k)')
        end if
    end subroutine

    !---------------------------------------------------------------------------
    ! Parse string-valued cell from MATLAB pointer.
    !---------------------------------------------------------------------------
    subroutine cell_string_from_matlab(v, v_pr, n, err_status)
        character (len=20), dimension(:), allocatable, intent(inout) :: v
        mwPointer, intent(in) :: v_pr
        integer, intent(in) :: n
        integer, intent(out) :: err_status
        integer :: i
        mwPointer :: cell_entry

        mwPointer :: mxGetCell
        integer mxGetString

        allocate (v(n))
        err_status = 0
        do i = 1, n
           cell_entry = mxGetCell(v_pr, i)
           if (cell_entry .eq. 0) then
              err_status = 1
              exit
           end if
           err_status = mxGetString(cell_entry, v(i), 20)
        end do
    end subroutine

    !---------------------------------------------------------------------------
    ! Create a real-valued matlab 3 dim array from a fortran array.
    !---------------------------------------------------------------------------
    function mex_double_array_3(arr) result(v_pr)
        mwPointer :: v_pr
        real(kind=dp), intent(in) :: arr(:, :, :)

        mwPointer :: mxCreateNumericArray, mxGetPr
        integer*4 :: mxClassIDFromClassName

        if (size(shape(arr)) .ne. 3) then
           call mexErrMsgIdAndTxt('MATLAB:mex_double_array_3:shapeMismatch', 'Expected shape (:,:,:)')
        end if

        v_pr = mxCreateNumericArray(3, shape(arr), mxClassIDFromClassName('double'), 0)
        call mxCopyReal8ToPtr(arr, mxGetPr(v_pr), size(arr))
    end function

end module mex_utils
