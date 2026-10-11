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

module mod_pf_at2_penalty
  public pf_at2_penalty
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
  subroutine pf_at2_penalty(MESH, t, QUADRATURE, MAT_CHAR, &
       strain_en_undgr, pfield, pfield_old, &
       KK_d_vector, res_p_field)

    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
    use scalar_utils, only: dp
    use system_factors, only: BtB_detJ, NtN_GP

    implicit none

    type(MESH_t), intent(in) :: MESH
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR
    real(kind=dp), intent(in) :: strain_en_undgr(:, :), pfield(:), pfield_old(:)

    real(kind=dp), intent(out) :: KK_d_vector(:), res_p_field(:)

    integer element, G_pts, el_mat, idx_start, idx_final
    real(kind=dp) ell, Gc, det_jac, tmp_1, G_pts_pf, G_pts_pf_old, penalty
    integer, allocatable :: el_nodes(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_kk_d(:, :), el_rhs_d(:), &
         el_pfield(:), el_pfield_old(:), NtN(:, :), BtB(:, :)

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (el_pfield_old(MESH%nel))
    allocate (el_kk_d(MESH%nel, MESH%nel))
    allocate (el_rhs_d(MESH%nel))
    allocate (NtN(MESH%nel, MESH%nel))
    allocate (BtB(MESH%nel, MESH%nel))

    KK_d_vector = 0.0d0;
    res_p_field = 0.0d0;

    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

       el_kk_d = 0.0d0;
       el_rhs_d = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
       el_pfield = pfield(el_nodes);
       el_pfield_old = pfield_old(el_nodes);
       el_mat = MESH%elem_material_id(element)

       Gc = MAT_CHAR(el_mat)%Gc
       ell = MAT_CHAR(el_mat)%ell

       do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

          G_pts_pf = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield);
          G_pts_pf_old = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield_old);

          penalty = 0.0d0;
          if ((G_pts_pf - G_pts_pf_old) < 0.0d0) then
             penalty = MAT_CHAR(1)%penalty_irrev;
          end if

          call BtB_detJ(QUADRATURE%dNdxi(:, :, G_pts), el_coord, MESH%dim, MESH%nel, BtB, det_jac);
          call NtN_GP(QUADRATURE%Nxi(:, G_pts), MESH%nel, NtN);
          
          tmp_1 = 2.0d0*strain_en_undgr(element, G_pts);
          el_kk_d = el_kk_d + t*QUADRATURE%gauss_W(G_pts)*det_jac*( &
               (Gc/ell + tmp_1 + penalty)*NtN + Gc*ell*BtB);
          el_rhs_d = el_rhs_d + t*QUADRATURE%gauss_W(G_pts)*det_jac*( &
               tmp_1*QUADRATURE%Nxi(:, G_pts) &
               + penalty*matmul(NtN, el_pfield_old) &
               );
       end do

       idx_start = (element - 1)*MESH%nel*MESH%nel + 1
       idx_final = element*MESH%nel*MESH%nel

       KK_d_vector(idx_start:idx_final) = reshape(el_kk_d, (/MESH%nel*MESH%nel/))
       res_p_field(el_nodes) = res_p_field(el_nodes) + matmul(el_kk_d, el_pfield) - el_rhs_d;
    end do
    return
  end subroutine pf_at2_penalty
endmodule mod_pf_at2_penalty
