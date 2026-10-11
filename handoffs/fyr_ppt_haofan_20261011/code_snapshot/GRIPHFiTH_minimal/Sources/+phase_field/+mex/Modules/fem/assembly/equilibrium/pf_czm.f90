! Copyright (C) 2026 ETH Zurich, SIS ID and CompMech D-MAVT
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

! Equilibrium kernel for Wu PF-CZM (Wu 2017 IJSS / Baktheer 2024).
!
! No volumetric-deviatoric or spectral split: effective stress = full elastic.
! Cauchy stress sigma = g(d) * CC * eps, tangent K = g(d) * CC.
! Driving force Y (output through the legacy `strain_en_undgr` array) =
! <sigma_tilde_1>_+^2 / (2 E_0)
! with sigma_tilde_1 = first principal of the effective (undegraded) stress.
! This kernel therefore changes the semantic meaning of `strain_en_undgr` from
! "undegraded tensile strain energy" to "Wu crack-driving force Y"; wrappers
! and post-processing must treat the PF-CZM branch accordingly.
!
! Author: Windows-FEM (FEM-9 Task G, 2026-05-12)
! Pattern: iso.f90 (no-split equilibrium) + Wu g(d) rational-fraction +
!          principal-stress driving-force projection.

module mod_equilibrium_pf_czm
  public equilibrium_pf_czm
contains

  !-----------------------------------------------------------------------------
  ! Wu PF-CZM degradation g(d), including the optional cubic a3 term used by
  ! Wu's concrete softening law. Existing exponential/linear cases set a3=0.
  ! Identical math to wu_degradation in pf_czm_fatigue.f90 — duplicated here
  ! to avoid cross-module dependency at link time (small price for a 30-line subroutine).
  !-----------------------------------------------------------------------------
  pure subroutine wu_g(d, p_exp, a1, a2, a3, g_val)
    use scalar_utils, only: dp
    real(kind=dp), intent(in) :: d, p_exp, a1, a2, a3
    real(kind=dp), intent(out) :: g_val
    real(kind=dp) :: dc, q, phi, w
    dc  = max(0.0d0, 1.0d0 - d)
    q   = dc**p_exp
    phi = a1*d + a1*a2*d*d + a1*a2*a3*d*d*d
    w   = q + phi
    if (w < 1.0d-30) then
       g_val = 0.0d0
    else
       g_val = q / w
    end if
  end subroutine wu_g

  !-----------------------------------------------------------------------------
  ! First principal component of the (positive) effective 2D stress.
  ! Inputs: sigma_xx, sigma_yy, sigma_xy (Voigt: t[1], t[2], t[3])
  ! Output: <sigma_1>_+ (Macaulay)
  !-----------------------------------------------------------------------------
  pure function macaulay_sigma1_2D(s_xx, s_yy, s_xy) result(s1_plus)
    use scalar_utils, only: dp
    real(kind=dp), intent(in) :: s_xx, s_yy, s_xy
    real(kind=dp) :: s1_plus, half_sum, disc, sqrt_disc, s1
    half_sum  = 0.5d0 * (s_xx + s_yy)
    disc      = 0.25d0*(s_xx - s_yy)**2 + s_xy*s_xy
    if (disc < 0.0d0) disc = 0.0d0      ! safety against tiny negative round-off
    sqrt_disc = sqrt(disc)
    s1        = half_sum + sqrt_disc
    s1_plus   = max(0.0d0, s1)
  end function macaulay_sigma1_2D

  !-----------------------------------------------------------------------------
  ! Main equilibrium assembly
  !-----------------------------------------------------------------------------
  subroutine equilibrium_pf_czm(MESH, DOF, t, QUADRATURE, MAT_CHAR, &
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

    real(kind=dp) res_stiff, p_exp, a1, a2, a3, E_mod
    real(kind=dp), allocatable :: CC(:, :), el_strain(:), sigma_eff(:)
    integer, allocatable :: el_nodes(:), dof_idx(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_pfield(:), el_kk(:, :), &
         el_displ(:), jac(:, :), inv_jac(:, :), dN_glob(:, :), &
         el_B(:, :), BtCB(:, :)

    logical(8) ok_flag
    integer element, G_pts, el_mat, idx_start, idx_final
    real(kind=dp) det_jac, g_d, G_pts_pf, sigma1_plus, Y_GP

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
    allocate (el_strain(MESH%tensors))
    allocate (sigma_eff(MESH%tensors))

    res_displ = 0.0d0
    KK_vector = 0.0d0
    strain_en_undgr = 0.0d0

    do element = 1, MESH%num_elem
       el_nodes  = MESH%elem(element, 1:MESH%nel)
       el_coord  = MESH%node(el_nodes, 1:MESH%dim)
       el_pfield = pfield(el_nodes)
       el_mat    = MESH%elem_material_id(element)
       CC        = CC_mat(:, :, el_mat)
       el_displ  = displ((/el_nodes, el_nodes + MESH%num_node/))
       res_stiff = MAT_CHAR(el_mat)%res_stiff
       E_mod     = MAT_CHAR(el_mat)%E
       p_exp     = MAT_CHAR(el_mat)%traction_p
       a1        = MAT_CHAR(el_mat)%a1
       a2        = MAT_CHAR(el_mat)%a2
       a3        = MAT_CHAR(el_mat)%a3

       el_kk = 0.0d0

       do G_pts = 1, QUADRATURE%num_gauss_pts
          jac = matmul(QUADRATURE%dNdxi(:, :, G_pts), el_coord)
          if (MESH%dim == 2) then
             call m22inv(jac, inv_jac, det_jac, ok_flag)
          else if (MESH%dim == 3) then
             call m33inv(jac, inv_jac, det_jac, ok_flag)
          end if

          dN_glob = matmul(inv_jac, QUADRATURE%dNdxi(:, :, G_pts))
          el_B = 0.0d0
          el_B(1, 1:MESH%nel) = dN_glob(1, :)
          el_B(2, MESH%nel + 1:MESH%nel*DOF%num_dof_node) = dN_glob(2, :)
          el_B(3, :) = (/dN_glob(2, :), dN_glob(1, :)/)

          ! Strain at Gauss point
          el_strain = matmul(el_B, el_displ)

          ! Effective stress sigma_tilde = CC * eps  (Voigt: xx, yy, xy)
          sigma_eff = matmul(CC, el_strain)

          ! PF-CZM reuses the legacy `strain_en_undgr` container to carry Y.
          ! Downstream code must not interpret this field as elastic energy.
          ! Driving force Y = <sigma_tilde_1>_+^2 / (2 E_0)  (Wu / Baktheer)
          sigma1_plus = macaulay_sigma1_2D(sigma_eff(1), sigma_eff(2), sigma_eff(3))
          Y_GP = sigma1_plus*sigma1_plus / (2.0d0 * E_mod)
          strain_en_undgr(element, G_pts) = Y_GP

          ! Degradation g(d) at this GP
          G_pts_pf = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield)
          call wu_g(G_pts_pf, p_exp, a1, a2, a3, g_d)
          ! Apply residual-stiffness floor as in amor/iso kernels
          g_d = g_d + res_stiff

          ! Tangent stiffness = g(d) * CC
          BtCB = matmul(transpose(el_B), matmul(CC, el_B))
          el_kk = el_kk + t * QUADRATURE%gauss_W(G_pts) * det_jac * g_d * BtCB
       end do

       dof_idx = (/el_nodes, el_nodes + MESH%num_node/)
       idx_start = ((element - 1)*num_entries) + 1
       idx_final = element*num_entries
       KK_vector(idx_start:idx_final) = reshape(el_kk, (/num_entries/))
       res_displ(dof_idx, 1) = res_displ(dof_idx, 1) + matmul(el_kk, el_displ)
    end do
    return
  end subroutine equilibrium_pf_czm
end module mod_equilibrium_pf_czm
