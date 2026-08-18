import torch
import torch._dynamo   # ★ 顶层导入，避免函数内 import 触发 UnboundLocalError
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import (
    NeuralNet, FourierFeatureNet, MeshGraphNet, HybridMeshGraphNet,
    ChannelSeparatedMeshGraphNet, DamageLatentMeshGraphNet, KANRBFFieldNet,
    TopologyKANSingleFrontRBFNet,
    init_xavier,
)

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None, fourier_dict=None, graph_dict=None):
    """
    构建 PFF 模型、材料属性和神经网络。

    ★ Direction 4 新增参数
    williams_dict : dict | None
        None 或 {"enable": False} → input_dimension = 2（原始行为）
        {"enable": True, ...}     → input_dimension = 8（Williams 特征）

    ★ 2026-05-11 C10 新增参数
    fourier_dict : dict | None
        None 或 {"enable": False} → 标准 NeuralNet（原始行为）
        {"enable": True, "sigma": 30.0, "n_features": 128, "seed": 0}
                                  → FourierFeatureNet 包裹 NeuralNet, 输入加 γ(x)
        互斥: williams_dict 和 fourier_dict 不可同时 enable。
    """
    # Phase field model
    residual_stiffness = PFF_model_dict.get(
        "residual_stiffness",
        PFF_model_dict.get("res_stiff", 0.0),
    )
    pffmodel = PFFModel(PFF_model = PFF_model_dict["PFF_model"],
                        se_split = PFF_model_dict["se_split"],
                        tol_ir = torch.tensor(PFF_model_dict["tol_ir"], device=device),
                        residual_stiffness = torch.tensor(residual_stiffness, device=device))

    # Material model
    matprop = MaterialProperties(mat_E = torch.tensor(mat_prop_dict["mat_E"], device=device),
                                mat_nu = torch.tensor(mat_prop_dict["mat_nu"], device=device),
                                w1 = torch.tensor(mat_prop_dict["w1"], device=device),
                                l0 = torch.tensor(mat_prop_dict["l0"], device=device))

    # ★ Direction 4: Williams 启用时 NN 输入维度从 2 扩展到 8
    _wd = williams_dict or {}
    _williams_on = _wd.get('enable', False)
    in_dim = 8 if _williams_on else domain_extrema.shape[0]   # 8 or 2

    # ★ 2026-05-11 C10: Fourier feature 启用时换用 FourierFeatureNet
    _fd = fourier_dict or {}
    _fourier_on = _fd.get('enable', False)
    _gd = graph_dict or {}
    _graph_on = _gd.get('enable', False)
    _graph_mode = str(_gd.get('mode', 'full'))
    if sum(bool(x) for x in (_williams_on, _fourier_on, _graph_on)) > 1:
        raise ValueError("Williams, Fourier, and graph representations are mutually exclusive")

    # Neural network
    _model_type = str(network_dict.get("model_type", "MLP")).lower()
    if _model_type in {"kan_rbf", "topology_kan_singlefront_rbf"} and any(
        (_williams_on, _fourier_on, _graph_on)
    ):
        raise ValueError("KAN-RBF models are mutually exclusive with Williams, Fourier, and graph modes")

    if _model_type == "kan_rbf":
        _kr = network_dict.get("kan_rbf", {})
        network = KANRBFFieldNet(
            input_dimension=in_dim,
            output_dimension=domain_extrema.shape[0] + 1,
            domain_extrema=domain_extrema,
            kan_width=int(_kr.get("kan_width", 32)),
            kan_basis=int(_kr.get("kan_basis", 9)),
            rbf_x_centres=int(_kr.get("rbf_x_centres", 41)),
            rbf_y_centres=int(_kr.get("rbf_y_centres", 17)),
            rbf_y_extent=float(_kr.get("rbf_y_extent", 0.20)),
            rbf_sigma_x=float(_kr.get("rbf_sigma_x", 0.08)),
            rbf_sigma_y=float(_kr.get("rbf_sigma_y", 0.035)),
        )
        print("[construct_model] KANRBFFieldNet enabled: "
              f"KAN width={_kr.get('kan_width', 32)}, basis={_kr.get('kan_basis', 9)}, "
              f"phase centres={_kr.get('rbf_x_centres', 41)}x{_kr.get('rbf_y_centres', 17)}")
    elif _model_type == "topology_kan_singlefront_rbf":
        _kr = network_dict.get("topology_kan_singlefront_rbf", {})
        network = TopologyKANSingleFrontRBFNet(
            input_dimension=in_dim,
            output_dimension=domain_extrema.shape[0] + 1,
            domain_extrema=domain_extrema,
            kan_width=int(_kr.get("kan_width", 64)),
            kan_basis=int(_kr.get("kan_basis", 15)),
            topology_eps_y=float(_kr.get("topology_eps_y", 0.02)),
            topology_eps_x=float(_kr.get("topology_eps_x", 0.04)),
            initial_tip_x=float(_kr.get("initial_tip_x", 0.0)),
            front_centres=int(_kr.get("front_centres", 81)),
            front_width=float(_kr.get("front_width", 0.025)),
            corridor_sigma_y=float(_kr.get("corridor_sigma_y", 0.02)),
            phase_bias=float(_kr.get("phase_bias", -2.0)),
            phase_weight_init=float(_kr.get("phase_weight_init", -4.0)),
        )
        print("[construct_model] TopologyKANSingleFrontRBFNet enabled: "
              f"KAN width={_kr.get('kan_width', 64)}, basis={_kr.get('kan_basis', 15)}, "
              f"front centres={_kr.get('front_centres', 81)}, "
              f"corridor sigma y={_kr.get('corridor_sigma_y', 0.02)}")
    elif _graph_on:
        if _graph_mode == 'hybrid':
            network = HybridMeshGraphNet(
                input_dimension=in_dim,
                output_dimension=domain_extrema.shape[0]+1,
                n_hidden_layers=network_dict["hidden_layers"],
                neurons=network_dict["neurons"],
                activation=network_dict["activation"],
                init_coeff=network_dict["init_coeff"],
                graph_layers=int(_gd.get('layers', 2)),
                graph_neurons=int(_gd.get('neurons', 32)),
                graph_scale=float(_gd.get('scale', 1.0)),
                graph_bounded=bool(_gd.get('bounded', False)),
                graph_correction_channels=str(_gd.get('correction_channels', 'all')),
            )
            print(f"[construct_model] HybridMeshGraphNet enabled: "
                  f"base={network_dict['hidden_layers']}x{network_dict['neurons']}, "
                  f"graph={_gd.get('layers', 2)}x{_gd.get('neurons', 32)}, "
                  f"channels={_gd.get('correction_channels', 'all')}")
        elif _graph_mode == 'channel_separated':
            network = ChannelSeparatedMeshGraphNet(
                input_dimension=in_dim,
                output_dimension=domain_extrema.shape[0]+1,
                n_hidden_layers=network_dict["hidden_layers"],
                neurons=network_dict["neurons"],
                activation=network_dict["activation"],
                init_coeff=network_dict["init_coeff"],
                graph_layers=int(_gd.get('layers', 2)),
                graph_neurons=int(_gd.get('neurons', 32)),
                graph_uv_scale=float(_gd.get('uv_scale', 0.05)),
                graph_alpha_scale=float(_gd.get('alpha_scale', 0.01)),
                graph_bounded=bool(_gd.get('bounded', True)),
            )
            print("[construct_model] ChannelSeparatedMeshGraphNet enabled: "
                  f"uv_scale={_gd.get('uv_scale', 0.05)}, "
                  f"alpha_scale={_gd.get('alpha_scale', 0.01)}")
        elif _graph_mode == 'damage_latent':
            network = DamageLatentMeshGraphNet(
                input_dimension=in_dim,
                output_dimension=domain_extrema.shape[0]+1,
                n_hidden_layers=network_dict["hidden_layers"],
                neurons=network_dict["neurons"],
                activation=network_dict["activation"],
                init_coeff=network_dict["init_coeff"],
                graph_layers=int(_gd.get('layers', 2)),
                graph_neurons=int(_gd.get('neurons', 32)),
                latent_scale=float(_gd.get('latent_scale', 0.05)),
                mask_x_min=float(_gd.get('mask_x_min', -0.12)),
                mask_x_max=float(_gd.get('mask_x_max', 0.50)),
                mask_half_width=float(_gd.get('mask_half_width', 0.06)),
                mask_transition=float(_gd.get('mask_transition', 0.01)),
            )
            print("[construct_model] DamageLatentMeshGraphNet enabled: "
                  f"latent_scale={_gd.get('latent_scale', 0.05)}")
        elif _graph_mode == 'full':
            network = MeshGraphNet(
                input_dimension=in_dim,
                output_dimension=domain_extrema.shape[0]+1,
                n_hidden_layers=int(_gd.get('layers', network_dict["hidden_layers"])),
                neurons=int(_gd.get('neurons', network_dict["neurons"])),
                activation=network_dict["activation"],
                init_coeff=network_dict["init_coeff"],
            )
            print(f"[construct_model] MeshGraphNet enabled: layers={network.n_hidden_layers}, "
                  f"width={network.neurons}")
        else:
            raise ValueError(f"unsupported graph mode {_graph_mode!r}")
    elif _fourier_on:
        network = FourierFeatureNet(
            input_dimension=in_dim,
            output_dimension=domain_extrema.shape[0]+1,
            n_hidden_layers=network_dict["hidden_layers"],
            neurons=network_dict["neurons"],
            activation=network_dict["activation"],
            init_coeff=network_dict["init_coeff"],
            n_features=_fd.get('n_features', 128),
            sigma=_fd.get('sigma', 30.0),
            seed=_fd.get('seed', network_dict.get('seed', 0)),
        )
        print(f"[construct_model] FourierFeatureNet enabled: σ={_fd.get('sigma', 30.0)}, "
              f"n_features={_fd.get('n_features', 128)}, inner_dim={2*_fd.get('n_features', 128)}")
    else:
        network = NeuralNet(input_dimension=in_dim,
                            output_dimension=domain_extrema.shape[0]+1,
                            n_hidden_layers=network_dict["hidden_layers"],
                            neurons=network_dict["neurons"],
                            activation=network_dict["activation"],
                            init_coeff=network_dict["init_coeff"])
    torch.manual_seed(network_dict["seed"])
    init_xavier(network)
    if hasattr(network, "zero_graph_output"):
        network.zero_graph_output()

    # ★ 速度优化：torch.compile（PyTorch ≥ 2.0），减少 Python launch overhead
    # 编译是惰性的（首次 forward 才真编译）→ 必须设 dynamo suppress_errors
    # 否则 inductor backend 缺 triton（Windows 默认无）会硬崩
    if network_dict.get("compile", False):
        try:
            torch._dynamo.config.suppress_errors = True   # 编译失败时 fallback 到 eager
            network = torch.compile(network, mode='reduce-overhead')
            print(f"[construct_model] torch.compile enabled (suppress_errors=True for fallback)")
        except Exception as e:
            print(f"[construct_model] torch.compile setup failed, eager mode: {e}")

    return pffmodel, matprop, network
