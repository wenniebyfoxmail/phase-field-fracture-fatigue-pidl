"""U01: five diagnostic column scalings only; never candidate-field arithmetic.

Shared evaluation is not independent multiplication evidence. The artificial
Fraction interval oracle in test_aa2024_underflow.py supplies that check.
No error suppression, exception retry, decomposition or file/data reads.
"""
import ctypes
import hashlib
import json
import struct
import sys

import numpy as np

SITES = ('producer.full_svd', 'producer.retained_left', 'producer.retained_right',
         'verifier.retained_left', 'verifier.retained_right')
ATOL = {'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}
RTOL = 1e-12
RELATIVE_DISPATCH = float.fromhex('0x1p-900')
SIGN = 1 << 63
FRACTION = (1 << 52)-1
MAGNITUDE = SIGN-1
_round_mode = None


class ArithmeticContract(ValueError):
    pass


def need(ok, label):
    if not ok:
        raise ArithmeticContract(label)


def model_state():
    """Read, never alter, the supported platform's floating-point environment."""
    global _round_mode
    need(sys.platform in ('darwin', 'linux') and sys.byteorder in ('little', 'big'), 'unsupported float platform')
    need((sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp,
          sys.float_info.min_exp, sys.float_info.rounds) == (2, 53, 1024, -1021, 1), 'binary64 model')
    need(np.dtype('float64').itemsize == struct.calcsize('d') == 8, 'binary64 layout')
    need(np.geterr() == dict(divide='raise', over='raise', under='raise', invalid='raise'), 'all raise required')
    if _round_mode is None:
        # FE_TONEAREST is 0 on the supported Darwin/Linux C ABIs. No setter.
        fn = ctypes.CDLL(None).fegetround
        fn.argtypes, fn.restype = [], ctypes.c_int
        _round_mode = fn
    need(_round_mode() == 0, 'FE_TONEAREST required')


def bits(value):
    return struct.unpack('>Q', struct.pack('>d', float(value)))[0]


def check_model():
    """Executable only after approval; normal outputs and exact subnormal add."""
    model_state()
    tiny = np.array([1], dtype=np.uint64).view(np.float64)
    need(bits(np.add(tiny, tiny)[0]) == 2, 'gradual exact subnormal addition')
    need(bits(np.multiply(tiny, np.array([float.fromhex('0x1p52')]))[0]) == 1 << 52,
         'subnormal input normal output')
    one = np.array([1.], dtype=np.float64)
    need(bits(np.add(one, float.fromhex('0x1p-53'))[0]) == bits(1.), 'nearest-even lower tie')
    above = np.array([struct.unpack('>d', struct.pack('>Q', bits(1.)+1))[0]])
    need(bits(np.add(above, float.fromhex('0x1p-53'))[0]) == bits(1.)+2, 'nearest-even upper tie')
    return 'binary64 RN-even probes; not a general hardware certification'


def pack_quantum(n, negative):
    """N=2**53 is a pack-only boundary, unreachable for dispatched input pairs."""
    need(type(n) is int and type(negative) is bool and 0 <= n <= 1 << 53, 'quantum pack range/type')
    return struct.unpack('>d', struct.pack('>Q', n | (SIGN if negative else 0)))[0]


def _decode(raw):
    field, frac = (raw >> 52) & 2047, raw & FRACTION
    return ((1 << 52)+frac, field-1075) if field else (frac, -1074)


def integer_product(x_bits, t_bits):
    """Called only for finite nonzero preclassified conservative inputs."""
    mx, ex = _decode(x_bits); mt, et = _decode(t_bits)
    need(mx > 0 and mt > 0, 'integer nonzero factors')
    p, h = mx*mt, ex+et+1074
    numerator, denominator = (p << h, 1) if h >= 0 else (p, 1 << -h)
    quotient, remainder = divmod(numerator, denominator)
    up = 2*remainder > denominator or (2*remainder == denominator and quotient % 2 == 1)
    n = quotient+int(up)
    need(n <= (1 << 53)-2, 'unreachable conservative product')
    negative = bool((x_bits ^ t_bits) & SIGN)
    result = pack_quantum(n, negative)
    direction = 'exact' if remainder == 0 else ('larger_magnitude' if up else 'smaller_magnitude')
    certificate = dict(x_bits=f'{x_bits:016x}', t_bits=f'{t_bits:016x}', out_bits=f'{bits(result):016x}',
                       P=str(p), h=h, numerator=str(numerator), denominator=str(denominator),
                       quotient=str(quotient), remainder=str(remainder), N=str(n),
                       magnitude_rounding=direction, error_bound='2^-1075')
    # Integer-only witness consistency; independent nearest-interval tests are separate.
    need(numerator == quotient*denominator+remainder and 0 <= remainder < denominator,
         'integer certificate division')
    need(bits(result) == n | (SIGN if negative else 0), 'integer certificate output')
    return result, certificate


def column_reference(factor, singular, site, records, budget=None):
    """Fresh read-only float64 factor[:,j]*singular[j], at exactly five sites."""
    model_state()
    need(site in SITES and isinstance(records, list), 'fixed reference site')
    need(not any(r['site'] == site for r in records), 'reference site used twice')
    need(isinstance(factor, np.ndarray) and isinstance(singular, np.ndarray) and
         factor.dtype == singular.dtype == np.dtype('float64') and
         factor.dtype.isnative and singular.dtype.isnative, 'native float64 factors')
    need(factor.ndim == 2 and singular.ndim == 1 and factor.shape[1] == len(singular) and
         factor.size > 0 and np.isfinite(factor).all() and np.isfinite(singular).all(), 'column shape/finite')
    if budget is not None:
        budget.check()
    before = [hashlib.sha256(v.tobytes()).hexdigest() for v in (factor, singular)]
    xb, tb = factor.view(np.uint64), np.broadcast_to(singular, factor.shape).view(np.uint64)
    zero = ((xb & MAGNITUDE) == 0) | ((tb & MAGNITUDE) == 0)
    _, xe = np.frexp(factor); _, te = np.frexp(singular)
    ordinary = ~zero & (xe+te[None, :] >= -1020)
    conservative = ~zero & ~ordinary
    out = np.empty(factor.shape, dtype=np.float64)
    # Never multiply the full array before selecting. No catch-and-retry path.
    right = np.broadcast_to(singular, factor.shape)
    out[ordinary] = np.multiply(factor[ordinary], right[ordinary])
    out.view(np.uint64)[zero] = (xb[zero] ^ tb[zero]) & SIGN
    certificates = []
    for ordinal, index in enumerate(np.argwhere(conservative)):
        if budget is not None and ordinal % 64 == 0:
            budget.check()
        i, j = (int(k) for k in index)
        value, certificate = integer_product(int(xb[i, j]), int(tb[i, j]))
        out[i, j] = value
        certificates.append(dict(index=[i, j], **certificate))
    need(np.isfinite(out).all(), 'finite diagnostic reference')
    need(before == [hashlib.sha256(v.tobytes()).hexdigest() for v in (factor, singular)], 'input bits changed')
    ob = out.view(np.uint64) & MAGNITUDE
    records.append(dict(site=site, shape=list(factor.shape), input_sha256=before,
                        ordinary_count=int(np.count_nonzero(ordinary)), zero_operand_count=int(np.count_nonzero(zero)),
                        integer_branch_count=len(certificates),
                        subnormal_output_count=int(np.count_nonzero((ob > 0) & (ob < 1 << 52))),
                        nonzero_product_rounded_zero_count=int(np.count_nonzero(conservative & (ob == 0))),
                        certificates=certificates))
    need(not np.shares_memory(out, factor) and not np.shares_memory(out, singular), 'reference aliases input')
    out.setflags(write=False)
    if budget is not None:
        budget.check()
    return out


def comparison(a, ref, kind='vector'):
    """All-component original RN64 inequality, with a first-failure witness."""
    model_state()
    need(kind in ATOL, 'only frozen tolerance kinds')
    a, ref = np.asarray(a), np.asarray(ref)
    need(a.dtype == ref.dtype == np.dtype('float64') and a.shape == ref.shape and
         a.size > 0 and np.isfinite(a).all() and np.isfinite(ref).all(), 'comparison dtype/finite/shape')
    d = np.abs(a-ref)
    magnitude = np.abs(ref)
    denom = np.full(ref.shape, ATOL[kind])
    ordinary = magnitude >= RELATIVE_DISPATCH
    denom[ordinary] = ATOL[kind]+RTOL*magnitude[ordinary]
    need(np.isfinite(d).all() and np.isfinite(denom).all() and np.all(denom > 0), 'comparison finite limits')
    passed = d <= denom
    failed = np.flatnonzero(~passed)
    def witness(flat):
        index = np.unravel_index(int(flat), a.shape)
        return dict(index=[int(i) for i in index], delta=float(d[index]), limit=float(denom[index]),
                    candidate=float(a[index]), reference=float(ref[index]))
    return dict(all_pass=bool(np.all(passed)), kind=kind, rtol=RTOL, atol=ATOL[kind], components=int(a.size),
                max_absolute_delta=witness(np.argmax(d)),
                first_failure=witness(failed[0]) if len(failed) else None)


def failure_text(label, summary):
    return label+' '+json.dumps(summary['first_failure'], allow_nan=False, sort_keys=True)
