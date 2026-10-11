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

module mod_equilibrium_initial
  public equilibrium_initial
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
  subroutine equilibrium_initial(MESH, DOF, t, QUADRATURE, MAT_CHAR, CC_mat, pfield, num_entries, &
       KK_vector, i_row, j_col, M_vector, &
       i_row_sig, j_col_sig, eps_vector, &
       i_row_eps, j_col_eps, &
       sig0_vector, &
       i_row_pf, j_col_pf)

    use matrix_utils, only: m22inv, m33inv
    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t, DOF_t
    use scalar_utils, only: dp

    implicit none

    type(MESH_t), intent(in) :: MESH
    type(DOF_t), intent(in) :: DOF
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR    
    real(kind=dp), intent(in) :: CC_mat(:, :, :), pfield(:)
    integer, intent(in) :: num_entries

    real(kind=dp), intent(out) :: KK_vector(:)
    integer, intent(out) :: i_row(:), j_col(:)
    real(kind=dp), intent(out) :: M_vector(:)
    integer, intent(out) :: i_row_sig(:), j_col_sig(:)
    real(kind=dp), intent(out) :: eps_vector(:)
    integer, intent(out) :: i_row_eps(:), j_col_eps(:)
    real(kind=dp), intent(out) :: sig0_vector(:)
    integer, intent(out) :: i_row_pf(:), j_col_pf(:)

    real(kind=dp), allocatable :: CC(:, :)

    real(kind=dp) res_stiff
    !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
    integer, allocatable :: el_nodes(:), dof_idx(:), sig_idx(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_pfield(:), el_kk(:, :), jac(:, :), inv_jac(:, :), dN_glob(:, :), &
         el_B(:, :), el_M_block(:, :), el_eps(:, :), el_sig(:, :), CC_dmg(:, :), BtCB(:, :), &
         N_block(:, :)

    logical ok_flag
    integer element, G_pts, j, i, idx_start, idx_final, el_mat
    real(kind=dp) det_jac

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (dof_idx(MESH%nel*DOF%num_dof_node))
    allocate (sig_idx(MESH%nel*MESH%tensors))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (CC(MESH%tensors, MESH%tensors))
    allocate (el_kk(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (jac(MESH%dim, MESH%dim))
    allocate (inv_jac(MESH%dim, MESH%dim))
    allocate (dN_glob(MESH%dim, MESH%nel))
    allocate (el_B(MESH%tensors, MESH%nel*DOF%num_dof_node))
    allocate (el_eps(MESH%tensors*MESH%nel, MESH%nel*DOF%num_dof_node))
    allocate (el_sig(MESH%tensors*MESH%nel, MESH%nel*DOF%num_dof_node))
    allocate (el_M_block(MESH%nel, MESH%nel))
    allocate (CC_dmg(MESH%tensors, MESH%tensors))
    allocate (BtCB(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (N_block(MESH%tensors, MESH%nel*MESH%tensors))

    KK_vector = 0.0d0;
    M_vector = 0.0d0;
    eps_vector = 0.0d0;
    sig0_vector = 0.0d0;
    i_row = 0;
    j_col = 0;
    i_row_sig = 0;
    j_col_sig = 0;
    i_row_eps = 0;
    j_col_eps = 0;
    i_row_pf = 0;
    j_col_pf = 0;

    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

       el_nodes = 0;
       dof_idx = 0;
       sig_idx = 0;
       el_mat = 0;
       el_coord = 0.0d0;
       el_pfield = 0.0d0;
       CC = 0.0d0;
       el_kk = 0.0d0;
       el_eps = 0.0d0;
       el_sig = 0.0d0;
       el_M_block = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
       el_pfield = pfield(el_nodes); !Should it be el_nodes transpose?
       el_mat = MESH%elem_material_id(element)
       CC = CC_mat(:, :, el_mat)
       
       res_stiff = MAT_CHAR(el_mat)%res_stiff       

       do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

          det_jac = 0.0d0;
          jac = 0.0d0;
          dN_glob = 0.0d0;
          el_B = 0.0d0;
          CC_dmg = 0.0d0;
          BtCB = 0.0d0;
          N_block = 0.0d0;
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

          do j = 1, MESH%tensors
             N_block(j, (j - 1)*MESH%nel + 1:j*MESH%nel) = reshape(QUADRATURE%Nxi(:, G_pts), (/MESH%nel/))
          end do

          CC_dmg = ((1 - dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield))**2 + res_stiff)*CC;
          BtCB = matmul(transpose(el_B), matmul(CC_dmg, el_B))

          el_kk = el_kk + t*QUADRATURE%gauss_W(G_pts)*det_jac*BtCB
          el_M_block = el_M_block + t*QUADRATURE%gauss_W(G_pts)*det_jac*matmul(reshape(QUADRATURE%Nxi(:, G_pts), (/MESH%nel, 1/)), reshape(QUADRATURE%Nxi(:, G_pts), (/1, MESH%nel/))); !
          el_eps = el_eps + t*QUADRATURE%gauss_W(G_pts)*det_jac*matmul(transpose(N_block), el_B);
          el_sig = el_sig + t*QUADRATURE%gauss_W(G_pts)*det_jac*matmul(transpose(N_block), matmul(CC, el_B));
       end do

       dof_idx = (/el_nodes, el_nodes + MESH%num_node/);
       sig_idx = (/el_nodes, el_nodes + MESH%num_node, el_nodes + (2*MESH%num_node)/)

       idx_start = ((element - 1)*num_entries) + 1
       idx_final = element*num_entries
       KK_vector(idx_start:idx_final) = reshape(el_kk, (/num_entries/))

       ! matrix for L2-projection
       idx_start = ((element - 1)*MESH%nel*MESH%nel*MESH%tensors) + 1
       idx_final = element*MESH%nel*MESH%nel*MESH%tensors
       M_vector(idx_start:idx_final) = (/reshape(el_M_block, (/MESH%nel*MESH%nel/)), reshape(el_M_block, (/MESH%nel*MESH%nel/)), reshape(el_M_block, (/MESH%nel*MESH%nel/))/)

       ! vectors for L2-projection of strain and stress
       idx_start = ((element - 1)*MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node) + 1
       idx_final = element*MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node
       eps_vector(idx_start:idx_final) = reshape(el_eps, (/MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node/))
       sig0_vector(idx_start:idx_final) = reshape(el_sig, (/MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node/))

       do j = 1, MESH%nel*DOF%num_dof_node
          idx_start = (element - 1)*num_entries + (MESH%nel*DOF%num_dof_node)*(j - 1) + 1
          idx_final = (element - 1)*num_entries + (MESH%nel*DOF%num_dof_node)*(j)
          i_row(idx_start:idx_final) = dof_idx
          j_col(idx_start:idx_final) = dof_idx(j)
          idx_start = (element - 1)*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node + (MESH%nel*MESH%tensors)*(j - 1) + 1
          idx_final = (element - 1)*MESH%tensors*MESH%nel*MESH%nel*DOF%num_dof_node + (MESH%nel*MESH%tensors)*(j)
          i_row_eps(idx_start:idx_final) = sig_idx
          j_col_eps(idx_start:idx_final) = dof_idx(j)
       end do

       do i = 1, MESH%tensors
          do j = 1, MESH%nel
             idx_start = (element - 1)*MESH%tensors*MESH%nel*MESH%nel + (i - 1)*MESH%nel*MESH%nel + (MESH%nel)*(j - 1) + 1
             idx_final = (element - 1)*MESH%tensors*MESH%nel*MESH%nel + (i - 1)*MESH%nel*MESH%nel + (MESH%nel)*(j)
             i_row_sig(idx_start:idx_final) = el_nodes(j) + ((i - 1)*MESH%num_node)
             j_col_sig(idx_start:idx_final) = el_nodes + ((i - 1)*MESH%num_node)
          end do
       end do

       do j = 1, MESH%nel
          idx_start = ((element - 1)*MESH%nel*MESH%nel) + ((j - 1)*MESH%nel) + 1
          idx_final = ((element - 1)*MESH%nel*MESH%nel) + ((j)*MESH%nel)
          i_row_pf(idx_start:idx_final) = el_nodes
          j_col_pf(idx_start:idx_final) = el_nodes(j)
       end do

    end do
    return
  end subroutine equilibrium_initial
endmodule mod_equilibrium_initial
