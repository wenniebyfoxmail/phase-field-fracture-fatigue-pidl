from pathlib import Path
import sys

import pytest
import torch


SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))

from network import (  # noqa: E402
    HybridMeshGraphNet, MeshGraphNet, bind_mesh_graph, init_xavier,
)


def make_net():
    return MeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0)


def test_forward_requires_bound_graph():
    with pytest.raises(RuntimeError, match="not bound"):
        make_net()(torch.rand(4, 2))


def test_bound_graph_forward_and_backward():
    net = make_net()
    connectivity = torch.tensor([[0, 1, 2], [1, 3, 2]])
    coordinates = torch.rand(4, 2, requires_grad=True)
    bind_mesh_graph(net, connectivity, len(coordinates))
    output = net(coordinates)
    assert output.shape == (4, 3)
    output.square().mean().backward()
    assert coordinates.grad is not None
    assert all(p.grad is not None for p in net.parameters())


def test_graph_can_rebind_for_coarse_to_fine_mesh():
    net = make_net()
    bind_mesh_graph(net, torch.tensor([[0, 1, 2]]), 3)
    assert net(torch.rand(3, 2)).shape == (3, 3)
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    assert net(torch.rand(4, 2)).shape == (4, 3)


def test_runtime_graph_is_not_stored_in_checkpoint():
    net = make_net()
    bind_mesh_graph(net, torch.tensor([[0, 1, 2]]), 3)
    keys = net.state_dict().keys()
    assert "edge_src" not in keys
    assert "edge_dst" not in keys
    assert "degree" not in keys


def test_xavier_initializes_biasless_message_layers():
    net = make_net()
    init_xavier(net)
    assert all(layer.bias is None for layer in net.neighbor_layers)
    assert all(torch.isfinite(layer.weight).all() for layer in net.neighbor_layers)


def test_hybrid_starts_as_exact_coordinate_mlp():
    net = HybridMeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8)
    init_xavier(net)
    net.zero_graph_output()
    coordinates = torch.rand(4, 2)
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    assert torch.equal(net(coordinates), net.base(coordinates))


def test_hybrid_graph_branch_receives_gradient_from_zero_output():
    net = HybridMeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8)
    init_xavier(net)
    net.zero_graph_output()
    coordinates = torch.rand(4, 2)
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    net(coordinates).square().mean().backward()
    assert net.graph.output_layer.weight.grad is not None
    assert torch.count_nonzero(net.graph.output_layer.weight.grad) > 0
