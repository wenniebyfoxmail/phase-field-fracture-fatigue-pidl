import torch
import torch._dynamo   # ★ 顶层导入，避免函数内 import 触发 UnboundLocalError
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import NeuralNet, FourierFeatureNet, SplitUVAlphaNet, init_xavier

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None, fourier_dict=None, sdf_ribbon_dict=None):
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

    ★ 2026-05-14 C8 v0a 新增参数
    sdf_ribbon_dict : dict | None
        None 或 {"enable": False} → input_dimension 不变
        {"enable": True, "epsilon": 1e-3}
                                  → input_dimension = 3，第3个通道 γ=sign(y)·sigmoid(-(x-x_tip)/ε)
        互斥: 与 williams_dict 不可同时 enable（都改 NN 输入维度）。
        可与 fourier_dict 组合（Fourier 投影 3 通道）。
    """
    # Phase field model
    pffmodel = PFFModel(PFF_model = PFF_model_dict["PFF_model"],
                        se_split = PFF_model_dict["se_split"],
                        tol_ir = torch.tensor(PFF_model_dict["tol_ir"], device=device))

    # Material model
    matprop = MaterialProperties(mat_E = torch.tensor(mat_prop_dict["mat_E"], device=device),
                                mat_nu = torch.tensor(mat_prop_dict["mat_nu"], device=device),
                                w1 = torch.tensor(mat_prop_dict["w1"], device=device),
                                l0 = torch.tensor(mat_prop_dict["l0"], device=device))

    # ★ Direction 4: Williams 启用时 NN 输入维度从 2 扩展到 8
    _wd = williams_dict or {}
    _williams_on = _wd.get('enable', False)

    # ★ 2026-05-14 C8: SDF ribbon
    #   apply_to='uv_only' (v1, default) → split NN: uv-net sees (x,y,γ), α-net sees (x,y)
    #   apply_to='all'     (v2)          → single NN sees (x,y,γ), all heads see γ
    _rd = sdf_ribbon_dict or {}
    _ribbon_on = _rd.get('enable', False)
    _ribbon_apply = _rd.get('apply_to', 'uv_only')   # ★ default uv_only per red-team W1
    if _ribbon_on and _ribbon_apply not in ('uv_only', 'all'):
        raise ValueError(f"sdf_ribbon_dict.apply_to must be 'uv_only' or 'all', got {_ribbon_apply!r}")
    if _williams_on and _ribbon_on:
        raise ValueError("williams_dict and sdf_ribbon_dict cannot both be enabled "
                         "(both reshape NN input dimension)")

    if _williams_on:
        in_dim = 8
    elif _ribbon_on:
        in_dim = 3                              # (x, y, γ); SplitUVAlphaNet routes γ off α head
    else:
        in_dim = domain_extrema.shape[0]        # 2

    # ★ 2026-05-11 C10: Fourier feature 启用时换用 FourierFeatureNet
    _fd = fourier_dict or {}
    _fourier_on = _fd.get('enable', False)
    if _williams_on and _fourier_on:
        raise ValueError("williams_dict and fourier_dict cannot both be enabled")
    if _ribbon_on and _ribbon_apply == 'uv_only' and _fourier_on:
        # v1 split NN + Fourier interaction not yet implemented: would need Fourier
        # only on uv-net or only on α-net, with care about γ projection.
        raise NotImplementedError(
            "sdf_ribbon_dict(apply_to='uv_only') + fourier_dict not yet implemented. "
            "For v0a smoke disable fourier_dict; for v2 (apply_to='all') Fourier wraps the single NN."
        )

    # Neural network
    if _fourier_on:
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
        torch.manual_seed(network_dict["seed"])
        init_xavier(network)
    elif _ribbon_on and _ribbon_apply == 'uv_only':
        # ★ 2026-05-14 C8 v1: split NN to isolate SDF effect on (u, v) from α head
        # uv-net: (x, y, γ) → (u_raw, v_raw)
        # α-net : (x, y)    → (α_raw,)
        torch.manual_seed(network_dict["seed"])
        uv_net = NeuralNet(input_dimension=3,
                           output_dimension=2,
                           n_hidden_layers=network_dict["hidden_layers"],
                           neurons=network_dict["neurons"],
                           activation=network_dict["activation"],
                           init_coeff=network_dict["init_coeff"])
        init_xavier(uv_net)
        alpha_net = NeuralNet(input_dimension=2,
                              output_dimension=1,
                              n_hidden_layers=network_dict["hidden_layers"],
                              neurons=network_dict["neurons"],
                              activation=network_dict["activation"],
                              init_coeff=network_dict["init_coeff"])
        init_xavier(alpha_net)
        network = SplitUVAlphaNet(uv_net=uv_net, alpha_net=alpha_net)
        print(f"[construct_model] SDF ribbon v1 (uv_only): split NN, "
              f"uv-net in_dim=3, α-net in_dim=2")
    else:
        network = NeuralNet(input_dimension=in_dim,
                            output_dimension=domain_extrema.shape[0]+1,
                            n_hidden_layers=network_dict["hidden_layers"],
                            neurons=network_dict["neurons"],
                            activation=network_dict["activation"],
                            init_coeff=network_dict["init_coeff"])
        torch.manual_seed(network_dict["seed"])
        init_xavier(network)
        if _ribbon_on and _ribbon_apply == 'all':
            print(f"[construct_model] SDF ribbon v2 (all heads): single NN, in_dim=3, "
                  f"γ reaches u/v/α via shared weights")

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