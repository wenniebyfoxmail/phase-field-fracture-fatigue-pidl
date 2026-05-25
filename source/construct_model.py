import torch
import torch._dynamo   # ★ 顶层导入，避免函数内 import 触发 UnboundLocalError
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import NeuralNet, FourierFeatureNet, TipLocalNet, init_xavier

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None, fourier_dict=None, tip_local_net_dict=None):
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
    tip_local_net_dict : dict | None
        None 或 {"enable": False} → 标准 NeuralNet（原始行为）
        {"enable": True, "x_tip": 0.0, "y_tip": 0.0, "r_tip": 0.05, ...}
                                  → Global NN + compact local crack-tip correction NN.
        互斥: williams_dict, fourier_dict, tip_local_net_dict 不可同时 enable。
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
    in_dim = 8 if _williams_on else domain_extrema.shape[0]   # 8 or 2

    # ★ 2026-05-11 C10: Fourier feature 启用时换用 FourierFeatureNet
    _fd = fourier_dict or {}
    _fourier_on = _fd.get('enable', False)
    _td = tip_local_net_dict or {}
    _tip_local_on = _td.get('enable', False)
    _enabled = [
        name for name, enabled in (
            ("williams_dict", _williams_on),
            ("fourier_dict", _fourier_on),
            ("tip_local_net_dict", _tip_local_on),
        ) if enabled
    ]
    if len(_enabled) > 1:
        raise ValueError(f"Mutually exclusive representation configs enabled: {_enabled}")

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
    elif _tip_local_on:
        network = TipLocalNet(
            input_dimension=in_dim,
            output_dimension=domain_extrema.shape[0]+1,
            n_hidden_layers=network_dict["hidden_layers"],
            neurons=network_dict["neurons"],
            activation=network_dict["activation"],
            init_coeff=network_dict["init_coeff"],
            x_tip=_td.get('x_tip', 0.0),
            y_tip=_td.get('y_tip', 0.0),
            r_tip=_td.get('r_tip', 0.05),
            window_radius=_td.get('window_radius', _td.get('r_tip', 0.05)),
            tip_hidden_layers=_td.get('hidden_layers', 3),
            tip_neurons=_td.get('neurons', 80),
            zero_init=_td.get('zero_init', True),
            output_mode=_td.get('output_mode', 'all'),
        )
        print(f"[construct_model] TipLocalNet enabled: tip=({_td.get('x_tip', 0.0)}, "
              f"{_td.get('y_tip', 0.0)}), r_tip={_td.get('r_tip', 0.05)}, "
              f"window_radius={_td.get('window_radius', _td.get('r_tip', 0.05))}, "
              f"local={_td.get('hidden_layers', 3)}x{_td.get('neurons', 80)}, "
              f"output_mode={_td.get('output_mode', 'all')}")
    else:
        network = NeuralNet(input_dimension=in_dim,
                            output_dimension=domain_extrema.shape[0]+1,
                            n_hidden_layers=network_dict["hidden_layers"],
                            neurons=network_dict["neurons"],
                            activation=network_dict["activation"],
                            init_coeff=network_dict["init_coeff"])
    torch.manual_seed(network_dict["seed"])
    init_xavier(network)
    if _tip_local_on and _td.get('zero_init', True):
        network.zero_local_output()

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
