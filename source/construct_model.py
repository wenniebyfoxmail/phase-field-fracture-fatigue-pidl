import torch
import torch._dynamo   # ★ 顶层导入，避免函数内 import 触发 UnboundLocalError
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import NeuralNet, init_xavier

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None, xfem_dict=None):
    """
    构建 PFF 模型、材料属性和神经网络。

    williams_dict : dict | None
        None 或 {"enable": False} → input_dimension = 2（原始行为）
        {"enable": True, ...}     → input_dimension = 8（Williams 特征）

    ★ α-3 XFEM-jump enrichment (Apr 29) — see design_alpha3_xfem_jump_apr29.md
    xfem_dict : dict | None
        None 或 {"enable": False} → 标准 NeuralNet（原行为）
        {"enable": True, ...}     → 构建 XFEMJumpNN（continuous head + Heaviside-gated jump head）
        Optional keys: n_hidden_c, neurons_c (default 8/400 = network_dict);
                       n_hidden_j, neurons_j (default 4/100);
                       heaviside_kind ('soft' | 'hard', default 'soft');
                       heaviside_eps (default 0.0005 = h_mesh/4);
                       activation_j (default 'ReLU')
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

    # ★ α-3 XFEM-jump (Heaviside discontinuity at moving x_tip)
    _xd = xfem_dict or {}
    _xfem_on = _xd.get('enable', False)

    # ★ Direction 4: Williams 启用时 NN 输入维度从 2 扩展到 8
    _wd = williams_dict or {}
    _williams_on = _wd.get('enable', False)

    if _xfem_on:
        from xfem_jump_network import XFEMJumpNN
        network = XFEMJumpNN(
            n_hidden_c=_xd.get('n_hidden_c', network_dict["hidden_layers"]),
            neurons_c=_xd.get('neurons_c', network_dict["neurons"]),
            n_hidden_j=_xd.get('n_hidden_j', 4),
            neurons_j=_xd.get('neurons_j', 100),
            heaviside_kind=_xd.get('heaviside_kind', 'soft'),
            heaviside_eps=_xd.get('heaviside_eps', 0.0005),
            jump_relative_input=_xd.get('jump_relative_input', True),
            activation_c=network_dict["activation"],
            activation_j=_xd.get('activation_j', 'ReLU'),
            init_coeff=network_dict["init_coeff"],
        )
        torch.manual_seed(network_dict["seed"])
        init_xavier(network.cont)
        init_xavier(network.jump)
        print(f"[construct_model] XFEMJumpNN built: "
              f"cont={_xd.get('n_hidden_c', network_dict['hidden_layers'])}×{_xd.get('neurons_c', network_dict['neurons'])} "
              f"jump={_xd.get('n_hidden_j', 4)}×{_xd.get('neurons_j', 100)} "
              f"heaviside={_xd.get('heaviside_kind', 'soft')} eps={_xd.get('heaviside_eps', 0.0005)}")
    elif _williams_on:
        in_dim = 8  # Williams features
        network = NeuralNet(input_dimension=in_dim,
                            output_dimension=domain_extrema.shape[0]+1,
                            n_hidden_layers=network_dict["hidden_layers"],
                            neurons=network_dict["neurons"],
                            activation=network_dict["activation"],
                            init_coeff=network_dict["init_coeff"])
        torch.manual_seed(network_dict["seed"])
        init_xavier(network)
    else:
        in_dim = domain_extrema.shape[0]   # 2
        network = NeuralNet(input_dimension=in_dim,
                            output_dimension=domain_extrema.shape[0]+1,
                            n_hidden_layers=network_dict["hidden_layers"],
                            neurons=network_dict["neurons"],
                            activation=network_dict["activation"],
                            init_coeff=network_dict["init_coeff"])
        torch.manual_seed(network_dict["seed"])
        init_xavier(network)

    # ★ 速度优化：torch.compile（PyTorch ≥ 2.0），减少 Python launch overhead
    # Skip for XFEMJumpNN (nested module + custom Heaviside has STE control flow)
    if network_dict.get("compile", False) and not _xfem_on:
        try:
            torch._dynamo.config.suppress_errors = True
            network = torch.compile(network, mode='reduce-overhead')
            print(f"[construct_model] torch.compile enabled (suppress_errors=True for fallback)")
        except Exception as e:
            print(f"[construct_model] torch.compile setup failed, eager mode: {e}")

    return pffmodel, matprop, network