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

module mod_fracture_energy
  public fracture_energy
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
  subroutine fracture_energy(MESH, t, QUADRATURE, MAT_CHAR, &
       CC_mat, pfield, c_w, order, &
       fract_en)

    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
    use scalar_utils, only: dp
    use system_factors, only: BtB_detJ

    implicit none

    type(MESH_t), intent(in) :: MESH
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR
    real(kind=dp), intent(in) :: CC_mat(:, :, :), pfield(:)
    real(kind=dp), intent(in) :: c_w
    integer, intent(in) :: order

    real(kind=dp), intent(out) :: fract_en

    real(kind=dp) ell, Gc, det_jac
    integer element, el_mat, G_pts
    real(kind=dp), allocatable :: CC(:, :)
    integer, allocatable :: el_nodes(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_pfield(:), &
         tmp_1(:, :), tmp_4(:), BtB(:, :)

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (CC(MESH%tensors, MESH%tensors))
    allocate (tmp_1(MESH%nel, MESH%nel))
    allocate (tmp_4(1))
    allocate (BtB(MESH%nel, MESH%nel))

    fract_en = 0.0d0;

    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

        el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
        el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
        el_pfield = pfield(el_nodes);
        el_mat = MESH%elem_material_id(element)

        CC = CC_mat(:, :, el_mat)
        Gc = MAT_CHAR(el_mat)%Gc
        ell = MAT_CHAR(el_mat)%ell

        do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

            call BtB_detJ(QUADRATURE%dNdxi(:, :, G_pts), el_coord, MESH%dim, MESH%nel, BtB, det_jac);
            tmp_1 = Gc*ell*BtB;
            tmp_4 = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield);
            if (order == 2) then
               tmp_4 = tmp_4*tmp_4;
            end if
            tmp_4 = Gc/ell*tmp_4 + dot_product(el_pfield, matmul(tmp_1, el_pfield));
            fract_en = fract_en + t/c_w*QUADRATURE%gauss_W(G_pts)*det_jac*tmp_4(1);
        end do

    end do
    return
  end subroutine fracture_energy
endmodule mod_fracture_energy
