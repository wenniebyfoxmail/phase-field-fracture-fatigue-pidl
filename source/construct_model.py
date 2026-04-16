import torch
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import NeuralNet, init_xavier

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None, fourier_dict=None):
    """
    构建 PFF 模型、材料属性和神经网络。

    ★ Direction 4 新增参数
    williams_dict : dict | None
        None 或 {"enable": False} → input_dimension = 2（原始行为）
        {"enable": True, ...}     → input_dimension = 8（Williams 特征）

    ★ exp/fourier-feature 新增参数
    fourier_dict : dict | None
        None 或 {"enable": False} → input_dimension = 2（原始行为）
        {"enable": True, "n_freq": nf, ...} → input_dimension = 2 + 2·nf（Fourier 特征）
        与 williams_dict 互斥（已在 config.py 通过 assert 检查）
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

    # ★ NN 输入维度：Williams (8D) / Fourier (2+2·n_freq D) / 原始 (2D) 三选一
    _wd = williams_dict or {}
    _fd = fourier_dict or {}
    _williams_on = _wd.get('enable', False)
    _fourier_on  = _fd.get('enable', False)
    if _williams_on:
        in_dim = 8                                           # Williams 8D 标准集
    elif _fourier_on:
        in_dim = 2 + 2 * int(_fd.get('n_freq', 16))          # Fourier 2 + 2·n_freq
    else:
        in_dim = domain_extrema.shape[0]                     # 原始 2D

    # Neural network
    network = NeuralNet(input_dimension=in_dim,
                        output_dimension=domain_extrema.shape[0]+1,
                        n_hidden_layers=network_dict["hidden_layers"],
                        neurons=network_dict["neurons"],
                        activation=network_dict["activation"],
                        init_coeff=network_dict["init_coeff"])
    torch.manual_seed(network_dict["seed"])
    init_xavier(network)

    return pffmodel, matprop, network