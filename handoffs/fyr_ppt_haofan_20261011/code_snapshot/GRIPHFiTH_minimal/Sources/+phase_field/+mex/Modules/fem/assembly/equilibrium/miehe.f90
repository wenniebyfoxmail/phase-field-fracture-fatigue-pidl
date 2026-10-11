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

module mod_equilibrium_miehe
  public equilibrium_miehe
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
  subroutine equilibrium_miehe(MESH, DOF, t, QUADRATURE, MAT_CHAR, &
       CC_mat, pfield, displ, num_entries, stress_state, &
       KK_vector, res_displ, strain_en_undgr)

    use matrix_utils, only: diasym, m22inv, m33inv
    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t, DOF_t
    use scalar_utils, only: H_p, H_n, dp

    implicit none

    type(MESH_t), intent(in) :: MESH
    type(DOF_t), intent(in) :: DOF
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR
    real(kind=dp), intent(in) :: CC_mat(:, :, :), pfield(:), displ(:)
    integer, intent(in) :: num_entries, stress_state

    real(kind=dp), intent(out) :: KK_vector(:), res_displ(:, :), strain_en_undgr(:, :)
    real(kind=dp) K, G, E, ni, lambda, res_stiff, lambda_loc, eps_33_fac
    integer, allocatable :: entry_1(:), entry_2(:), entry_3(:), entry_4(:)

    real(kind=dp), allocatable :: CC(:, :)
    real(kind=dp), allocatable :: II(:, :), Id(:, :)

    !Dynamic allocation ROUTINE & OUTPUT PARAMETERS
    integer, allocatable :: el_nodes(:), dof_idx(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_pfield(:), el_kk(:, :), el_displ(:), jac(:, :), inv_jac(:, :), dN_glob(:, :), &
         el_B(:, :), BtCB(:, :), BtCB_plus(:, :), CC_plus(:, :), CC_neg(:, :), &
         el_strain(:), el_strain_tensor(:, :), princ_dir(:, :), princ_strain(:), &
         M_proj(:, :), H_proj(:, :, :), G_proj(:, :, :, :), P_plus(:, :), P_neg(:, :), eps_plus(:, :), eps_neg(:, :), &
         sig_plus(:, :), sig_neg(:, :), sig_plus_voigt(:), sig_neg_voigt(:), sig_voigt(:), el_res(:), princ_strain_tensor(:, :)

    logical ok_flag
    integer element, G_pts, el_mat, idx_start, idx_final, eps_p_idx, eps_n_idx
    real(kind=dp) det_jac, CC_dmg, trace_eps

    !=================================================================
    allocate (el_nodes(MESH%nel))
    allocate (dof_idx(MESH%nel*DOF%num_dof_node))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (el_kk(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (el_displ(MESH%nel*DOF%num_dof_node))
    allocate (CC(MESH%tensors, MESH%tensors))
    allocate (CC_plus(MESH%tensors, MESH%tensors))
    allocate (CC_neg(MESH%tensors, MESH%tensors))
    allocate (el_strain(MESH%tensors))
    allocate (el_strain_tensor(MESH%dim, MESH%dim))
    allocate (princ_strain(MESH%dim))
    allocate (princ_dir(MESH%dim, MESH%dim))
    allocate (princ_strain_tensor(MESH%dim, MESH%dim))
    allocate (II(MESH%tensors, MESH%tensors))
    allocate (Id(MESH%dim, MESH%dim))
    allocate (jac(MESH%dim, MESH%dim))
    allocate (inv_jac(MESH%dim, MESH%dim))
    allocate (dN_glob(MESH%dim, MESH%nel))
    allocate (el_B(MESH%tensors, MESH%nel*DOF%num_dof_node))

    allocate (entry_1(MESH%tensors*MESH%tensors))
    allocate (entry_2(MESH%tensors*MESH%tensors))
    allocate (entry_3(MESH%tensors*MESH%tensors))
    allocate (entry_4(MESH%tensors*MESH%tensors))

    allocate (M_proj(MESH%tensors, MESH%dim));
    allocate (H_proj(MESH%tensors, MESH%tensors, MESH%dim));
    allocate (G_proj(MESH%tensors, MESH%tensors, MESH%dim, MESH%dim));
    allocate (P_plus(MESH%tensors, MESH%tensors));
    allocate (P_neg(MESH%tensors, MESH%tensors));
    allocate (eps_plus(MESH%dim, MESH%dim));
    allocate (eps_neg(MESH%dim, MESH%dim));
    allocate (sig_plus(MESH%dim, MESH%dim));
    allocate (sig_neg(MESH%dim, MESH%dim));
    allocate (sig_plus_voigt(MESH%tensors));
    allocate (sig_neg_voigt(MESH%tensors));
    allocate (sig_voigt(MESH%tensors));
    allocate (BtCB(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (BtCB_plus(MESH%nel*DOF%num_dof_node, MESH%nel*DOF%num_dof_node))
    allocate (el_res(MESH%nel*DOF%num_dof_node))

    res_displ = 0.0d0;
    KK_vector = 0.0d0;
    strain_en_undgr = 0.0d0;

    !PRELIMINARY DECLARATIONS
    if (MESH%dim == 2) then
       entry_1 = (/1, 3, 1, 3, 2, 3, 1, 3, 1/);
       entry_2 = (/1, 3, 3, 3, 2, 2, 3, 2, 2/);
       entry_3 = (/1, 3, 3, 3, 2, 2, 3, 2, 3/);
       entry_4 = (/1, 3, 1, 3, 2, 3, 1, 3, 3/);
       II = reshape((/1.0d0, 1.0d0, 0.0d0, &
            1.0d0, 1.0d0, 0.0d0, &
            0.0d0, 0.0d0, 0.0d0/), (/MESH%tensors, MESH%tensors/));
       Id = reshape((/1.0d0, 0.0d0, &
            0.0d0, 1.0d0/), (/MESH%dim, MESH%dim/));
    elseif (MESH%dim == 3) then
       entry_1 = (/1, 4, 6, 1, 4, 6, 4, 2, 5, 4, 2, 5, 6, 5, 3, 6, 5, 3, 1, 4, 6, 1, 4, 6, 4, 2, 5, 4, 2, 5, 6, 5, 3, 6, 5, 3/);
       entry_2 = (/1, 4, 6, 4, 6, 1, 4, 2, 5, 2, 5, 4, 6, 5, 3, 5, 3, 6, 4, 2, 5, 2, 5, 4, 6, 5, 3, 5, 3, 6, 1, 4, 6, 4, 6, 1/);
       entry_3 = (/1, 4, 6, 4, 6, 1, 4, 2, 5, 2, 5, 4, 6, 5, 3, 5, 3, 6, 4, 2, 5, 4, 6, 1, 6, 5, 3, 6, 5, 4, 1, 4, 6, 1, 4, 6/);
       entry_4 = (/1, 4, 6, 1, 4, 6, 4, 2, 5, 4, 2, 5, 6, 5, 3, 6, 5, 3, 1, 4, 6, 4, 2, 5, 4, 2, 5, 2, 5, 3, 6, 5, 3, 5, 3, 6/);
       II = reshape((/1.0d0, 1.0d0, 1.0d0, 0.0d0, 0.0d0, 0.0d0, &
            1.0d0, 1.0d0, 1.0d0, 0.0d0, 0.0d0, 0.0d0, &
            1.0d0, 1.0d0, 1.0d0, 0.0d0, 0.0d0, 0.0d0, &
            0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
            0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, &
            0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0, 0.0d0/), (/MESH%tensors, MESH%tensors/))

       Id = reshape((/1.0d0, 0.0d0, 0.0d0, &
            0.0d0, 1.0d0, 0.0d0, &
            0.0d0, 0.0d0, 1.0d0/), (/MESH%dim, MESH%dim/))
    end if


    !+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    do element = 1, MESH%num_elem !LOOP ON ELEMENTS

       el_nodes = 0;
       dof_idx = 0;
       el_mat = 0;
       el_coord = 0.0d0;
       el_pfield = 0.0d0;
       el_kk = 0.0d0;
       el_displ = 0.0d0;
       el_res = 0.0d0;
       el_nodes = MESH%elem(element, 1:MESH%nel); !nodes of the element
       el_coord = MESH%node(el_nodes, 1:MESH%dim); !coordinates of the nodes
       el_pfield = pfield(el_nodes);
       el_displ = displ((/el_nodes, el_nodes + MESH%num_node/));
       el_mat = MESH%elem_material_id(element)
       CC = CC_mat(:, :, el_mat)

       E = MAT_CHAR(el_mat)%E
       ni = MAT_CHAR(el_mat)%ni
       G = MAT_CHAR(el_mat)%G
       K = MAT_CHAR(el_mat)%K
       res_stiff = MAT_CHAR(el_mat)%res_stiff
       lambda = MAT_CHAR(el_mat)%lambda
       lambda_loc = lambda; !initialize for plane strain (for plane stress, it needs to be adjusted)
       !note: for plane stress, to be fully correct one would need to check further the epsilon_33 component,
       !see Li et al. (2021): 'A phase field method for plane-stress fracture problems with tension-compression asymmetry'
       !https://doi.org/10.1016/j.engfracmech.2021.107995
       if (stress_state==2) then
          eps_33_fac = lambda/(lambda+2*G);
          lambda_loc = lambda * (1-eps_33_fac);
       end if

       do G_pts = 1, QUADRATURE%num_gauss_pts !LOOP ON GAUSS POINTS

          det_jac = 0.0d0;
          CC_dmg = 0.0d0;
          trace_eps = 0.0d0;
          eps_p_idx = 0;
          eps_n_idx = 0;
          jac = 0.0d0;
          dN_glob = 0.0d0;
          el_B = 0.0d0;
          CC_plus = 0.0d0;
          CC_neg = 0.0d0;
          BtCB = 0.0d0;
          BtCB_plus = 0.0d0;
          el_strain = 0.0d0;
          el_strain_tensor = 0.0d0;
          princ_dir = 0.0d0;
          princ_strain = 0.0d0;
          princ_strain_tensor = 0.0d0;
          M_proj = 0.0d0;
          H_proj = 0.0d0;
          G_proj = 0.0d0;
          P_plus = 0.0d0;
          P_neg = 0.0d0;
          eps_plus = 0.0d0;
          eps_neg = 0.0d0;
          sig_plus = 0.0d0;
          sig_neg = 0.0d0;
          sig_plus_voigt = 0.0d0;
          sig_neg_voigt = 0.0d0;
          sig_voigt = 0.0d0;
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

          el_strain = matmul(el_B, el_displ)
          el_strain_tensor = reshape((/el_strain(1), 0.5d0*el_strain(3), &
               0.5d0*el_strain(3), el_strain(2)/), (/MESH%dim, MESH%dim/))

          princ_dir = el_strain_tensor
          call diasym(princ_dir, princ_strain, MESH%dim) !This might be modified introducing the analytical computation?

          princ_strain_tensor(1, 1) = princ_strain(1)
          princ_strain_tensor(2, 2) = princ_strain(2)

          CC_dmg = ((1.0d0 - dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield))**2 + res_stiff);
          if ((princ_strain(1) > 0.0d0) .and. (princ_strain(2) > 0.0d0)) then !ISOTROPIC MODEL
             CC_plus = CC;
             BtCB = matmul(transpose(el_B), matmul(CC_dmg*CC_plus, el_B))
             BtCB_plus = matmul(transpose(el_B), matmul(CC_plus, el_B))
             strain_en_undgr(element, G_pts) = 0.5d0*dot_product(el_displ, matmul(BtCB_plus, el_displ));
             sig_voigt = CC_dmg*matmul(CC_plus, el_strain);
          elseif ((princ_strain(1) <= 0.0d0) .and. (princ_strain(2) <= 0.0d0)) then !NO DISSIPATION
             CC_neg = CC;
             BtCB = matmul(transpose(el_B), matmul(CC_neg, el_B))
             BtCB_plus = matmul(transpose(el_B), matmul(CC_plus, el_B))
             strain_en_undgr(element, G_pts) = 0.0d0;
             sig_voigt = matmul(CC_neg, el_strain);
          else !STRAIN SPLIT
             !M_proj has in the column i the Voigt notation of the projector
             !n_i(x)n_i related to the eigenvalue i
             M_proj(1, 1) = princ_dir(1, 1)*princ_dir(1, 1); !n_1(x)n_1 in Voigt notation
             M_proj(2, 1) = princ_dir(2, 1)*princ_dir(2, 1);
             M_proj(3, 1) = princ_dir(1, 1)*princ_dir(2, 1);
             M_proj(1, 2) = princ_dir(1, 2)*princ_dir(1, 2); !n_2(x)n_2 in Voigt notation
             M_proj(2, 2) = princ_dir(2, 2)*princ_dir(2, 2);
             M_proj(3, 2) = princ_dir(1, 2)*princ_dir(2, 2);
             H_proj(:, :, 1) = matmul(reshape(M_proj(:, 1), (/MESH%tensors, 1/)), reshape(M_proj(:, 1), (/1, MESH%tensors/)));
             H_proj(:, :, 2) = matmul(reshape(M_proj(:, 2), (/MESH%tensors, 1/)), reshape(M_proj(:, 2), (/1, MESH%tensors/)));
             G_proj(:,:,1,2) = reshape(((M_proj(entry_1,1)*M_proj(entry_2,2)) + (M_proj(entry_3,1)*M_proj(entry_4,2))), (/MESH%tensors, MESH%tensors/));
             G_proj(:,:,2,1) = reshape(((M_proj(entry_1,2)*M_proj(entry_2,1)) + (M_proj(entry_3,2)*M_proj(entry_4,1))), (/MESH%tensors, MESH%tensors/));
             ! BUG FIX 1 (Carrara campaign 2026-05-01): correctly identify positive vs negative
             ! eigenvalue indices. Previously hardcoded as eps_n_idx=1, eps_p_idx=2 regardless
             ! of which principal strain was actually positive — gave sign-flipped projector
             ! whenever diasym returned eigenvalues in opposite order, causing NaN at cycle 2 in
             ! cyclic loading.
             if (princ_strain(1) > 0.0d0) then
                eps_p_idx = 1
                eps_n_idx = 2
             else
                eps_p_idx = 2
                eps_n_idx = 1
             end if
             ! BUG FIX 2: protect (eps_p - eps_n) divide-by-zero when eigenvalues are equal.
             ! In strain-split branch, eps_p > 0 and eps_n <= 0 so diff > 0 always except at
             ! eps_n = 0 with eps_p approaching 0 from above. When diff < tol use ISOTROPIC fallback.
             if (abs(princ_strain(eps_p_idx) - princ_strain(eps_n_idx)) < 1.0d-14) then
                P_plus = H_proj(:,:,eps_p_idx)
                P_neg  = H_proj(:,:,eps_n_idx)
             else
                P_plus = ( princ_strain(eps_p_idx)/(2.0d0*(princ_strain(eps_p_idx)-princ_strain(eps_n_idx))) ) * (G_proj(:,:,eps_p_idx,eps_n_idx)+G_proj(:,:,eps_n_idx,eps_p_idx)) + H_proj(:,:,eps_p_idx);
                P_neg  = ( princ_strain(eps_n_idx)/(2.0d0*(princ_strain(eps_n_idx)-princ_strain(eps_p_idx))) ) * (G_proj(:,:,eps_n_idx,eps_p_idx)+G_proj(:,:,eps_p_idx,eps_n_idx)) + H_proj(:,:,eps_n_idx);
             end if
             eps_plus = matmul(princ_dir, matmul(0.5*(princ_strain_tensor + abs(princ_strain_tensor)), transpose(princ_dir)));
             eps_neg = matmul(princ_dir, matmul(0.5*(princ_strain_tensor - abs(princ_strain_tensor)), transpose(princ_dir)));
             trace_eps = el_strain(1) + el_strain(2)

             ! BUG FIX 3: protect H_p(trace)/trace and H_n(trace)/trace when trace = 0
             ! (deviatoric strain or balanced volumetric). H_p/H_n are sharp Macaulay brackets,
             ! so H_p(0)/0 = 0/0 = NaN. Mathematical limits: x>0 -> 1, x<0 -> 0, x=0 -> 0.5
             ! (we use 0 conservatively at exact zero — no volumetric contribution).
             if (trace_eps > 0.0d0) then
                CC_plus = lambda_loc*II + (2.0d0*G*P_plus);
                CC_neg  = (2.0d0*G*P_neg);
             else if (trace_eps < 0.0d0) then
                CC_plus = (2.0d0*G*P_plus);
                CC_neg  = lambda_loc*II + (2.0d0*G*P_neg);
             else
                CC_plus = (2.0d0*G*P_plus);
                CC_neg  = (2.0d0*G*P_neg);
             end if
             sig_plus = (lambda_loc*H_p(trace_eps)*Id) + (2.0d0*G*eps_plus);
             sig_neg = (lambda_loc*H_n(trace_eps)*Id) + (2.0d0*G*eps_neg);
             sig_plus_voigt = (/sig_plus(1, 1), sig_plus(2, 2), sig_plus(1, 2)/);
             sig_neg_voigt = (/sig_neg(1, 1), sig_neg(2, 2), sig_neg(1, 2)/);
             sig_voigt = sig_neg_voigt + (CC_dmg*sig_plus_voigt);
             BtCB = matmul(transpose(el_B), matmul((CC_neg + CC_dmg*CC_plus), el_B))

             strain_en_undgr(element,G_pts) = 0.5d0*(lambda_loc * (H_p(trace_eps)**2) + 2.0d0*G*(eps_plus(1,1)**2 + eps_plus(2,2)**2 + 2.0d0*eps_plus(1,2)**2));
          end if

          el_kk = el_kk + t*QUADRATURE%gauss_W(G_pts)*det_jac*BtCB
          el_res = el_res + t*QUADRATURE%gauss_W(G_pts)*det_jac*matmul(transpose(el_B), sig_voigt)

       end do

       dof_idx = (/el_nodes, el_nodes + MESH%num_node/);
       idx_start = ((element - 1)*num_entries) + 1
       idx_final = element*num_entries
       KK_vector(idx_start:idx_final) = reshape(el_kk, (/num_entries/))

       res_displ(dof_idx, 1) = res_displ(dof_idx, 1) + el_res;
    end do
    return
  end subroutine equilibrium_miehe
endmodule mod_equilibrium_miehe
