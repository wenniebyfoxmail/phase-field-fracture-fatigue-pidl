"""S09 diagnostic integral-kernel GNO; no mechanics residual or event input."""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F


def mlp(a, b, c):
    return nn.Sequential(nn.Linear(a, b), nn.GELU(), nn.Linear(b, c))


class IntegralBlock(nn.Module):
    """Low-rank continuous kernel. Never instantiate [edges,width,width]."""
    def __init__(self, width=64, rank=8):
        super().__init__()
        self.a = nn.Linear(width, rank, bias=False)
        self.kernel = mlp(3, 32, rank)
        self.b = nn.Linear(rank, width, bias=False)
        self.local = nn.Linear(width, width)
        self.norm = nn.LayerNorm(width)

    def forward(self, v, edges, relative, weight):
        src, dst = edges
        message = self.a(v)[src] * self.kernel(relative) * weight[:, None]
        aggregate = v.new_zeros((len(v), message.shape[-1]))
        aggregate.index_add_(0, dst, message)
        return v + F.gelu(self.norm(self.local(v) + self.b(aggregate)))


class FractureOperator(nn.Module):
    def __init__(self, state_mean, state_scale, increment_scale, width=64, rank=8):
        super().__init__()
        for name, value in [('state_mean', state_mean), ('state_scale', state_scale),
                            ('increment_scale', increment_scale)]:
            self.register_buffer(name, torch.as_tensor(value, dtype=torch.float32))
        # Three states * three fields, xy + native boundary flag, five path values.
        self.encoder = mlp(17, width, width)
        self.blocks = nn.ModuleList([IntegralBlock(width, rank) for _ in range(2)])
        self.coarse = IntegralBlock(width, rank)
        self.decoder = mlp(3 * width, width, 3)
        # Exactly-zero increment is representable and is the initial baseline.
        nn.init.zeros_(self.decoder[-1].weight)
        nn.init.zeros_(self.decoder[-1].bias)

    def forward(self, history, graph, path):
        if history.shape != (3, len(graph['xy']), 3) or path.shape != (5,):
            raise ValueError('expected history [3,N,3] and full peak-to-peak path [5]')
        h = ((history - self.state_mean) / self.state_scale).permute(1, 0, 2).flatten(1)
        inp = torch.cat([h, graph['xy'], graph['boundary'][:, None],
                         path[None, :].expand(len(h), -1)], -1)
        encoded = self.encoder(inp)
        local = encoded
        for block in self.blocks:
            local = block(local, graph['edges'], graph['relative'], graph['weight'])
        cluster = graph['cluster']
        coarse = local.new_zeros((len(graph['coarse_area']), local.shape[-1]))
        coarse.index_add_(0, cluster, local * graph['area'][:, None])
        coarse = coarse / graph['coarse_area'][:, None]
        coarse = self.coarse(coarse, graph['coarse_edges'], graph['coarse_relative'],
                             graph['coarse_weight'])
        return self.decoder(torch.cat([encoded, local, coarse[cluster]], -1))

    def advance(self, history, graph, path):
        raw = self(history, graph, path)
        return decode(history[-1], raw, self.increment_scale), raw


def decode(current, raw, scale):
    proposal = current + raw * scale
    return torch.stack([torch.maximum(current[:, 0], proposal[:, 0]).clamp(max=1),
                        torch.maximum(current[:, 1], proposal[:, 1]),
                        proposal[:, 2].clamp(min=0)], -1)


def area_loss(prediction, target, scale, area, channel_weights=None):
    error = F.smooth_l1_loss(prediction / scale, target / scale, reduction='none')
    if channel_weights is not None:
        error = error * error.new_tensor(channel_weights)
    return (error.mean(-1) * area).sum() / area.sum()


def one_step_loss(model, history, target, graph, path, channel_weights=None):
    pred, raw = model.advance(history, graph, path)
    # This branch supplies corrective gradients even when projection kills them.
    raw_target = (target - history[-1]) / model.increment_scale
    raw_loss = area_loss(raw, raw_target, torch.ones_like(model.increment_scale), graph['area'], channel_weights)
    state_loss = area_loss(pred, target, model.state_scale, graph['area'], channel_weights)
    return state_loss + raw_loss, pred


def rollout(model, history, graph, path, steps):
    result = []
    for _ in range(steps):
        pred, _ = model.advance(history, graph, path)
        result.append(pred)
        history = torch.cat([history[1:], pred[None]], 0)
    return torch.stack(result)
