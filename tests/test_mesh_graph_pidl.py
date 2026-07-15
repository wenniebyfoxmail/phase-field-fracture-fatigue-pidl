from pathlib import Path
import sys

import pytest
import torch


SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))

from network import (  # noqa: E402
    ChannelSeparatedMeshGraphNet, DamageLatentMeshGraphNet,
    HybridMeshGraphNet, MeshGraphNet, NeuralNet, bind_mesh_graph, init_xavier,
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


def test_hybrid_exposes_base_output_head_for_recovery_protocol():
    net = HybridMeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8)
    assert net.output_layer is net.base.output_layer


def test_hybrid_can_reset_trained_graph_correction_before_recovery():
    net = HybridMeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8)
    with torch.no_grad():
        net.graph.output_layer.weight.fill_(1.0)
        net.graph.output_layer.bias.fill_(1.0)
    net.zero_graph_output()
    assert torch.count_nonzero(net.graph.output_layer.weight) == 0
    assert torch.count_nonzero(net.graph.output_layer.bias) == 0


def test_bounded_hybrid_correction_cannot_exceed_scale():
    net = HybridMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_scale=0.05, graph_bounded=True,
    )
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    x = torch.rand(4, 2)
    correction = net(x) - net.base(x)
    assert torch.max(torch.abs(correction)) <= 0.050001


@pytest.mark.parametrize(
    ("channels", "inactive"),
    (("alpha", (0, 1)), ("uv", (2,))),
)
def test_hybrid_channel_ablation_leaves_inactive_base_outputs_exact(channels, inactive):
    net = HybridMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_scale=0.05, graph_bounded=True,
        graph_correction_channels=channels,
    )
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    x = torch.rand(4, 2)
    output = net(x)
    base = net.base(x)
    assert torch.equal(output[:, inactive], base[:, inactive])


def test_inactive_graph_output_rows_receive_zero_gradient():
    net = HybridMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_scale=0.05, graph_bounded=True,
        graph_correction_channels="alpha",
    )
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    net(torch.rand(4, 2)).square().mean().backward()
    grad = net.graph.output_layer.weight.grad
    assert torch.count_nonzero(grad[0:2]) == 0
    assert torch.count_nonzero(grad[2]) > 0


def test_row_specific_graph_reset_preserves_other_channels():
    net = HybridMeshGraphNet(2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8)
    with torch.no_grad():
        net.graph.output_layer.weight.fill_(1.0)
        net.graph.output_layer.bias.fill_(1.0)
    net.zero_graph_output(rows=(2,))
    assert torch.count_nonzero(net.graph.output_layer.weight[0:2]) > 0
    assert torch.count_nonzero(net.graph.output_layer.bias[0:2]) > 0
    assert torch.count_nonzero(net.graph.output_layer.weight[2]) == 0
    assert net.graph.output_layer.bias[2] == 0


def test_channel_mask_is_runtime_only_and_signature_is_explicit():
    net = HybridMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_scale=0.05, graph_bounded=True,
        graph_correction_channels="uv",
    )
    assert "graph_correction_mask" not in net.state_dict()
    assert net.representation_signature() == (
        "hybrid|channels=uv|bounded=true|scale=0.05|graph=2x8"
    )


def test_neural_net_encode_preserves_forward_semantics():
    net = NeuralNet(2, 3, 2, 12, "TrainableReLU", 1.0)
    x = torch.rand(4, 2)
    assert torch.equal(net(x), net.output_layer(net.encode(x)))


def test_channel_separated_starts_as_exact_coordinate_mlp():
    net = ChannelSeparatedMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_uv_scale=0.05, graph_alpha_scale=0.01,
    )
    init_xavier(net)
    net.zero_graph_output()
    x = torch.rand(4, 2)
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    assert torch.equal(net(x), net.base(x))


def test_channel_separated_alpha_reset_preserves_uv_graph():
    net = ChannelSeparatedMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
    )
    with torch.no_grad():
        net.graph_uv.output_layer.weight.fill_(1.0)
        net.graph_alpha.output_layer.weight.fill_(1.0)
    net.zero_graph_output(rows=(2,))
    assert torch.count_nonzero(net.graph_uv.output_layer.weight) > 0
    assert torch.count_nonzero(net.graph_alpha.output_layer.weight) == 0


def test_channel_separated_respects_independent_bounds():
    net = ChannelSeparatedMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
        graph_uv_scale=0.05, graph_alpha_scale=0.01,
    )
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    x = torch.rand(4, 2)
    correction = net(x) - net.base(x)
    assert torch.max(torch.abs(correction[:, :2])) <= 0.050001
    assert torch.max(torch.abs(correction[:, 2])) <= 0.010001


def test_damage_latent_starts_as_exact_coordinate_mlp():
    net = DamageLatentMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
    )
    init_xavier(net)
    net.zero_graph_output()
    x = torch.rand(4, 2)
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    assert torch.equal(net(x), net.base(x))


def test_damage_latent_graph_never_changes_uv_outputs():
    net = DamageLatentMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
    )
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    x = torch.tensor([[0.0, 0.0], [0.1, 0.0], [0.2, 0.01], [0.3, 0.0]])
    assert torch.equal(net(x)[:, :2], net.base(x)[:, :2])


def test_damage_latent_graph_receives_gradient_after_hard_alpha_reset():
    net = DamageLatentMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
    )
    init_xavier(net)
    net.zero_graph_output(rows=(2,))
    with torch.no_grad():
        net.output_layer.weight[2].zero_()
        net.output_layer.bias[2].fill_(1.0)
    x = torch.tensor([[0.0, 0.0], [0.1, 0.0], [0.2, 0.01], [0.3, 0.0]])
    bind_mesh_graph(net, torch.tensor([[0, 1, 2], [1, 3, 2]]), 4)
    net(x).square().mean().backward()
    grad = net.graph.output_layer.weight.grad
    assert grad is not None
    assert torch.count_nonzero(grad) > 0


def test_damage_latent_mask_is_detached_and_spatially_local():
    net = DamageLatentMeshGraphNet(
        2, 3, 2, 12, "TrainableReLU", 1.0, 2, 8,
    )
    x = torch.tensor([[0.0, 0.0], [0.0, 0.3]], requires_grad=True)
    mask = net._damage_mask(x)
    assert not mask.requires_grad
    assert mask[0] > 0.9
    assert mask[1] < 1.0e-6
