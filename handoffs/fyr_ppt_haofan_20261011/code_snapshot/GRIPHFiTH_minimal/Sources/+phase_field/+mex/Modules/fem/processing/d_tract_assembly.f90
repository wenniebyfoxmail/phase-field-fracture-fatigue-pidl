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

module mod_d_tract_assembly
  public d_tract_assembly
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
  subroutine d_tract_assembly(MESH, DOF, t, QUADRATURE, BOUNDARY_CONDS, i_step, &
       D_RHS_tract)

    use types, only: QUADRATURE_t, MESH_t, DOF_t, BOUNDARY_CONDS_t
    use array_utils, only: distance2d
    use scalar_utils, only: dp

    implicit none

    type(MESH_t), intent(in) :: MESH
    type(DOF_t), intent(in) :: DOF
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(BOUNDARY_CONDS_t), intent(in) :: BOUNDARY_CONDS
    real(kind=dp), intent(in) :: i_step

    real(kind=dp), intent(out) :: D_RHS_tract(:)

    integer element, G_pts, pts, j, i, start, final
    real(kind=dp) det_jac
    integer, allocatable :: el_nodes(:), FACE_nodes(:)
    real(kind=dp), allocatable :: el_coord(:, :), FACE_coord(:, :), FACE_rel_pos(:), el_f(:), Nt(:, :)

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (FACE_nodes(MESH%nel_tract))
    allocate (FACE_coord(MESH%nel_tract, MESH%dim))
    allocate (FACE_rel_pos(MESH%nel_tract))
    allocate (el_f(MESH%nel_tract*DOF%num_dof_node))
    allocate (Nt(MESH%nel_tract*DOF%num_dof_node, MESH%dim))

    D_RHS_tract = 0.0d0;

    do j = 1, BOUNDARY_CONDS%num_elem_tract !LOOP ON ELEMENTS

       element = BOUNDARY_CONDS%elem_tract(j)
       el_nodes = 0;
       el_coord = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes

       do i = 1, MESH%nel !LOOP ON GAUSS POINTS

          if (BOUNDARY_CONDS%tract_face(element, i) == 1) then !SELECTION IF

             start = 0;
             final = 0;
             el_f = 0.0d0;
             FACE_nodes = 0;
             FACE_coord = 0.0d0;
             if (i /= MESH%nel) then
                start = i;
                final = i + 1;
             else
                start = MESH%nel;
                final = 1;
             end if

             FACE_nodes = el_nodes((/start, final/));
             FACE_coord = el_coord((/start, final/), 1:MESH%dim);
             do pts = 1, MESH%nel_tract
                FACE_rel_pos(pts) = distance2d(FACE_coord(pts, :), FACE_coord(1, :))
             end do

             do G_pts = 1, QUADRATURE%num_gauss_pts_tract

                det_jac = 0.0d0;
                Nt = 0.0d0;
                det_jac = dot_product(QUADRATURE%dNdxi_tract(:, G_pts), FACE_rel_pos);
                Nt = reshape((/QUADRATURE%Nxi_tract(:, G_pts), 0.0d0, 0.0d0, 0.0d0, 0.0d0, QUADRATURE%Nxi_tract(:, G_pts)/), (/4, 2/))

                el_f = el_f + t*QUADRATURE%gauss_W_tract(G_pts)*det_jac*matmul(Nt, (/BOUNDARY_CONDS%tx_increment, BOUNDARY_CONDS%ty_increment/))*i_step

             end do

             D_RHS_tract((/FACE_nodes, FACE_nodes + MESH%num_node/)) = D_RHS_tract((/FACE_nodes, FACE_nodes + MESH%num_node/)) + el_f;
          end if !END if FOR SELECTION

       end do

    end do
    return
  end subroutine d_tract_assembly
endmodule mod_d_tract_assembly
