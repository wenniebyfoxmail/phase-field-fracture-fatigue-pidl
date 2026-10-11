"""scaling.py — Physical PCC ↔ PIDL-normalized unit conversion.

Phase 2A infrastructure (2026-05-14, Mac dev). Pure utility module; no PIDL
imports. Defines the dimensionless mapping for running PCC concrete physics
in the existing PIDL codebase that uses `mat_E=1` normalized units.

## Non-dim scheme

Two reference quantities (Buckingham π):
    L_char = W_phys                                    — domain width
    sigma_char = sqrt(E_phys * G_f_phys / ell_phys)    — Griffith critical stress

Then (corrected normalization per external expert review, 2026-05-14):
    mat_E_norm = E_phys / sigma_char² * sigma_char² / E_phys = 1     ✓ matches toy
    domain_norm = [-W/(2*L_char), +W/(2*L_char)] = [-0.5, 0.5]      ✓ matches toy
    l0_norm = ell_phys / L_char    (typically O(0.01-0.05))
    w1_norm = w1_phys / psi_char    ← CORRECTED: was σ_char, now ψ_char
              where w1_phys = G_f * c_w / ell_phys  (cohesive-driver stress, MPa)
                    psi_char = sigma_char² / E_phys  (energy density scale, MPa)
              c_w = 8/3 for AT1, c_w = 2 for AT2
              Under Griffith σ_char: ψ_char = G_f/ell, so w1_norm = c_w
              (= 8/3 ≈ 2.67 for AT1, = 2.0 for AT2 PCC)
    alpha_T_norm = alpha_T_phys / psi_char

## Why ψ_char (not σ_char) for w1_norm?

PIDL's compute_energy.py builds the damage-energy integrand as
    E_d_density = (w1/c_w) * [w(α) + l0² * |∇α|²]
which has units of stress (MPa) — but represents an ENERGY DENSITY, not a stress.
To non-dim correctly, the natural denominator is the energy-density scale
ψ_char = σ_char²/E, not σ_char itself.

The earlier "w1_norm = w1_phys/σ_char" gave 3.44e-3 for AT1 PCC — wrong by
factor ~σ_char/ψ_char = E/σ_char ≈ 775×. That made damage cost vanishingly
small in PIDL, which would (a) artificially favor crack growth and
(b) confound any "Phase 2A null result" with a core scaling bug rather than
true Carrara structural asymmetry. External expert review flagged this 2026-05-14.

## What PCC reveals vs toy (corrected)

α_T/ψ_char ratio measures fatigue/critical-energy gap:
- toy: α_T_norm = 0.5, ψ_char_norm ≡ 1 by def. → ratio ≈ 0.5 (low-cycle regime)
- PCC: α_T_norm = 100 → ratio ≈ 100 (much higher cycle count to activate fatigue)

At S^max=0.75·f_t in normalized units:
    σ_norm = 0.75·f_t / σ_char = 0.75·3 / 38.73 ≈ 0.058
    ψ_per_cycle_norm ≈ σ_norm²/2 ≈ 1.7e-3   (NOT 0.56 as previously claimed)
    N_f_pure_estimate = α_T_norm / ψ_per_cycle ≈ 100/1.7e-3 ≈ **6×10⁴ cycles**
        for the linear pre-fatigue regime (f=1 still).

This is deep VHCF — well beyond what PIDL can train in a paper-timescale run.
Phase 2A first smoke at N=50 is expected to show ᾱ accumulating LINEARLY but
very slowly (~50·1.7e-3 ≈ 0.085 = 0.085% of α_T), with f≈1 throughout and
no observable d-localization. This is a "infrastructure transition" smoke,
NOT a discriminator between Phase 2A and Phase 2B kernel adequacy.

## Caveat — uncalibrated load mapping (P1, P2, P4 from expert review)

`disp_for_stress_intact()` below assumes intact-bar kinematics
u_top = (σ/E)·H, which is exact only for an uncracked uniform bar. With the
SENT precrack at a₀=W/2 the compliance is higher, so the same prescribed
displacement gives a nominal stress LESS than the target. The runner's
`disp_ratio_intact` label is therefore an "intact-bar displacement-equivalent
stress ratio", NOT a calibrated cracked-geometry nominal stress. Compare
against Baktheer with this caveat.

Also: this default `a0_phys = W/2 = 50 mm` reuses the toy half-width notch
geometry so the existing toy mesh (`meshed_geom1.msh`) can be reused unchanged.
Earlier FEM PCC line used `a0 = 5 mm` (a₀/W = 0.05). Phase 2A units transition
is NOT geometrically equivalent to the FEM PCC line — geometry-vs-units
effects are confounded here. Treat as Phase 2A units-transition smoke only.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PCCScaling:
    """Physical PCC parameters + derived characteristic scales + non-dim values.

    Physical units: E in MPa, lengths in mm, G_f in N/mm, stresses in N/mm² (= MPa).

    Usage:
        s = PCCScaling.baktheer_default(pff_model='AT1')
        config.mat_prop_dict['mat_E'] = s.mat_E_norm
        config.mat_prop_dict['mat_nu'] = s.mat_nu_norm
        config.mat_prop_dict['w1']    = s.w1_norm
        config.mat_prop_dict['l0']    = s.l0_norm
        config.fatigue_dict['alpha_T']  = s.alpha_T_norm
        config.fatigue_dict['disp_max'] = s.disp_for_stress_intact(0.75 * s.ft_phys)
    """
    # ── Physical PCC parameters ─────────────────────────────────────────────
    E_phys:       float    # Young's modulus (MPa)
    nu_phys:      float    # Poisson ratio
    G_f_phys:     float    # Fracture energy (N/mm)
    ft_phys:      float    # Tensile strength (MPa) — used for loading target only
    ell_phys:     float    # Phase-field length scale (mm)
    alpha_T_phys: float    # Fatigue threshold (N/mm²) per Baktheer 2024
    W_phys:       float    # Domain width (mm) — used as L_char
    H_phys:       float    # Domain height (mm)
    a0_phys:      float    # Initial crack length (mm)
    pff_model:    str = 'AT1'   # 'AT1' or 'AT2' (determines c_w in w1 formula)

    # ── Derived characteristic scales (auto-computed) ───────────────────────
    L_char:       float = 0.0   # = W_phys
    sigma_char:   float = 0.0   # = sqrt(E * G_f / ell)  (Griffith)
    u_char:       float = 0.0   # = L_char * sigma_char / E_phys
    psi_char:     float = 0.0   # = sigma_char² / E_phys  (energy density scale)
    c_w:          float = 0.0   # 8/3 for AT1, 2 for AT2

    def __post_init__(self):
        c_w = {'AT1': 8.0/3.0, 'AT2': 2.0}[self.pff_model]
        L_char = self.W_phys
        sigma_char = (self.E_phys * self.G_f_phys / self.ell_phys) ** 0.5
        u_char = L_char * sigma_char / self.E_phys
        psi_char = sigma_char ** 2 / self.E_phys
        for name, val in [('L_char', L_char), ('sigma_char', sigma_char),
                          ('u_char', u_char), ('psi_char', psi_char), ('c_w', c_w)]:
            object.__setattr__(self, name, val)

    # ── PIDL-compatible dimensionless values ────────────────────────────────
    @property
    def mat_E_norm(self) -> float:
        """Always 1.0 — preserves existing PIDL toy convention."""
        return 1.0

    @property
    def mat_nu_norm(self) -> float:
        """Poisson ratio is dimensionless."""
        return self.nu_phys

    @property
    def l0_norm(self) -> float:
        """l0_norm = ell / W. For PCC: 2/100 = 0.02 (close to toy 0.01)."""
        return self.ell_phys / self.L_char

    @property
    def w1_phys(self) -> float:
        """Cohesive-driver stress in physical units: w1 = G_f * c_w / ell."""
        return self.G_f_phys * self.c_w / self.ell_phys

    @property
    def w1_norm(self) -> float:
        """w1_norm = w1_phys / psi_char.

        CORRECTED 2026-05-14 (expert review P0): w1 is non-dim stand-in for
        cohesive-driver stress in an ENERGY DENSITY integrand, so it must be
        normalized by the energy-density scale ψ_char = σ²/E, not by σ_char.

        Under Griffith σ_char = sqrt(E·G_f/ell): ψ_char = G_f/ell, and
        w1_phys = G_f·c_w/ell, so analytically w1_norm = c_w.
            AT1 PCC: w1_norm = 8/3 ≈ 2.667
            AT2 PCC: w1_norm = 2.0

        Prior buggy version (w1_phys/σ_char) gave 3.44e-3 — wrong by ~775×.
        That made the damage cost vanishingly small, which would artificially
        favor crack growth and confound any "Phase 2A null result" with
        scaling bug rather than Carrara structural asymmetry.
        """
        return self.w1_phys / self.psi_char

    @property
    def G_c_norm(self) -> float:
        """G_c in normalized units; sanity check."""
        return self.G_f_phys / (self.sigma_char * self.L_char)

    @property
    def alpha_T_norm(self) -> float:
        """alpha_T / psi_char.

        Ratio measures the fatigue-relative-to-critical-energy gap:
          toy ≈ 1.3 (low-cycle fatigue regime)
          PCC ≈ 100 (VHCF / structural-asymmetry regime — Carrara prediction)
        """
        return self.alpha_T_phys / self.psi_char

    @property
    def W_norm(self) -> float:
        return self.W_phys / self.L_char    # = 1.0 by construction

    @property
    def H_norm(self) -> float:
        return self.H_phys / self.L_char

    @property
    def a0_norm(self) -> float:
        return self.a0_phys / self.L_char    # = 0.5 for SENT half-width notch

    # ── Loading conversion ──────────────────────────────────────────────────
    def disp_for_stress_intact(self, sigma_target_phys: float) -> float:
        """Top-boundary displacement (normalized) under INTACT-BAR kinematics.

        ⚠ CAVEAT (P1 from expert review 2026-05-14):
        This assumes uniform-strain compliance ε = σ/E, u_top = ε × H_phys —
        valid only for an uncracked uniform bar. For a SENT specimen with
        a precrack at a₀/W = 0.5, the effective compliance is significantly
        higher, so the prescribed displacement gives a nominal far-field stress
        LESS than the target. Use this as a displacement-equivalent label, NOT
        as a calibrated nominal stress.

        Returns:
            u_norm such that the INTACT-bar interpretation maps it to
            sigma_target_phys. The realized nominal stress in the cracked
            geometry is smaller — calibrate separately if anchor needed.
        """
        eps_phys = sigma_target_phys / self.E_phys
        u_phys = eps_phys * self.H_phys
        return u_phys / self.u_char

    # Back-compat alias (deprecated — use disp_for_stress_intact for clarity)
    disp_for_stress = disp_for_stress_intact

    def disp_phys_to_norm(self, u_phys_mm: float) -> float:
        return u_phys_mm / self.u_char

    def disp_norm_to_phys(self, u_norm: float) -> float:
        """Re-dimensionalize NN displacement output (mm)."""
        return u_norm * self.u_char

    def stress_norm_to_phys(self, sigma_norm: float) -> float:
        """Re-dimensionalize stress (MPa)."""
        return sigma_norm * self.sigma_char

    def psi_norm_to_phys(self, psi_norm: float) -> float:
        """Re-dimensionalize energy density (MPa = N/mm²)."""
        return psi_norm * self.psi_char

    # ── Factory ─────────────────────────────────────────────────────────────
    @classmethod
    def baktheer_default(cls, pff_model: str = 'AT1') -> "PCCScaling":
        """Default PCC concrete params per Baktheer 2024 arXiv calibration.

        E=30 GPa, nu=0.18, G_f=0.10 N/mm, f_t=3 MPa, ell=2 mm, alpha_T=5 N/mm².
        Domain: 100×100 mm SENT, a₀=50 mm (= W/2).
        """
        return cls(
            E_phys=30_000.0,
            nu_phys=0.18,
            G_f_phys=0.10,
            ft_phys=3.0,
            ell_phys=2.0,
            alpha_T_phys=5.0,
            W_phys=100.0,
            H_phys=100.0,
            a0_phys=50.0,
            pff_model=pff_model,
        )

    # ── Debug summary ───────────────────────────────────────────────────────
    def summary(self) -> str:
        return (
            f"PCC Scaling Summary ({self.pff_model})\n"
            f"  Physical:  E={self.E_phys:.1f} MPa  nu={self.nu_phys}\n"
            f"             G_f={self.G_f_phys} N/mm  f_t={self.ft_phys} MPa  ell={self.ell_phys} mm\n"
            f"             alpha_T={self.alpha_T_phys} N/mm²\n"
            f"             Domain {self.W_phys}x{self.H_phys} mm, a0={self.a0_phys} mm\n"
            f"  Char scales:  c_w={self.c_w:.4f}\n"
            f"             L_char={self.L_char:.1f} mm  sigma_char={self.sigma_char:.2f} MPa (Griffith)\n"
            f"             u_char={self.u_char:.3e} mm  psi_char={self.psi_char:.3e} MPa\n"
            f"             w1_phys={self.w1_phys:.4f} MPa (cohesive-driver stress)\n"
            f"             G_c_norm={self.G_c_norm:.3e}\n"
            f"  PIDL-ready (non-dim):\n"
            f"             mat_E={self.mat_E_norm}  mat_nu={self.mat_nu_norm}\n"
            f"             w1={self.w1_norm:.5f}  l0={self.l0_norm}\n"
            f"             alpha_T={self.alpha_T_norm:.2f}  (vs toy 0.5; ratio ≈ {self.alpha_T_norm/0.5:.0f}×)\n"
            f"             Domain [-0.5, 0.5]²  (W_norm={self.W_norm})  a0_norm={self.a0_norm}\n"
            f"             [intact-bar kinematics labels; realized cracked-nominal stress is LESS]\n"
            f"             u_norm(0.75·f_t)_intact = {self.disp_for_stress_intact(0.75 * self.ft_phys):.4f}\n"
            f"             u_norm(0.50·f_t)_intact = {self.disp_for_stress_intact(0.50 * self.ft_phys):.4f}\n"
            f"             u_norm(1.00·f_t)_intact = {self.disp_for_stress_intact(1.00 * self.ft_phys):.4f}\n"
        )


if __name__ == "__main__":
    print(PCCScaling.baktheer_default('AT1').summary())
    print()
    print(PCCScaling.baktheer_default('AT2').summary())
