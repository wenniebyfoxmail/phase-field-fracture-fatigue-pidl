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

module mod_pf_integration
   public pf_integration
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
   subroutine pf_integration(MESH, t, QUADRATURE, pfield, rel_pf, d_int)
     
     use types, only: QUADRATURE_t, MESH_t
     use scalar_utils, only: dp
     use system_factors, only: BtB_detJ, NtN_GP
 
     implicit none
 
     type(MESH_t), intent(in) :: MESH
     real(kind=dp), intent(in) :: t
     type(QUADRATURE_t), intent(in) :: QUADRATURE
     real(kind=dp), intent(in) :: pfield(:)
 
     real(kind=dp), intent(out) :: d_int(:)
     
     integer element, G_pts
     real(kind=dp) det_jac, G_pts_pf, rel_pf
     integer, allocatable :: el_nodes(:)
     real(kind=dp), allocatable :: el_coord(:, :), el_d_int(:), el_pfield(:), BtB(:, :)
     
     !=================================================================
     allocate (el_nodes(MESH%nel))
     allocate (el_coord(MESH%nel, MESH%dim))
     allocate (el_pfield(MESH%nel))
     allocate (el_d_int(1))
     allocate (BtB(MESH%nel, MESH%nel))
     
     d_int = 0.0d0;
     
     do element = 1, MESH%num_elem !LOOP ON ELEMENTS
 
        el_d_int = 0.0d0;
        el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
        el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
        el_pfield = pfield(el_nodes);
        
        do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS
           G_pts_pf = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield);

           if (G_pts_pf < rel_pf) then
              G_pts_pf = 0.0d0;
           end if
           
           call BtB_detJ(QUADRATURE%dNdxi(:, :, G_pts), el_coord, MESH%dim, MESH%nel, BtB, det_jac);
           
           el_d_int = el_d_int + G_pts_pf*t*QUADRATURE%gauss_W(G_pts)*det_jac;
        end do
        
        d_int = d_int + el_d_int;
     end do
     return
   end subroutine pf_integration
 endmodule mod_pf_integration
 