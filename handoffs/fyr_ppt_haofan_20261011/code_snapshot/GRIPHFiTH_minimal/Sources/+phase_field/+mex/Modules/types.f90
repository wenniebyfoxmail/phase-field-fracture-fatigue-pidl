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

module types
  use scalar_utils, only: dp

  implicit none
  ! The `implicit none` statement works for all subroutines/functions in a module

  public MAT_CHAR_t, DOF_t, MESH_t, QUADRATURE_t, BOUNDARY_CONDS_t
  type MAT_CHAR_t
     real(kind=dp) :: E, ni, G, K, lambda, Gc, ell, res_stiff, alpha_T, p, penalty_irrev, penalty_recov
     real(kind=dp) :: traction_p, a1, a2, a3
  end type MAT_CHAR_t
  type MESH_t
     integer :: num_node, num_elem, nel, nel_tract, dim, tensors
     real(kind=dp), dimension(:, :), allocatable :: node  ! num_node x dim
     integer, dimension(:, :), allocatable :: elem  ! num_elem x nel
     integer, dimension(:), allocatable :: elem_material_id  ! num_elem
  end type MESH_t
  type DOF_t
     integer :: num_dof_node, num_dof
  end type DOF_t
  type QUADRATURE_t
     integer :: order
     integer :: num_gauss_pts
     real(kind=dp), dimension(:, :), allocatable :: gauss_pts  ! num_gauss_pts x MESH%dim
     real(kind=dp), dimension(:), allocatable :: gauss_W  ! num_gauss_pts
     real(kind=dp), dimension(:, :, :), allocatable :: dNdxi ! MESH%dim x MESH%nel x num_gauss_pts
     real(kind=dp), dimension(:, :), allocatable :: Nxi  ! MESH%nel x num_gauss_pts
     integer :: num_gauss_pts_tract  ! computed as: order * (MESH%dim - 1)
     real(kind=dp), dimension(:, :), allocatable :: gauss_pts_tract  ! num_gauss_pts_tract x (MESH%dim - 1)
     real(kind=dp), dimension(:), allocatable :: gauss_W_tract  ! num_gauss_pts_tract
     real(kind=dp), dimension(:, :), allocatable :: dNdxi_tract ! MESH%nel_tract x num_gauss_pts_tract
     real(kind=dp), dimension(:, :), allocatable :: Nxi_tract  ! MESH%nel_tract x num_gauss_pts_tract
  end type QUADRATURE_t
  type BOUNDARY_CONDS_t
     integer :: num_conn_tract  ! computed: numel_struct_field
     integer, dimension(:), allocatable :: conn_tract  ! num_conn_tract
     integer, dimension(:), allocatable :: flag_tract  ! MESH%num_elem
     integer, dimension(:, :), allocatable :: tract_face  ! MESH%num_elem x MESH%nel
     integer :: num_elem_tract  ! computed: numel_struct_field
     integer, dimension(:), allocatable :: elem_tract  ! num_elem_tract
     integer :: num_non_hom_dirichlet_bc  ! computed: numel_struct_field
     integer, dimension(:), allocatable :: non_hom_dirichlet_bc  ! num_non_hom_dirichlet_bc
     integer :: num_dirichlet_bc_pf ! computed: numel_struct_field
     integer, dimension(:), allocatable :: dirichlet_bc_pf  ! num_dirichlet_bc_pf
     real(kind=dp) :: tx_final, ty_final, tx_increment, ty_increment
  end type BOUNDARY_CONDS_t
contains
end module types
