"""Physical-to-PIDL scaling for phase-field fracture and fatigue.

The PIDL energy implementation uses

    E_d = (w1 / c_w) [w(alpha) + ell**2 |grad(alpha)|**2],

so ``w1`` has units of energy density and is exactly ``G_c / ell``.  The
normalization below chooses

    psi_ref = G_c / ell,
    sigma_ref = sqrt(E G_c / ell),
    u_ref = L_ref sqrt(G_c / (E ell)).

This gives the code-compatible normalized values ``mat_E = 1`` and
``w1 = 1``.  ``c_w`` remains inside the phase-field functional and must not be
folded into ``w1`` a second time.

Matching these units is necessary for scale transfer, but it is not a road
validation.  Geometry ratios, load shape, fatigue threshold, constitutive
family, environment, and observation semantics must also match or be
identified from data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Any, Dict, Mapping, Optional


_CW = {"AT1": 8.0 / 3.0, "AT2": 2.0}


def _positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


@dataclass(frozen=True)
class PhaseFieldScaling:
    """Dimensional material, geometry, load, and discretization contract.

    The default physical units are MPa, mm, and N/mm.  This is a unit system,
    not a material assumption: any consistent stress-length system works.

    ``alpha_T_phys`` is optional because it is a fatigue parameter that must be
    calibrated rather than inferred from ``E`` and ``G_c`` alone.
    """

    E_phys: float
    nu_phys: float
    G_c_phys: float
    ell_phys: float
    L_phys: float
    H_phys: float
    a0_phys: float
    u_max_phys: float
    alpha_T_phys: Optional[float] = None
    mesh_h_phys: Optional[float] = None
    residual_stiffness: float = 0.0
    R_ratio: float = 0.0
    pff_model: str = "AT1"
    plane_condition: str = "plane_strain"
    energy_split: str = "amor"
    boundary_condition: str = "sent_reverse_bc"
    geometry_form: str = "homogeneous_sent_square"
    load_form: str = "cyclic_displacement"
    geometry_load_ratios: tuple[tuple[str, Optional[float]], ...] = ()
    material_label: str = "unspecified"
    evidence_class: str = "illustrative"

    def __post_init__(self) -> None:
        for name in ("E_phys", "G_c_phys", "ell_phys", "L_phys", "H_phys"):
            _positive(name, float(getattr(self, name)))
        if not 0 <= self.a0_phys <= self.L_phys:
            raise ValueError("a0_phys must lie in [0, L_phys]")
        if not -1.0 <= self.R_ratio <= 1.0:
            raise ValueError("R_ratio must lie in [-1, 1]")
        if not -1.0 < self.nu_phys < 0.5:
            raise ValueError("nu_phys must lie in (-1, 0.5)")
        if self.alpha_T_phys is not None:
            _positive("alpha_T_phys", self.alpha_T_phys)
        if self.mesh_h_phys is not None:
            _positive("mesh_h_phys", self.mesh_h_phys)
        if self.residual_stiffness < 0:
            raise ValueError("residual_stiffness cannot be negative")
        if self.pff_model not in _CW:
            raise ValueError(f"pff_model must be one of {sorted(_CW)}")
        if self.plane_condition not in {"plane_stress", "plane_strain", "3d"}:
            raise ValueError("plane_condition must be plane_stress, plane_strain, or 3d")
        ratio_names = [name for name, _ in self.geometry_load_ratios]
        if len(set(ratio_names)) != len(ratio_names):
            raise ValueError("geometry_load_ratios names must be unique")

    @property
    def c_w(self) -> float:
        return _CW[self.pff_model]

    @property
    def psi_ref(self) -> float:
        """Reference energy density, ``G_c / ell``."""
        return self.G_c_phys / self.ell_phys

    @property
    def sigma_ref(self) -> float:
        """Reference stress implied by the code normalization."""
        return sqrt(self.E_phys * self.psi_ref)

    @property
    def strain_ref(self) -> float:
        return self.sigma_ref / self.E_phys

    @property
    def u_ref(self) -> float:
        return self.L_phys * self.strain_ref

    @property
    def w1_phys(self) -> float:
        """Code parameter in physical units: exactly ``G_c / ell``."""
        return self.psi_ref

    @property
    def mat_E_norm(self) -> float:
        return 1.0

    @property
    def mat_nu_norm(self) -> float:
        return self.nu_phys

    @property
    def w1_norm(self) -> float:
        return self.w1_phys / self.psi_ref

    @property
    def G_c_over_E_ell(self) -> float:
        """Fracture-energy-density ratio ``G_c / (E ell)``."""
        return self.G_c_phys / (self.E_phys * self.ell_phys)

    @property
    def l0_norm(self) -> float:
        return self.ell_phys / self.L_phys

    @property
    def H_norm(self) -> float:
        return self.H_phys / self.L_phys

    @property
    def a0_norm(self) -> float:
        return self.a0_phys / self.L_phys

    @property
    def u_max_norm(self) -> float:
        return self.u_max_phys / self.u_ref

    @property
    def load_energy_ratio(self) -> float:
        """``E (u/L)^2 / (G_c/ell)``; equals ``u_max_norm**2``."""
        return self.u_max_norm**2

    @property
    def alpha_T_norm(self) -> Optional[float]:
        if self.alpha_T_phys is None:
            return None
        return self.alpha_T_phys / self.psi_ref

    @property
    def h_over_ell(self) -> Optional[float]:
        if self.mesh_h_phys is None:
            return None
        return self.mesh_h_phys / self.ell_phys

    @property
    def ell_over_h(self) -> Optional[float]:
        if self.mesh_h_phys is None:
            return None
        return self.ell_phys / self.mesh_h_phys

    def normalized_groups(self) -> Dict[str, Any]:
        """Return groups that must be compared before a scale-transfer claim."""
        return {
            "mat_E": self.mat_E_norm,
            "nu": self.mat_nu_norm,
            "w1": self.w1_norm,
            "w1_norm": self.w1_norm,
            "G_c_over_E_ell": self.G_c_over_E_ell,
            "ell_over_L": self.l0_norm,
            "H_over_L": self.H_norm,
            "a0_over_L": self.a0_norm,
            "u_max_over_u_ref": self.u_max_norm,
            "load_energy_ratio": self.load_energy_ratio,
            "E_uL2_over_w1": self.load_energy_ratio,
            "alpha_T_over_psi_ref": self.alpha_T_norm,
            "alpha_T_over_w1": self.alpha_T_norm,
            "h_over_ell": self.h_over_ell,
            "eta": self.residual_stiffness,
            "R_ratio": self.R_ratio,
            "pff_model": self.pff_model,
            "plane_condition": self.plane_condition,
            "energy_split": self.energy_split,
            "boundary_condition": self.boundary_condition,
            "geometry_form": self.geometry_form,
            "load_form": self.load_form,
            "geometry_load_ratios": dict(self.geometry_load_ratios),
        }

    def dimensional_scales(self) -> Dict[str, float]:
        return {
            "L_ref": self.L_phys,
            "psi_ref": self.psi_ref,
            "sigma_ref": self.sigma_ref,
            "strain_ref": self.strain_ref,
            "u_ref": self.u_ref,
        }

    def to_contract(self) -> Dict[str, Any]:
        return {
            "physical": asdict(self),
            "scales": self.dimensional_scales(),
            "dimensionless": self.normalized_groups(),
            "claim_boundary": {
                "dimensional_similarity_only": True,
                "road_calibrated": False,
                "cycle_to_traffic_mapping_available": False,
            },
        }

    @classmethod
    def from_dimensionless_toy(
        cls,
        *,
        E_phys: float,
        G_c_phys: float,
        ell_phys: float,
        L_phys: float,
        nu: float = 0.3,
        ell_over_L: float = 0.01,
        H_over_L: float = 1.0,
        a0_over_L: float = 0.5,
        u_max_norm: float = 0.12,
        alpha_T_norm: float = 0.5,
        h_over_ell: Optional[float] = None,
        **kwargs: Any,
    ) -> "PhaseFieldScaling":
        """Create one physical realization of a dimensionless toy problem.

        ``ell_phys`` and ``L_phys`` must already satisfy ``ell_over_L``.  This
        explicit redundancy catches accidental coordinate-only rescaling.
        """
        ratio = ell_phys / L_phys
        if abs(ratio - ell_over_L) > 1e-10 * max(1.0, abs(ell_over_L)):
            raise ValueError(
                f"ell_phys/L_phys={ratio:g} does not match ell_over_L={ell_over_L:g}"
            )
        psi_ref = G_c_phys / ell_phys
        u_ref = L_phys * sqrt(psi_ref / E_phys)
        mesh_h = None if h_over_ell is None else h_over_ell * ell_phys
        return cls(
            E_phys=E_phys,
            nu_phys=nu,
            G_c_phys=G_c_phys,
            ell_phys=ell_phys,
            L_phys=L_phys,
            H_phys=H_over_L * L_phys,
            a0_phys=a0_over_L * L_phys,
            u_max_phys=u_max_norm * u_ref,
            alpha_T_phys=alpha_T_norm * psi_ref,
            mesh_h_phys=mesh_h,
            **kwargs,
        )

    def disp_for_stress_intact(self, sigma_target_phys: float) -> float:
        """Normalized displacement under an intact uniform-bar assumption.

        This is not a calibrated cracked-geometry nominal stress.
        """
        u_phys = (sigma_target_phys / self.E_phys) * self.H_phys
        return u_phys / self.u_ref

    disp_for_stress = disp_for_stress_intact

    def disp_phys_to_norm(self, value: float) -> float:
        return value / self.u_ref

    def disp_norm_to_phys(self, value: float) -> float:
        return value * self.u_ref

    def stress_norm_to_phys(self, value: float) -> float:
        return value * self.sigma_ref

    def psi_norm_to_phys(self, value: float) -> float:
        return value * self.psi_ref


_PI_TRANSFER_KEYS = (
    "ell_over_L",
    "h_over_ell",
    "G_c_over_E_ell",
    "alpha_T_over_w1",
    "E_uL2_over_w1",
    "nu",
    "eta",
    "R_ratio",
    "pff_model",
    "plane_condition",
    "energy_split",
    "boundary_condition",
    "geometry_form",
    "load_form",
)


def audit_pi_transfer(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    relative_tolerance: float = 0.01,
    absolute_tolerance: float = 1e-12,
) -> list[Dict[str, Any]]:
    """Classify canonical Pi groups as matched, mismatched, or unobservable.

    ``geometry_load_ratios`` is expanded into one row per declared ratio. A
    missing value is never silently treated as a match; it is explicitly
    labelled ``unobservable``.
    """
    if relative_tolerance < 0 or absolute_tolerance < 0:
        raise ValueError("audit tolerances cannot be negative")

    rows: list[Dict[str, Any]] = []

    def append_row(group: str, ref: Any, value: Any, category: str) -> None:
        ratio = None
        if ref is None or value is None:
            status = "unobservable"
        elif isinstance(ref, (int, float)) and isinstance(value, (int, float)):
            scale = max(abs(float(ref)), abs(float(value)), absolute_tolerance)
            delta = abs(float(value) - float(ref))
            status = (
                "matched"
                if delta <= absolute_tolerance + relative_tolerance * scale
                else "mismatched"
            )
            if abs(float(ref)) > absolute_tolerance:
                ratio = float(value) / float(ref)
        else:
            status = "matched" if value == ref else "mismatched"
        rows.append(
            {
                "group": group,
                "category": category,
                "reference": ref,
                "candidate": value,
                "candidate_over_reference": ratio,
                "status": status,
            }
        )

    numeric = {
        "ell_over_L",
        "h_over_ell",
        "G_c_over_E_ell",
        "alpha_T_over_w1",
        "E_uL2_over_w1",
        "nu",
        "eta",
        "R_ratio",
    }
    for key in _PI_TRANSFER_KEYS:
        append_row(
            key,
            reference.get(key),
            candidate.get(key),
            "buckingham_pi" if key in numeric else "model_form",
        )

    ref_ratios = reference.get("geometry_load_ratios") or {}
    cand_ratios = candidate.get("geometry_load_ratios") or {}
    for key in sorted(set(ref_ratios) | set(cand_ratios)):
        append_row(
            f"geometry_load_ratio:{key}",
            ref_ratios.get(key),
            cand_ratios.get(key),
            "geometry_load_ratio",
        )
    return rows


@dataclass(frozen=True)
class PCCScaling(PhaseFieldScaling):
    """Backward-compatible PCC convenience wrapper.

    The May 2026 implementation incorrectly used ``w1 = c_w G_c / ell``.
    This class now follows the energy implementation and config contract:
    ``w1 = G_c / ell`` and therefore ``w1_norm = 1``.
    """

    ft_phys: float = 3.0
    W_phys: Optional[float] = None

    def __post_init__(self) -> None:
        if self.W_phys is not None and abs(self.W_phys - self.L_phys) > 1e-12:
            raise ValueError("W_phys and L_phys must match")
        super().__post_init__()

    @property
    def G_f_phys(self) -> float:
        return self.G_c_phys

    @property
    def W_norm(self) -> float:
        return 1.0

    @property
    def G_c_norm(self) -> float:
        return self.G_c_phys / (self.sigma_ref * self.L_phys)

    @classmethod
    def baktheer_default(cls, pff_model: str = "AT1") -> "PCCScaling":
        E = 30_000.0
        G_c = 0.10
        ell = 2.0
        L = 100.0
        H = 100.0
        ft = 3.0
        sigma_ref = sqrt(E * G_c / ell)
        u_ref = L * sigma_ref / E
        u_phys = (0.75 * ft / E) * H
        return cls(
            E_phys=E,
            nu_phys=0.18,
            G_c_phys=G_c,
            ell_phys=ell,
            L_phys=L,
            H_phys=H,
            a0_phys=50.0,
            u_max_phys=u_phys,
            alpha_T_phys=5.0,
            mesh_h_phys=ell / 3.0,
            pff_model=pff_model,
            plane_condition="plane_strain",
            material_label="PCC illustrative legacy preset",
            evidence_class="literature-derived-unverified",
            ft_phys=ft,
            W_phys=L,
        )

    def summary(self) -> str:
        return (
            f"PCC Scaling Summary ({self.pff_model})\n"
            f"  Physical: E={self.E_phys:g} MPa, nu={self.nu_phys:g}, "
            f"G_c={self.G_c_phys:g} N/mm, ell={self.ell_phys:g} mm\n"
            f"  Scales: psi_ref={self.psi_ref:.6g} MPa, "
            f"sigma_ref={self.sigma_ref:.6g} MPa, u_ref={self.u_ref:.6g} mm\n"
            f"  PIDL: E={self.mat_E_norm:g}, w1={self.w1_norm:g}, "
            f"ell/L={self.l0_norm:g}, alpha_T={self.alpha_T_norm:g}, "
            f"u_max={self.u_max_norm:.6g}\n"
            "  Label: dimensional scaling only; not a road or fatigue-life validation"
        )


if __name__ == "__main__":
    print(PCCScaling.baktheer_default().summary())
