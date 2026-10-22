"""Narrow certificate for an exact rigid-translation AMOR roundoff artefact.

Source: GRIPHFiTH 862992a60edc7f59335365beacb5c71fc8592a7a,
Modules/fem/assembly/equilibrium/amor.f90:125-152. The source forms
B.T @ (Cplus @ B), then u.T @ (K @ u), rather than a strain quadratic.
Only the fixed E=1, nu=0.3, plane-strain, eta=0 source family is supported.
The caller must independently bind that family and the raw payload identity.

This does not alter arrays, qualify equilibrium, or admit arbitrary small
negative energies. Exact constant nodal displacement and derivative partition
of unity prove zero strain. A source-operation error bound must also cover H.
Bounds use exact rational arithmetic, gamma_(2*n) for an n-term dot product,
and an absolute half-smallest-subnormal allowance per rounded operation.
Assumptions: IEEE binary64 round-to-nearest elementary operations, no overflow;
FMA/reassociation with no more operations is covered. No approximate reciprocal
or other non-IEEE fast-math transformations are certified.
"""
from __future__ import annotations

import math
from fractions import Fraction as F
import numpy as np

PRODUCER_COMMIT = "862992a60edc7f59335365beacb5c71fc8592a7a"
_U = F(1, 2**53)
_ETA = F(1, 2**1075)
_MAX = F.from_float(float(np.finfo(np.float64).max))
_ZERO = (F(0), F(0))


def _gamma(n):
    return n * _U / (1 - n * _U)


def _zeta(n):
    return n * _ETA / (1 - n * _U)


def _point(x):
    q = F.from_float(float(x))
    return q, q


def _abs(a):
    return max(abs(a[0]), abs(a[1]))


def _checked(a):
    if max(abs(a[0]), abs(a[1])) > _MAX:
        raise ValueError("source operation could overflow binary64")
    return a


def _mul_exact(a, b):
    q = [x*y for x in a for y in b]
    return min(q), max(q)


def _round(a):
    # |fl(x)-x| <= u*|x| + half-smallest-subnormal, including underflow.
    e = _U * _abs(a) + _ETA
    return _checked((a[0]-e, a[1]+e))


def _add(a, b):
    return _round((a[0]+b[0], a[1]+b[1]))


def _neg(a):
    return -a[1], -a[0]


def _mul(a, b):
    return _round(_mul_exact(a, b))


def _div(a, b):
    if b[0] <= 0 <= b[1]:
        raise ValueError("source divisor interval includes zero")
    return _round(_mul_exact(a, (1/b[1], 1/b[0])))


def _dot(a, b, *, rounded=True):
    terms = [_mul_exact(x, y) for x, y in zip(a, b)]
    low, high = sum(x[0] for x in terms), sum(x[1] for x in terms)
    if rounded:
        # n products + at most n additions; independent of reduction order.
        n = 2*len(terms)
        absolute_sum = sum(_abs(x) for x in terms)
        # Every product and every possible partial sum must be representable;
        # cancellation in the final result cannot hide intermediate overflow.
        if (1+_gamma(n))*absolute_sum + _zeta(n) > _MAX:
            raise ValueError("source dot product could overflow binary64")
        error = _gamma(n)*absolute_sum + _zeta(n)
        low, high = low-error, high+error
    return _checked((low, high))


def _up(x):
    """Outward conversion of a nonnegative exact upper bound to binary64."""
    value = float(x)
    if not math.isfinite(value):
        raise ValueError("certificate bound is not finite")
    if F.from_float(value) < x:
        value = math.nextafter(value, math.inf)
    return value


def _down(x):
    value = float(x)
    if not math.isfinite(value):
        raise ValueError("certificate bound is not finite")
    if F.from_float(value) > x:
        value = math.nextafter(value, -math.inf)
    return value


def _absolute_matmul(a, b):
    """Enclose a rounded product using nonnegative absolute input bounds."""
    n = 2*len(b)
    answer = []
    for row in a:
        output = []
        for j in range(len(b[0])):
            upper = (1+_gamma(n))*sum(row[k]*b[k][j] for k in range(len(b))) + _zeta(n)
            if upper > _MAX:
                raise ValueError("source quadratic intermediate could overflow binary64")
            output.append(upper)
        answer.append(output)
    return answer


def _array(value, shape, name):
    a = np.asarray(value)
    if a.dtype != np.float64 or a.shape != shape or not np.isfinite(a).all():
        raise ValueError(f"{name} must be finite float64 with shape {shape}")
    return a


def _material_branches():
    # Exact source elastic_stiffness_matrix.m:27-30 and material_characteristic
    # .m:54-58. All construction arithmetic is enclosed, not just nominal C.
    one, two = _point(1.), _point(2.)
    nu = _point(.3)
    one_plus = _add(one, nu)
    one_minus_two = _add(one, _neg(_mul(two, nu)))
    factor = _div(one, _mul(one_plus, one_minus_two))
    diag = _mul(factor, _add(one, _neg(nu)))
    off = _mul(factor, nu)
    shear = _mul(factor, _div(one_minus_two, two))
    tensile = [[diag, off, _ZERO], [off, diag, _ZERO], [_ZERO, _ZERO, shear]]
    G = _div(one, _mul(two, one_plus))
    twice_G = _mul(two, G)
    # Native constants I_dev are evaluated as binary64 divisions.
    third = _div(one, _point(3.))
    two_thirds = _div(two, _point(3.))
    devdiag = _mul(twice_G, two_thirds)
    devoff = _mul(twice_G, _neg(third))
    devshear = _mul(twice_G, _point(.5))
    compression = [[devdiag, devoff, _ZERO], [devoff, devdiag, _ZERO],
                   [_ZERO, _ZERO, devshear]]
    return {"trace_nonnegative": tensile, "trace_negative": compression}


def certify_negative_energy(xy, u, d, native_shape, native_derivative, raw_H, raw_q):
    """Return a JSON-compatible certificate, or raise ValueError.

    Inputs are one element/GP: xy,u [4,2], d,N [4], dN/dxi [2,4].
    Canonical H=q=0 is authorized only by this narrow rigid-translation proof.
    Payload/source hashes and fixed material/boundary family remain caller checks.
    """
    xy = _array(xy, (4, 2), "xy")
    u = _array(u, (4, 2), "u")
    d = _array(d, (4,), "d")
    N = _array(native_shape, (4,), "native_shape")
    D = _array(native_derivative, (2, 4), "native_derivative")
    H = float(_array(raw_H, (), "raw_H"))
    q = float(_array(raw_q, (), "raw_q"))
    if not H < 0 or H != q:
        raise ValueError("certificate requires raw_H == raw_q < 0")
    if not np.all(d == 0):
        raise ValueError("certificate requires exactly zero nodal damage")
    bits = u.view(np.uint64)
    if not np.array_equal(bits, np.broadcast_to(bits[0], bits.shape)):
        raise ValueError("certificate requires bitwise constant nodal displacement")
    if np.unique(xy, axis=0).shape[0] != 4:
        raise ValueError("Q4 coordinates repeat a node")
    fd = [[F.from_float(float(x)) for x in row] for row in D]
    if any(sum(row) != 0 for row in fd):
        raise ValueError("native derivatives lack exact partition of unity")
    a,b,c,e = fd[0][1],fd[0][2],fd[1][3],fd[1][2]
    if (fd != [[-a,a,b,-b],[-c,-e,e,c]] or
            min(a,b,c,e) <= 0 or a+b != F(1,2) or c+e != F(1,2)):
        raise ValueError("native derivative is not an interior Q4 basis")
    expected_N = [4*a*c,4*a*e,4*b*e,4*b*c]
    # A basis consistency check, not the energy acceptance tolerance. Four
    # derivative/shape factors and their products need fewer than 16 roundings.
    if any(abs(F.from_float(float(n))-target) > _gamma(16)*abs(target)
           for n,target in zip(N,expected_N)):
        raise ValueError("native shape and derivative are inconsistent")

    DI = [[_point(x) for x in row] for row in D]
    XI = [[_point(x) for x in row] for row in xy]
    J = [[_dot(DI[i], [XI[k][j] for k in range(4)]) for j in range(2)]
         for i in range(2)]
    det = _add(_mul(J[0][0],J[1][1]), _neg(_mul(J[0][1],J[1][0])))
    # Source m22inv:67-80 declines |det|<=1e-10; require positive orientation
    # for the ENTIRE rounded determinant enclosure, not a recomputed center.
    if det[0] <= F.from_float(1e-10):
        raise ValueError("native Q4 determinant interval is nonpositive or below source inverse threshold")
    inv = [[_div(J[1][1],det),_div(_neg(J[0][1]),det)],
           [_div(_neg(J[1][0]),det),_div(J[0][0],det)]]
    grad = [[_dot(inv[i], [DI[k][j] for k in range(2)]) for j in range(4)]
            for i in range(2)]
    B = [grad[0]+[_ZERO]*4, [_ZERO]*4+grad[1], grad[1]+grad[0]]
    # Source displacement ordering is [ux1..ux4, uy1..uy4].
    uv = [_point(x) for x in np.r_[u[:,0],u[:,1]]]
    ua = [_abs(x) for x in uv]
    ba = [[_abs(x) for x in row] for row in B]
    strain_abs = [_abs(_dot(row,uv,rounded=False)) for row in B]
    w = [sum(x*y for x,y in zip(row,ua)) for row in ba]
    branches = {}
    bounds = []
    for name,C in _material_branches().items():
        ca = [[_abs(x) for x in row] for row in C]
        # Certify all four source products, including K before multiplication
        # by a possibly tiny u. Bounds also cover every reduction partial sum.
        cb_upper = _absolute_matmul(ca, ba)
        k_upper = _absolute_matmul(list(map(list, zip(*ba))), cb_upper)
        ku_upper = _absolute_matmul(k_upper, [[v] for v in ua])
        _absolute_matmul([ua], ku_upper)
        def quad(v):
            return sum(v[i]*ca[i][j]*v[j] for i in range(3) for j in range(3))/2
        geometry = quad(strain_abs)
        scale = quad(w)
        # CB(3), B.T@CB(3), Ku(8), u.T@Ku(8): 6+6+16+16=44.
        assembly = _gamma(44)*scale
        # Additive underflow terms propagated through those same four dots.
        su = sum(ua)
        k_under = (1+_gamma(6))*_zeta(6)*sum(w)*su + _zeta(6)*su*su
        under = ((1+_gamma(16))*((1+_gamma(16))*k_under +
                 _zeta(16)*su)+_zeta(16))/2 + _ETA
        bound = geometry + assembly + under
        if scale > _MAX or bound > _MAX:
            raise ValueError("source energy operation could overflow")
        bounds.append(bound)
        branches[name] = {"geometry_rounding_bound":_up(geometry),
                          "quadratic_scale":_up(scale),
                          "assembly_rounding_bound":_up(assembly),
                          "absolute_underflow_bound":_up(under),
                          "total_bound":_up(bound),
                          "C_abs_upper":[[_up(x) for x in row] for row in ca]}
    bound = max(bounds)
    if F.from_float(abs(H)) > bound:
        raise ValueError("negative energy exceeds the source-operation roundoff bound")
    return {"schema":"rigid_translation_amor_roundoff_v1",
            "producer_commit":PRODUCER_COMMIT,"raw_H":H,"raw_q":q,
            "raw_H_hex":H.hex(),"raw_q_hex":q.hex(),
            "canonical_H":0.0,"canonical_q":0.0,
            "proof":"bitwise constant nodal displacement; exact derivative row sums zero; invertible Q4; d=0; continuum H=q=0",
            "unit_roundoff":float(_U),"gamma_operation_count":44,
            "gamma44_upper":_up(_gamma(44)),
            "dot_operation_counts":[6,6,16,16],
            "determinant_interval":[_down(det[0]),_up(det[1])],
            "absolute_bound":_up(bound),"ratio":float(F.from_float(abs(H))/bound),
            "branches":branches,
            "arithmetic_assumptions":"IEEE binary64 round-to-nearest; gamma bounds include absolute gradual-underflow terms; no overflow or approximate reciprocal",
            "scope":"fixed E=1, nu=0.3, plane-strain AMOR eta=0; caller binds source and payload; raw arrays unchanged"}
