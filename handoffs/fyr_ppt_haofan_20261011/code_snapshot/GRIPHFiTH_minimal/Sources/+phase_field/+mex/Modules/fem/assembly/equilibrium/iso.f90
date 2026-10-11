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

module mod_equilibrium_iso
  public equilibrium_iso
contains
  !======================================================================
  ! Purpose: ...
  !
  ! Inputs:
  ! ...
  !
  ! Outputs:
  ! ...
  !===============================================================================
  subroutine equilibrium_iso(MESH, DOF, t, QUADRATURE, MAT_CHAR, &
       CC_mat, pfield, displ, num_entries, &
       KK_vector, res_displ, strain_en_undgr)

    use matrix_utils, only: m22inv, m33inv
    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t, DOF_t
    use scalar_utils, only: dp

    implicit none

    type(MESH_t), intent(in) :: MESH
    type(DOF_t), intent(in) :: DOF
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR
    real(kind=dp), intent(in) :: CC_mat(:, :, :), pfield(:), displ(:)
    integer, intent(in) :: num_entries

    real(kind=dp), intent(out) :: KK_vector(:), res_displ(:, :), strain_en_undgr(:, :)

    real(kind=dp) res_stiff

    real(kind=dp), allocatable :: CC(:, :)
    integer, allocatable :: el_nodes(:), dof_idx(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_pfield(:), el_kk(:, :), el_displ(:), jac(:, :), inv_jac(:, :), dN_glob(:, :), &
         el_B(:, :), BtCB(:, :)

    logical(8) ok_flag
    integer element, G_pts, el_mat, idx_start, idx_final
    real(kind=dp) det_jac, CC_dmg

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (dof_idx(MESH%nel*DOF%num_dof_node))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (CC(MESH%tensors, MESH%tensors))
    allocate (el_kk(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (el_displ(MESH%nel*DOF%num_dof_node))
    allocate (jac(MESH%dim, MESH%dim))
    allocate (inv_jac(MESH%dim, MESH%dim))
    allocate (dN_glob(MESH%dim, MESH%nel))
    allocate (el_B(MESH%tensors, MESH%nel*DOF%num_dof_node))
    allocate (BtCB(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))

    res_displ = 0.0d0;
    KK_vector = 0.0d0;
    strain_en_undgr = 0.0d0;

    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

       el_nodes = 0;
       dof_idx = 0;
       el_mat = 0;
       el_coord = 0.0d0;
       el_pfield = 0.0d0;
       CC = 0.0d0;
       el_kk = 0.0d0;
       el_displ = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
       el_pfield = pfield(el_nodes);
       el_mat = MESH%elem_material_id(element)
       CC = CC_mat(:, :, el_mat)
       el_displ = displ((/el_nodes, el_nodes + MESH%num_node/));
       res_stiff = MAT_CHAR(el_mat)%res_stiff

       do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

          det_jac = 0.0d0;
          CC_dmg = 0.0d0;
          jac = 0.0d0;
          dN_glob = 0.0d0;
          el_B = 0.0d0;
          BtCB = 0.0d0;
          jac = matmul(QUADRATURE%dNdxi(:, :, G_pts), el_coord);
          if (MESH%dim == 2) then
             call m22inv(jac, inv_jac, det_jac, ok_flag)
          else if (MESH%dim == 3) then
             call m33inv(jac, inv_jac, det_jac, ok_flag)
          end if

          dN_glob = matmul(inv_jac, QUADRATURE%dNdxi(:, :, G_pts));
          el_B(1, 1:MESH%nel) = dN_glob(1, :)
          el_B(2, MESH%nel + 1:MESH%nel*DOF%num_dof_node) = dN_glob(2, :)
          el_B(3, :) = (/dN_glob(2, :), dN_glob(1, :)/)

          CC_dmg = ((1.0d0 - dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield))**2 + res_stiff);
          BtCB = matmul(transpose(el_B), matmul(CC, el_B))

          el_kk = el_kk + t*QUADRATURE%gauss_W(G_pts)*det_jac*CC_dmg*BtCB

          strain_en_undgr(element, G_pts) = 0.5d0*dot_product(el_displ, matmul(BtCB, el_displ));
       end do

       dof_idx = (/el_nodes, el_nodes + MESH%num_node/);
       idx_start = ((element - 1)*num_entries) + 1
       idx_final = element*num_entries
       KK_vector(idx_start:idx_final) = reshape(el_kk, (/num_entries/))

       res_displ(dof_idx, 1) = res_displ(dof_idx, 1) + matmul(el_kk, el_displ);
    end do
    return
  end subroutine equilibrium_iso
endmodule mod_equilibrium_iso
