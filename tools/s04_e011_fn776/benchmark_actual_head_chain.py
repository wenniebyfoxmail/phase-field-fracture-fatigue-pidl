"""CPU-only synthetic consistency check for the canonical actual-head UV mapping.

This reads no scientific payload and is not part of the producer code bundle.
"""
from pathlib import Path
import json
import math
import sys


def main():
    import torch
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / 'source'), str(root / 'SENS_tensile')]
    from network import NeuralNet
    from run_native_q4_one_step_matrix import make_field
    from worker import actual_head_uv

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1)
    torch.use_deterministic_algorithms(True)
    device = torch.device('cpu')
    net = NeuralNet(2, 3, 8, 400, 'TrainableReLU', 1.).double()
    state = {name: value.detach().clone() for name, value in net.state_dict().items()}
    field = make_field(state, device, .11999988, 'legacy_nonsmooth')
    field.net = field.net.double()
    field.domain_extrema = field.domain_extrema.double()
    field.lmbda = torch.tensor([.11999988], dtype=torch.float64)
    field.theta = torch.tensor([math.pi / 2], dtype=torch.float64)
    for parameter in field.net.parameters():
        parameter.requires_grad_(False)
    original = {name: value.detach().clone() for name, value in field.net.state_dict().items()}
    x = torch.rand((17, 2), dtype=torch.float64) - .5
    with torch.no_grad():
        features = field.net.encode(x)
    rank, size = 388, 776
    transform = torch.randn((401, rank), dtype=torch.float64) * 1e-5

    def materialized(z):
        delta = transform @ z.reshape(rank, 2)
        with torch.no_grad():
            field.net.output_layer.weight[:2].copy_(original['output_layer.weight'][:2] + delta[:-1].T)
            field.net.output_layer.bias[:2].copy_(original['output_layer.bias'][:2] + delta[-1])
            return field.fieldCalculation(x)

    records = []
    for name, z0 in (('zero', torch.zeros(size, dtype=torch.float64)),
                     ('nonzero', torch.randn(size, dtype=torch.float64) * 1e-6)):
        raw_u, raw_v, raw_d = materialized(z0)
        canonical_u, canonical_v = actual_head_uv(torch, field, original, features, x, transform, rank, z0)
        z = z0.detach().clone().requires_grad_(True)
        u, v = actual_head_uv(torch, field, original, features, x, transform, rank, z)
        energy = .5 * (u.square() + 2.0 * v.square()).sum()
        direct, force_u, force_v = torch.autograd.grad(energy, (z, u, v))
        canonical_force = torch.cat((force_u, force_v)).detach()
        raw_force = torch.cat((raw_u.detach(), 2.0 * raw_v.detach()))
        zv = z0.detach().clone().requires_grad_(True)
        vu, vv = actual_head_uv(torch, field, original, features, x, transform, rank, zv)
        pulled = torch.autograd.grad((vu * raw_force[:len(x)]).sum() +
                                     (vv * raw_force[len(x):]).sum(), zv)[0]
        field_error = float(torch.max(torch.abs(torch.stack((raw_u-canonical_u, raw_v-canonical_v)))))
        gradient_error = float(torch.max(torch.abs(direct-pulled)))
        force_error = float(torch.max(torch.abs(raw_force-canonical_force)))
        damage_error = float(torch.max(torch.abs(raw_d-field.fieldCalculation(x)[2])))
        records.append(dict(name=name, field_maxabs=field_error, gradient_maxabs=gradient_error,
                            force_maxabs=force_error, damage_maxabs=damage_error))
        assert field_error <= 1e-12
        assert gradient_error <= 1e-12
        assert force_error <= 1e-12
        assert damage_error == 0.0
    print(json.dumps(dict(status='SYNTHETIC_ACTUAL_HEAD_CHAIN_PASS', records=records,
                          payload_accessed=False, remote_accessed=False), indent=2))


if __name__ == '__main__':
    main()
