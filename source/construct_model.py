import torch
import torch._dynamo   # ★ 顶层导入，避免函数内 import 触发 UnboundLocalError
from pff_model import PFFModel
from material_properties import MaterialProperties
from network import NeuralNet, init_xavier

def construct_model(PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
                    williams_dict=None):
    """
    构建 PFF 模型、材料属性和神经网络。

    ★ Direction 4 新增参数
    williams_dict : dict | None
        None 或 {"enable": False} → input_dimension = 2（原始行为）
        {"enable": True, ...}     → input_dimension = 8（Williams 特征）
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

    # Neural network
    network = NeuralNet(input_dimension=in_dim,
                        output_dimension=domain_extrema.shape[0]+1,
                        n_hidden_layers=network_dict["hidden_layers"],
                        neurons=network_dict["neurons"],
                        activation=network_dict["activation"],
                        init_coeff=network_dict["init_coeff"])
    torch.manual_seed(network_dict["seed"])
    init_xavier(network)

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