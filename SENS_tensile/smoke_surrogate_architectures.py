#!/usr/bin/env python3
"""Small smoke tests for crack-evolution surrogate architectures.

This file is intentionally standalone. It does not import PIDL training code,
does not read or write archives, and does not launch a real training run. The
goal is only to check whether several candidate model families can execute a
forward pass, backpropagate, and fit a tiny synthetic state-transition target.

Models covered:
  - MeshGNN: unstructured node/edge state transition.
  - TinyUNet: grid-to-grid state transition.
  - TinyFNO2D: grid-to-grid spectral operator surrogate.
  - DynamicsNet: low-dimensional state transition.
  - DirectFieldMLP: direct coordinate/action-to-field predictor.
"""
from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import Callable

import torch
import torch.nn as nn
import torch.nn.functional as F


STATE_DIM = 3
ACTION_DIM = 3


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def choose_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    return torch.device(name)


def mlp(sizes: list[int], activation: Callable[[], nn.Module] = nn.GELU) -> nn.Sequential:
    layers: list[nn.Module] = []
    for i in range(len(sizes) - 1):
        layers.append(nn.Linear(sizes[i], sizes[i + 1]))
        if i < len(sizes) - 2:
            layers.append(activation())
    return nn.Sequential(*layers)


def make_coords_grid(batch: int, height: int, width: int, device: torch.device) -> torch.Tensor:
    y = torch.linspace(-0.5, 0.5, height, device=device)
    x = torch.linspace(-0.5, 0.5, width, device=device)
    yy, xx = torch.meshgrid(y, x, indexing="ij")
    coords = torch.stack([xx, yy], dim=0)
    return coords.unsqueeze(0).repeat(batch, 1, 1, 1)


def crack_like_state(
    coords: torch.Tensor,
    action: torch.Tensor,
    time_shift: float = 0.0,
) -> torch.Tensor:
    """Create a small synthetic state {u, d, H} on a grid or point cloud.

    coords can be Bx2xHxW or Nx2. action can be Bx3 or Nx3.
    """
    if coords.ndim == 4:
        x = coords[:, 0:1]
        y = coords[:, 1:2]
        load = action[:, 0].view(-1, 1, 1, 1)
        temp = action[:, 1].view(-1, 1, 1, 1)
        humid = action[:, 2].view(-1, 1, 1, 1)
    elif coords.ndim == 2:
        x = coords[:, 0:1]
        y = coords[:, 1:2]
        load = action[:, 0:1]
        temp = action[:, 1:2]
        humid = action[:, 2:3]
    else:
        raise ValueError(f"Unsupported coords shape: {tuple(coords.shape)}")

    tip = -0.20 + 0.18 * load + 0.03 * temp + time_shift
    corridor = torch.exp(-90.0 * y.pow(2))
    front = torch.sigmoid(18.0 * (x - tip))
    damage = corridor * front
    history = torch.maximum(damage, 0.65 * damage + 0.10 * load + 0.05 * humid)
    ux = load * (y + 0.5) + 0.04 * torch.sin(2.0 * math.pi * x) * (1.0 - damage)
    return torch.cat([ux, damage, history], dim=1 if coords.ndim == 4 else -1)


def make_grid_transition_batch(
    batch: int,
    height: int,
    width: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    coords = make_coords_grid(batch, height, width, device)
    action = torch.rand(batch, ACTION_DIM, device=device)
    state_t = crack_like_state(coords, action, time_shift=0.00)
    state_next = crack_like_state(coords, action, time_shift=0.05)
    action_maps = action[:, :, None, None].expand(-1, -1, height, width)
    return torch.cat([state_t, action_maps], dim=1), state_next


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.GELU(),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TinyUNet(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, width: int = 16) -> None:
        super().__init__()
        self.enc1 = ConvBlock(in_channels, width)
        self.enc2 = ConvBlock(width, width * 2)
        self.bottleneck = ConvBlock(width * 2, width * 4)
        self.up2 = nn.ConvTranspose2d(width * 4, width * 2, kernel_size=2, stride=2)
        self.dec2 = ConvBlock(width * 4, width * 2)
        self.up1 = nn.ConvTranspose2d(width * 2, width, kernel_size=2, stride=2)
        self.dec1 = ConvBlock(width * 2, width)
        self.out = nn.Conv2d(width, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(F.max_pool2d(e1, 2))
        b = self.bottleneck(F.max_pool2d(e2, 2))
        d2 = self.dec2(torch.cat([self.up2(b), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.out(d1)


class SpectralConv2d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, modes: int) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.modes = modes
        scale = 1.0 / (in_channels * out_channels)
        weight = scale * torch.randn(in_channels, out_channels, modes, modes, dtype=torch.cfloat)
        self.weight = nn.Parameter(weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, _, height, width = x.shape
        x_ft = torch.fft.rfft2(x, norm="ortho")
        out_ft = torch.zeros(
            batch,
            self.out_channels,
            height,
            width // 2 + 1,
            dtype=torch.cfloat,
            device=x.device,
        )
        h_modes = min(self.modes, height)
        w_modes = min(self.modes, width // 2 + 1)
        out_ft[:, :, :h_modes, :w_modes] = torch.einsum(
            "bixy,ioxy->boxy",
            x_ft[:, :, :h_modes, :w_modes],
            self.weight[:, :, :h_modes, :w_modes],
        )
        return torch.fft.irfft2(out_ft, s=(height, width), norm="ortho")


class FNOBlock2d(nn.Module):
    def __init__(self, channels: int, modes: int) -> None:
        super().__init__()
        self.spectral = SpectralConv2d(channels, channels, modes)
        self.pointwise = nn.Conv2d(channels, channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.gelu(self.spectral(x) + self.pointwise(x))


class TinyFNO2D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, width: int = 16, modes: int = 6) -> None:
        super().__init__()
        self.lift = nn.Conv2d(in_channels, width, kernel_size=1)
        self.blocks = nn.Sequential(
            FNOBlock2d(width, modes),
            FNOBlock2d(width, modes),
            FNOBlock2d(width, modes),
        )
        self.project = nn.Sequential(
            nn.Conv2d(width, width, kernel_size=1),
            nn.GELU(),
            nn.Conv2d(width, out_channels, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.project(self.blocks(self.lift(x)))


@dataclass
class GraphBatch:
    node_features: torch.Tensor
    edge_index: torch.Tensor
    edge_attr: torch.Tensor
    target: torch.Tensor


def make_graph_batch(side: int, device: torch.device) -> GraphBatch:
    coords_grid = make_coords_grid(1, side, side, device)[0].permute(1, 2, 0).reshape(-1, 2)
    jitter = 0.012 * torch.randn_like(coords_grid)
    coords = coords_grid + jitter
    n_nodes = coords.shape[0]
    action = torch.rand(1, ACTION_DIM, device=device).expand(n_nodes, -1)
    state_t = crack_like_state(coords, action, time_shift=0.00)
    target = crack_like_state(coords, action, time_shift=0.05)

    edges: list[tuple[int, int]] = []
    for row in range(side):
        for col in range(side):
            idx = row * side + col
            if row + 1 < side:
                edges.append((idx, (row + 1) * side + col))
                edges.append(((row + 1) * side + col, idx))
            if col + 1 < side:
                edges.append((idx, row * side + col + 1))
                edges.append((row * side + col + 1, idx))

    edge_index = torch.tensor(edges, dtype=torch.long, device=device).t().contiguous()
    src, dst = edge_index
    edge_attr = coords[dst] - coords[src]
    node_features = torch.cat([coords, state_t, action], dim=1)
    return GraphBatch(node_features, edge_index, edge_attr, target)


class GraphMessageBlock(nn.Module):
    def __init__(self, hidden_dim: int, edge_dim: int = 2) -> None:
        super().__init__()
        self.message = mlp([hidden_dim * 2 + edge_dim, hidden_dim, hidden_dim])
        self.update = mlp([hidden_dim * 2, hidden_dim, hidden_dim])

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        src, dst = edge_index
        msg_input = torch.cat([x[src], x[dst], edge_attr], dim=-1)
        msg = self.message(msg_input)
        agg = torch.zeros_like(x)
        agg.index_add_(0, dst, msg)
        deg = torch.zeros(x.shape[0], 1, device=x.device)
        deg.index_add_(0, dst, torch.ones_like(dst, dtype=x.dtype).unsqueeze(-1))
        agg = agg / deg.clamp_min(1.0)
        return x + self.update(torch.cat([x, agg], dim=-1))


class MeshGNN(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, hidden_dim: int = 48, layers: int = 3) -> None:
        super().__init__()
        self.encoder = mlp([in_dim, hidden_dim, hidden_dim])
        self.blocks = nn.ModuleList([GraphMessageBlock(hidden_dim) for _ in range(layers)])
        self.decoder = mlp([hidden_dim, hidden_dim, out_dim])

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        x = self.encoder(node_features)
        for block in self.blocks:
            x = block(x, edge_index, edge_attr)
        return self.decoder(x)


class DynamicsNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 64) -> None:
        super().__init__()
        self.net = mlp([state_dim + action_dim, hidden_dim, hidden_dim, state_dim])

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        return state + self.net(torch.cat([state, action], dim=-1))


class DirectFieldMLP(nn.Module):
    def __init__(self, in_dim: int = 6, out_dim: int = STATE_DIM, hidden_dim: int = 64) -> None:
        super().__init__()
        self.net = mlp([in_dim, hidden_dim, hidden_dim, hidden_dim, out_dim])

    def forward(self, coords_time_action: torch.Tensor) -> torch.Tensor:
        return self.net(coords_time_action)


def smoke_grid_model(
    name: str,
    model: nn.Module,
    device: torch.device,
    steps: int,
    height: int,
    width: int,
) -> tuple[float, float]:
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3.0e-3)
    x, target = make_grid_transition_batch(batch=3, height=height, width=width, device=device)
    first = last = math.nan
    for step in range(steps):
        pred = model(x)
        loss = F.mse_loss(pred, target)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        first = float(loss.detach()) if step == 0 else first
        last = float(loss.detach())
    print(f"{name:14s} output={tuple(pred.shape)} loss={first:.4e}->{last:.4e}")
    return first, last


def smoke_mesh_gnn(device: torch.device, steps: int, side: int) -> tuple[float, float]:
    batch = make_graph_batch(side=side, device=device)
    model = MeshGNN(
        in_dim=batch.node_features.shape[1],
        out_dim=STATE_DIM,
        hidden_dim=48,
        layers=3,
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3.0e-3)
    first = last = math.nan
    for step in range(steps):
        pred = model(batch.node_features, batch.edge_index, batch.edge_attr)
        loss = F.mse_loss(pred, batch.target)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        first = float(loss.detach()) if step == 0 else first
        last = float(loss.detach())
    print(f"{'MeshGNN':14s} output={tuple(pred.shape)} loss={first:.4e}->{last:.4e}")
    return first, last


def smoke_dynamics_net(device: torch.device, steps: int) -> tuple[float, float]:
    model = DynamicsNet(state_dim=12, action_dim=ACTION_DIM).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3.0e-3)
    state = torch.randn(32, 12, device=device)
    action = torch.rand(32, ACTION_DIM, device=device)
    target = state + 0.15 * torch.tanh(state) + 0.05 * action.mean(dim=-1, keepdim=True)
    first = last = math.nan
    for step in range(steps):
        pred = model(state, action)
        loss = F.mse_loss(pred, target)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        first = float(loss.detach()) if step == 0 else first
        last = float(loss.detach())
    print(f"{'DynamicsNet':14s} output={tuple(pred.shape)} loss={first:.4e}->{last:.4e}")
    return first, last


def smoke_direct_field_mlp(device: torch.device, steps: int) -> tuple[float, float]:
    model = DirectFieldMLP().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3.0e-3)
    n_points = 384
    coords = torch.rand(n_points, 2, device=device) - 0.5
    action = torch.rand(1, ACTION_DIM, device=device).expand(n_points, -1)
    time = torch.full((n_points, 1), 0.25, device=device)
    target = crack_like_state(coords, action, time_shift=0.05)
    features = torch.cat([coords, time, action], dim=-1)
    first = last = math.nan
    for step in range(steps):
        pred = model(features)
        loss = F.mse_loss(pred, target)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        first = float(loss.detach()) if step == 0 else first
        last = float(loss.detach())
    print(f"{'DirectFieldMLP':14s} output={tuple(pred.shape)} loss={first:.4e}->{last:.4e}")
    return first, last


def parse_models(text: str) -> list[str]:
    available = ["mesh_gnn", "unet", "fno", "dynamics", "direct_mlp"]
    if text == "all":
        return available
    requested = [part.strip() for part in text.split(",") if part.strip()]
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise SystemExit(f"Unknown model(s): {', '.join(unknown)}. Available: {', '.join(available)}")
    return requested


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default="all", help="all or comma list: mesh_gnn,unet,fno,dynamics,direct_mlp")
    parser.add_argument("--steps", type=int, default=4, help="Tiny optimization steps per model.")
    parser.add_argument("--grid-size", type=int, default=16, help="Grid height/width for UNet/FNO tests.")
    parser.add_argument("--graph-side", type=int, default=12, help="Nodes per side for synthetic graph.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--device", default="cpu", help="cpu, mps, or auto. Default cpu for portability.")
    args = parser.parse_args()

    torch.set_num_threads(1)
    set_seed(args.seed)
    device = choose_device(args.device)
    selected = parse_models(args.models)
    print(f"device={device} steps={args.steps} models={','.join(selected)}")

    in_channels = STATE_DIM + ACTION_DIM
    if "mesh_gnn" in selected:
        smoke_mesh_gnn(device, args.steps, args.graph_side)
    if "unet" in selected:
        smoke_grid_model(
            "TinyUNet",
            TinyUNet(in_channels, STATE_DIM),
            device,
            args.steps,
            args.grid_size,
            args.grid_size,
        )
    if "fno" in selected:
        smoke_grid_model(
            "TinyFNO2D",
            TinyFNO2D(in_channels, STATE_DIM),
            device,
            args.steps,
            args.grid_size,
            args.grid_size,
        )
    if "dynamics" in selected:
        smoke_dynamics_net(device, args.steps)
    if "direct_mlp" in selected:
        smoke_direct_field_mlp(device, args.steps)


if __name__ == "__main__":
    main()
