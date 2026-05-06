from config import *

PATH_SOURCE = Path(__file__).parents[1]
sys.path.insert(0, str(PATH_SOURCE/Path('source')))

from field_computation import FieldComputation
from construct_model import construct_model
from model_train import train



# run as: python .\main.py hidden_layers neurons seed activation init_coeff
# for example: python .\main.py 8 400 1 TrainableReLU 3.0


## ############################################################################
## Model construction #########################################################
## ############################################################################
pffmodel, matprop, network = construct_model(PFF_model_dict, mat_prop_dict,
                                             network_dict, domain_extrema, device,
                                             williams_dict=williams_dict)   # ★ Direction 4
field_comp = FieldComputation(net = network,
                              domain_extrema = domain_extrema,
                              lmbda = torch.tensor([0.0], device = device),
                              theta = loading_angle,
                              alpha_constraint = numr_dict["alpha_constraint"],
                              williams_dict = williams_dict,                 # ★ Direction 4
                              ansatz_dict  = ansatz_dict,                    # ★ Direction 5
                              l0 = mat_prop_dict["l0"],                      # ★ Direction 4
                              symmetry_prior = symmetry_prior)               # ★ 2026-05-06
field_comp.net = field_comp.net.to(device)
field_comp.domain_extrema = field_comp.domain_extrema.to(device)
field_comp.theta = field_comp.theta.to(device)
# ★ Direction 5: 可学习标量 c_singular（nn.Parameter）迁移到 device
if field_comp.c_singular is not None:
    import torch.nn as _nn
    field_comp.c_singular = _nn.Parameter(field_comp.c_singular.data.to(device))

## #############################################################################
## #############################################################################



## #############################################################################
# Training #####################################################################
## #############################################################################
if __name__ == "__main__":
    # ★ 根据 fatigue_dict 自动选择加载序列：
    #   fatigue_on=True  + loading_type='cyclic'   → disp_cyclic（等幅循环）
    #   fatigue_on=False 或 loading_type='monotonic' → disp（原始单调加载）
    _fatigue_on   = fatigue_dict.get("fatigue_on", False)
    _loading_type = fatigue_dict.get("loading_type", "monotonic")
    active_disp   = disp_cyclic if (_fatigue_on and _loading_type == "cyclic") else disp

    train(field_comp, active_disp, pffmodel, matprop, crack_dict, numr_dict,
          optimizer_dict, training_dict, coarse_mesh_file, fine_mesh_file,
          device, trainedModel_path, intermediateModel_path, writer,
          fatigue_dict=fatigue_dict)   # ★ 传入疲劳字典
