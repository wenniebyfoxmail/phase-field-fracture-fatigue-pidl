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

! Phase-field kernel: Wu PF-CZM (Wu 2017 IJSS) with Carrara unidirectional fatigue.
! Geometric function alpha(d) = 2d - d^2 (xi=2), c_alpha = pi, degradation
! g(d) = (1-d)^p / [(1-d)^p + phi(d)] with
! phi(d) = a1*d + a1*a2*d^2 + a1*a2*a3*d^3. Wu's concrete law uses a3;
! legacy exponential/linear cases set a3=0.
! Driving force is H = max over time of Y where Y comes from equilibrium kernel
! (Macaulay bracket on first principal effective stress).
!
! Author: Windows-FEM (FEM-9 Task G, 2026-05-12)
! Pattern: at2_history_fatigue.f90 (existing AT2+HISTORY+Carrara) extended with
!          rational-fraction g(d) derivatives and Wu alpha(d) geometric function.

module mod_pf_pf_czm_fatigue
  public pf_pf_czm_fatigue
contains

  !-----------------------------------------------------------------------------
  ! Wu PF-CZM degradation function and derivatives
  ! g(d) = q(d) / w(d)   with q(d) = (1-d)^p, w(d) = q(d) + phi(d),
  !                            phi(d) = a1*d + a1*a2*d^2 + a1*a2*a3*d^3
  !-----------------------------------------------------------------------------
  pure subroutine wu_degradation(d, p_exp, a1, a2, a3, g, gp, gpp)
    use scalar_utils, only: dp
    real(kind=dp), intent(in) :: d, p_exp, a1, a2, a3
    real(kind=dp), intent(out) :: g, gp, gpp
    real(kind=dp) :: dc, q, qp, qpp, phi, phip, phipp, w, wp, wpp

    dc   = max(0.0d0, 1.0d0 - d)          ! (1 - d) clipped non-negative
    q    = dc**p_exp
    qp   = -p_exp * dc**(p_exp - 1.0d0)
    qpp  =  p_exp * (p_exp - 1.0d0) * dc**(p_exp - 2.0d0)

    phi   = a1*d + a1*a2*d*d + a1*a2*a3*d*d*d
    phip  = a1 + 2.0d0*a1*a2*d + 3.0d0*a1*a2*a3*d*d
    phipp = 2.0d0*a1*a2 + 6.0d0*a1*a2*a3*d

    w    = q + phi
    wp   = qp + phip
    wpp  = qpp + phipp

    ! Quotient rule with safety on w
    ! g'' from full quotient rule (Day-1 code had 2*gp*w*wp, missing one factor
    ! of w; FD check P4 2026-05-12 caught rel err = 19. Correct: 2*gp*w*w*wp).
    if (w < 1.0d-30) then
       g   = 0.0d0
       gp  = 0.0d0
       gpp = 0.0d0
    else
       g   = q / w
       gp  = (qp*w - q*wp) / (w*w)
       gpp = (qpp*w*w - q*wpp*w - 2.0d0*gp*w*w*wp) / (w*w*w)
    end if
  end subroutine wu_degradation

  !-----------------------------------------------------------------------------
  ! Wu geometric function alpha(d) = 2d - d^2 and derivatives
  !-----------------------------------------------------------------------------
  pure subroutine wu_alpha(d, alpha_d, alpha_p, alpha_pp)
    use scalar_utils, only: dp
    real(kind=dp), intent(in) :: d
    real(kind=dp), intent(out) :: alpha_d, alpha_p, alpha_pp
    alpha_d  = 2.0d0*d - d*d
    alpha_p  = 2.0d0 - 2.0d0*d
    alpha_pp = -2.0d0
  end subroutine wu_alpha

  !-----------------------------------------------------------------------------
  ! Main kernel: assemble K_dd and residual for the d-PDE.
  !
  ! Inputs:
  !   strain_en_undgr(:,:)  : Y per (element, Gauss pt) from equilibrium kernel
  !                            (= <sigma_tilde_1>_+ ^2 / (2 E0))
  !   history_vars_old(:,:,k):
  !                            k=1 : H (max Y so far + H_min)
  !                            k=2 : alpha_bar (Carrara accumulator)
  !                            k=3 : g(d_prev) * Y_prev   (for Carrara delta-alphabar)
  !                            k=4 : f(alpha_bar) (cached fat_deg)
  !   pfield(:)             : current d nodal values
  !
  ! Outputs:
  !   KK_d_vector, res_p_field, history_vars_new
  !-----------------------------------------------------------------------------
  subroutine pf_pf_czm_fatigue(MESH, t, QUADRATURE, MAT_CHAR, &
       strain_en_undgr, history_vars_old, pfield, &
       KK_d_vector, res_p_field, history_vars_new)

    use types, only: MAT_CHAR_t, QUADRATURE_t, MESH_t
    use scalar_utils, only: dp, H_p
    use system_factors, only: BtB_detJ, NtN_GP

    implicit none

    type(MESH_t), intent(in) :: MESH
    real(kind=dp), intent(in) :: t
    type(QUADRATURE_t), intent(in) :: QUADRATURE
    type(MAT_CHAR_t), dimension(:), intent(in) :: MAT_CHAR
    real(kind=dp), intent(in) :: strain_en_undgr(:, :), history_vars_old(:, :, :), pfield(:)
    real(kind=dp), intent(out) :: KK_d_vector(:), res_p_field(:), history_vars_new(:, :, :)

    integer element, G_pts, el_mat, idx_start, idx_final
    real(kind=dp) ell, Gc, alpha_T, p_fat, res_stiff, det_jac
    real(kind=dp) p_exp, a1, a2, a3, c_alpha
    real(kind=dp) H_t, Y_t, Y_prev, g_d, gp_d, gpp_d
    real(kind=dp) alpha_d, alpha_p, alpha_pp
    real(kind=dp) Dalpha, alpha_np1, fat_deg, fat_deg_min
    real(kind=dp) G_pts_pf, coef_NtN_K, coef_NtN_R, coef_BtB
    integer, allocatable :: el_nodes(:)
    real(kind=dp), allocatable :: el_coord(:, :), el_kk_d(:, :), el_res_d(:), &
         el_pfield(:), NtN(:, :), BtB(:, :)

    ! Wu PF-CZM constants
    c_alpha = 3.14159265358979323846d0   ! pi
    fat_deg_min = 1.0d-6                  ! floor to prevent solver stall

    allocate (el_nodes(MESH%nel))
    allocate (el_coord(MESH%nel, MESH%dim))
    allocate (el_pfield(MESH%nel))
    allocate (el_kk_d(MESH%nel, MESH%nel))
    allocate (el_res_d(MESH%nel))
    allocate (NtN(MESH%nel, MESH%nel))
    allocate (BtB(MESH%nel, MESH%nel))

    KK_d_vector = 0.0d0
    res_p_field = 0.0d0

    do element = 1, MESH%num_elem
       el_kk_d  = 0.0d0
       el_res_d = 0.0d0
       el_nodes  = MESH%elem(element, 1:MESH%nel)
       el_coord  = MESH%node(el_nodes, 1:MESH%dim)
       el_pfield = pfield(el_nodes)
       el_mat    = MESH%elem_material_id(element)

       Gc        = MAT_CHAR(el_mat)%Gc
       ell       = MAT_CHAR(el_mat)%ell
       alpha_T   = MAT_CHAR(el_mat)%alpha_T
       p_fat     = MAT_CHAR(el_mat)%p
       res_stiff = MAT_CHAR(el_mat)%res_stiff
       ! Wu PF-CZM specific (NEW fields in MAT_CHAR — add via material_characteristic.m)
       p_exp = MAT_CHAR(el_mat)%traction_p
       a1    = MAT_CHAR(el_mat)%a1
       a2    = MAT_CHAR(el_mat)%a2
       a3    = MAT_CHAR(el_mat)%a3

       do G_pts = 1, QUADRATURE%num_gauss_pts
          ! Current d at Gauss point
          G_pts_pf = dot_product(QUADRATURE%Nxi(:, G_pts), el_pfield)

          ! History: H = max over time of Y, with H_min initial threshold
          ! (H_min is folded into history_vars_old(:,:,1) by the init step.)
          Y_t   = strain_en_undgr(element, G_pts)
          H_t   = max(history_vars_old(element, G_pts, 1), Y_t)
          history_vars_new(element, G_pts, 1) = H_t

          ! Wu degradation at current d
          call wu_degradation(G_pts_pf, p_exp, a1, a2, a3, g_d, gp_d, gpp_d)

          ! Carrara fatigue layer (unidirectional on degraded driving force g(d)*Y)
          ! Note: g(d_prev) * Y_prev stored in history slot k=3
          Y_prev   = history_vars_old(element, G_pts, 3)
          Dalpha   = H_p(g_d * Y_t - Y_prev)
          alpha_np1 = history_vars_old(element, G_pts, 2) + Dalpha
          fat_deg  = (2.0d0*alpha_T / (alpha_np1 + alpha_T))**p_fat
          fat_deg  = min(1.0d0, fat_deg)
          fat_deg  = max(fat_deg, fat_deg_min)

          history_vars_new(element, G_pts, 2) = alpha_np1
          history_vars_new(element, G_pts, 3) = g_d * Y_t
          history_vars_new(element, G_pts, 4) = fat_deg

          ! Wu geometric function derivatives
          call wu_alpha(G_pts_pf, alpha_d, alpha_p, alpha_pp)

          ! Element matrices
          call BtB_detJ(QUADRATURE%dNdxi(:, :, G_pts), el_coord, MESH%dim, MESH%nel, BtB, det_jac)
          call NtN_GP(QUADRATURE%Nxi(:, G_pts), MESH%nel, NtN)

          ! Wu PF-CZM is nonlinear in d. Unlike AT1/AT2, the residual cannot be
          ! reconstructed as K(d)*d - rhs because g'(d) and alpha'(d) are not
          ! affine in d. Assemble the variational residual directly:
          !   R_d  = N^T [ g'(d)*H + f*(G_c/(c_alpha*ell))*alpha'(d) ]
          !        + f * B^T [ 2*G_c*ell/c_alpha ] grad d
          ! and the Newton tangent as dR_d/dd. This matches Wu's UEL up to the
          ! global residual sign convention (Abaqus stores rd = -R_d).
          ! fat_deg placement on the G_c/dissipation side only (Baktheer 2024 Eq. 38).
          coef_NtN_K =  gpp_d * H_t + fat_deg * (Gc / (c_alpha * ell)) * alpha_pp
          coef_NtN_R =  gp_d  * H_t + fat_deg * (Gc / (c_alpha * ell)) * alpha_p
          coef_BtB   =  fat_deg * 2.0d0 * Gc * ell / c_alpha

          el_kk_d  = el_kk_d  + t * QUADRATURE%gauss_W(G_pts) * det_jac * &
                                (coef_NtN_K * NtN + coef_BtB * BtB)
          el_res_d = el_res_d + t * QUADRATURE%gauss_W(G_pts) * det_jac * &
                                (coef_NtN_R * QUADRATURE%Nxi(:, G_pts) + &
                                 coef_BtB * matmul(BtB, el_pfield))
       end do

       idx_start = (element - 1)*MESH%nel*MESH%nel + 1
       idx_final =  element*MESH%nel*MESH%nel
       KK_d_vector(idx_start:idx_final) = reshape(el_kk_d, (/MESH%nel*MESH%nel/))
       res_p_field(el_nodes) = res_p_field(el_nodes) + el_res_d
    end do
    return
  end subroutine pf_pf_czm_fatigue
end module mod_pf_pf_czm_fatigue
