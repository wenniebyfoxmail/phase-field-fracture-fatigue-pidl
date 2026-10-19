"""Hand-authored interface fixtures only. No file/data/model/runtime loader.

This module checks semantics and linear algebra; it is not a predictor, solver,
scientific estimator, or substitute for the owning runner's code review.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Packet:
    domain: str
    group: str
    clock: str
    step: int
    support: str
    reference: str
    role: str
    physical_unit: str | None = None
    phase: str | None = None


def history_contract(packets, origin, expected_role="response"):
    if not packets:
        raise ValueError("empty history")
    if type(origin) is not int or origin < 0:
        raise ValueError("invalid origin clock")
    first = packets[0]
    if first.clock not in {"release_step", "cycle", "load_substep"}:
        raise ValueError("undeclared clock")
    if any(not x for x in (first.domain, first.group, first.support, first.reference)):
        raise ValueError("missing identity or coordinate semantics")
    keys = ("domain", "group", "clock", "support", "reference", "physical_unit", "phase")
    for packet in packets:
        if type(packet.step) is not int or packet.step < 0:
            raise ValueError("invalid observation clock")
        if any(getattr(packet, k) != getattr(first, k) for k in keys):
            raise ValueError("history identity/clock/coordinate mismatch")
        if packet.role != expected_role:
            raise ValueError("mask/response/phase damage are different roles")
        if packet.step > origin:
            raise ValueError("future observation at origin")
        if packet.clock == "cycle" and (not packet.physical_unit or not packet.phase):
            raise ValueError("physical cycle requires unit and phase")
    if [p.step for p in packets] != sorted(set(p.step for p in packets)):
        raise ValueError("history not strictly ordered")
    if packets[-1].step != origin:
        raise ValueError("missing current observation")
    return {"clock": first.clock, "group": first.group,
            "physical_independence": "unknown" if first.physical_unit is None else "declared_only"}


def canonical(q):
    """q: [mean_full2, std_full2, mean_band2, std_band2] -> [g2,r6]."""
    if len(q) != 8 or not all(isfinite(float(x)) for x in q):
        raise ValueError("invalid response summary")
    return list(q[:2]) + list(q[2:4]) + [q[4]-q[0], q[5]-q[1]] + list(q[6:8])


def uncanonical(z):
    if len(z) != 8:
        raise ValueError("invalid canonical dimension")
    return list(z[:4]) + [z[4]+z[0], z[5]+z[1]] + list(z[6:8])


def origin_features(base, summaries, include_history=False):
    """Input-only intervention fixture; fitted residualizer is intentionally absent."""
    if len(base) != 12 or len(summaries) != 3:
        raise ValueError("wrong fixture schema")
    z = [canonical(q) for q in summaries]
    # Keep the exact C_RAW current coordinates; otherwise a new current-only
    # regularization geometry would be confounded with added history.
    current = list(base) + list(summaries[-1])
    if not include_history:
        return current
    return current + [z[i][k]-z[-1][k] for i in (0, 1) for k in range(2, 8)]


def canonical_coefficient(raw_coefficient):
    """beta_z = inverse(T).T beta_raw, where z=T raw, no fitting."""
    if len(raw_coefficient) != 8:
        raise ValueError("wrong coefficient dimension")
    b = list(raw_coefficient)
    return [b[0]+b[4], b[1]+b[5], b[2], b[3], b[4], b[5], b[6], b[7]]


def raw_coefficient(canonical_beta):
    b = list(canonical_beta)
    return [b[0]-b[4], b[1]-b[5], b[2], b[3], b[4], b[5], b[6], b[7]]


def dot(a, b):
    if len(a) != len(b):
        raise ValueError("dot dimensions")
    return sum(x*y for x, y in zip(a, b))


def pulled_penalty(beta_z):
    """||T.T beta_z||^2; production fold standardization must also be pulled back."""
    b = raw_coefficient(beta_z)
    return dot(b, b)


def check_preparation_plan(plan):
    if plan["execution_enabled"] is not False or plan["production_runner"] is not None:
        raise ValueError("preparation cannot enable execution")
    if plan["arms"] != {"C_RAW":20, "H_RAW":36, "C_REL":18,
                        "H_REL":30, "H_INNOV":32, "H_DONOR":32}:
        raise ValueError("designed arms changed")
    if plan["budget"]["gpu_hours"] != 0:
        raise ValueError("not a GPU proposal")
    if plan["data"]["clock"] != "release_step":
        raise ValueError("unverified cycle mapping")
    fits = len(plan["arms"])*19*2*(len(plan["ridge_alphas"])+1)
    if fits != plan["work"]["predictor_solves"]:
        raise ValueError("fit accounting mismatch")
    return {"preparation_only": True, "predictor_solves": fits}
