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

module mod_l2_projection
  public l2_projection
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
  subroutine l2_projection(MESH, DOF, t, QUADRATURE, CC_mat, &
       pfield, num_history_vars, history_vars, history_vars_L2, stress_L2)

    use types, only: QUADRATURE_t, MESH_t, DOF_t
    use matrix_utils, only: m22inv, m33inv
    use scalar_utils, only: dp

    implicit none

    type(MESH_t), intent(in) :: MESH
    type(DOF_t), intent(in) :: DOF
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    integer, intent(in) :: num_history_vars
    real(kind=dp), intent(in) :: CC_mat(:, :, :), pfield(:), history_vars(:, :, :)

    real(kind=dp), intent(out) :: history_vars_L2(:, :), stress_L2(:)

    logical(8) ok_flag
    integer element, G_pts, el_mat, j, idx_start, idx_final, hist_idx
    real(kind=dp) det_jac, CC_dmg
    integer, allocatable :: el_nodes(:)
    real(kind=dp), allocatable :: CC(:, :), el_coord(:, :), el_pfield(:), &
         jac(:, :), inv_jac(:, :), dN_glob(:, :), el_B(:, :), el_sig(:, :), &
         N_block(:, :), el_hist_idx(:, :)

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (jac(MESH%dim, MESH%dim))
    allocate (inv_jac(MESH%dim, MESH%dim))
    allocate (dN_glob(MESH%dim, MESH%nel))
    allocate (CC(MESH%tensors, MESH%tensors))
    allocate (el_B(MESH%tensors, MESH%nel*DOF%num_dof_node))
    allocate (el_sig(MESH%tensors*MESH%nel, MESH%nel*DOF%num_dof_node))
    allocate (N_block(MESH%tensors, MESH%nel*MESH%tensors))
    allocate (el_hist_idx(MESH%nel, num_history_vars))

    stress_L2 = 0.0d0;
    history_vars_L2 = 0.0d0;

    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

       el_nodes = 0;
       el_mat = 0;
       el_coord = 0.0d0;
       el_pfield = 0.0d0;
       el_sig = 0.0d0;
       el_hist_idx = 0.0d0;
       CC = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
       el_pfield = pfield(el_nodes); !Should it be el_nodes transpose?
       el_mat = MESH%elem_material_id(element)

       CC = CC_mat(:, :, el_mat)

       do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

          det_jac = 0.0d0;
          CC_dmg = 0.0d0;
          jac = 0.0d0;
          dN_glob = 0.0d0;
          el_B = 0.0d0;
          N_block = 0.0d0;

          !compute stress
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

          !compute contribution of stress
          CC_dmg = ((1 - dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield))**2);
          el_sig = el_sig + t*QUADRATURE%gauss_W(G_pts)*det_jac*CC_dmg*matmul(transpose(N_block), matmul(CC, el_B));

          !compute contribution of each history variable
          do hist_idx = 1, num_history_vars
            el_hist_idx(:, hist_idx) = el_hist_idx(:, hist_idx) + t*QUADRATURE%gauss_W(G_pts)*det_jac*history_vars(element, G_pts, hist_idx)*QUADRATURE%Nxi(:, G_pts)
          end do
          
       end do

       !assemble vector for the L2 projection for the stress
       idx_start = ((element - 1)*MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node) + 1
       idx_final = element*MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node
       stress_L2(idx_start:idx_final) = reshape(el_sig, (/MESH%nel*MESH%tensors*MESH%nel*DOF%num_dof_node/))

       !assemble all vectors for the L2 projection for the history variables
       do hist_idx = 1, num_history_vars
         history_vars_L2(el_nodes, hist_idx) = history_vars_L2(el_nodes, hist_idx) + el_hist_idx(:, hist_idx);
       end do


    end do
    return
  end subroutine l2_projection
endmodule mod_l2_projection
