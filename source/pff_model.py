"""
=============================================================================
pff_model.py - 相场断裂模型定义
=============================================================================
学习顺序: 1️⃣ 第一个阅读的文件

本文件定义了相场断裂的物理模型，包括：
- AT1模型：线性局部耗散函数 w(α) = α
- AT2模型：二次局部耗散函数 w(α) = α²

对应论文公式(2)(3)：
    AT1: g(α) = (1-α)² + η,  w(α) = α,   c_w = 8/3
    AT2: g(α) = (1-α)² + η,  w(α) = α²,  c_w = 2

参考论文第2节: "Phase-field model of brittle fracture"
=============================================================================
"""


import warnings

# Defines phase field fracture model
class PFFModel:
    """
    相场断裂模型类

    物理背景：
    - 相场变量 α ∈ [0, 1]：0表示完好材料，1表示完全断裂
    - 退化函数 g(α)：控制弹性模量随损伤的退化
    - 损伤函数 w(α)：控制单位体积的耗散能

    参数：
    ----------
    PFF_model : str
        模型类型，'AT1' 或 'AT2'
        - AT1：裂纹萌生有明确的应力阈值，相场突然从0跳到1
        - AT2：相场可以渐进演化，更容易学习裂纹萌生

    se_split : str
        应变能分解方式，'volumetric' 或 None
        - 'volumetric'：体积-偏应变分解，区分拉伸和压缩
        - None：不分解，压缩也会导致损伤（非物理）

    tol_ir : float
        不可逆性容差，默认 5×10⁻³
        控制相场不可逆性约束的严格程度
    """

    def __init__(self, PFF_model = 'AT1', se_split = 'volumetric', tol_ir = 5e-3):
        self.PFF_model = PFF_model # AT1 或 AT2 模型
        self.se_split = se_split    # 应变能分解方式
        self.tol_ir = tol_ir    # 不可逆性容差阈值

        # 输入检查
        if self.se_split != 'volumetric':
            warnings.warn('Prescribed strain energy split is not volumetric. No strain energy split will be applied.')
        
        if self.PFF_model not in ['AT1', 'AT2']:
            raise ValueError('PFF_model must be AT1 or AT2')

    # degradation function for Young's modulus and its derivative w.r.t. \alpha: g(\alpha) and g'(\alpha)
    def Edegrade(self, alpha):
        return (1 - alpha)**2, 2*(alpha - 1)

    """
    退化函数及其导数

    物理意义：
    - g(α) 控制杨氏模量随损伤的退化: E_eff = g(α) × E₀
    - 当 α=0（完好），g=1，材料保持原始刚度
    - 当 α=1（断裂），g≈0（实际为η），刚度几乎消失

    公式（论文公式2-3）：
        g(α) = (1 - α)² + η
        g'(α) = 2(α - 1) = -2(1 - α)

    参数：
    ------
    alpha : torch.Tensor
        相场变量 α ∈ [0, 1]

    返回：
    ------
    g : torch.Tensor
        退化函数值 g(α)
    dg : torch.Tensor
        退化函数导数 g'(α)

    注意：
    ------
    η = o(l) 是一个小的残余刚度，防止数值奇异
    在代码中通常设置为 η ≈ 10⁻⁶
    """

    # damage function and its derivative w.r.t. \alpha: w(\alpha) and w'(\alpha) and c_w
    def damageFun(self, alpha):
        """
               损伤函数及其导数和归一化常数

               物理意义：
               - w(α) 表示单位体积材料损伤所耗散的能量密度
               - c_w 是归一化常数，确保当裂纹完全形成时释放的能量等于 Gc

               公式：
               - AT1: w(α) = α,     c_w = 8/3    （线性）
               - AT2: w(α) = α²,    c_w = 2      （二次）

               AT1 vs AT2 的物理差异：
               - AT1：存在弹性阶段，达到临界应力后才开始损伤
               - AT2：任意应变都会导致损伤，无明确的弹性阶段

               参数：
               ------
               alpha : torch.Tensor
                   相场变量

               返回：
               ------
               w : torch.Tensor
                   损伤函数值 w(α)
               dw : float or torch.Tensor
                   损伤函数导数 w'(α)
               c_w : float
                   归一化常数
               """
        if self.PFF_model == 'AT1':
            return alpha, 1.0, 8.0/3.0
        elif self.PFF_model == 'AT2':
            return alpha**2, 2*alpha, 2.0
    
    # Irreversibility penalty
    def irrPenalty(self):
        """
                不可逆性惩罚系数

                物理意义：
                - 相场的不可逆性约束：α(t) ≥ α(t-1)
                - 即裂纹一旦形成就不能"愈合"
                - 使用惩罚函数法来软化这个约束

                惩罚能量（论文公式14）：
                    E_ir = ∫_Ω (1/2) γ_ir ⟨α - α_{n-1}⟩²₋ dΩ

                其中 ⟨·⟩₋ = min(·, 0)，只惩罚α减小的情况

                惩罚系数（论文公式15-16）：
                - AT1: γ_ir = (Gc/l) × 27/(64×TOL²_ir)
                - AT2: γ_ir = (Gc/l) × (1/TOL²_ir - 1)

                注意：
                ------
                在无量纲化后，Gc/l → w1/l0 = 1（见论文2.4节）
                因此这里只返回无量纲的系数部分

                返回：
                ------
                penalty_coeff : float
                    不可逆性惩罚的无量纲系数
                """
        if self.PFF_model == 'AT1':
            return 27/64/self.tol_ir**2
        elif self.PFF_model == 'AT2':
            return 1.0/self.tol_ir**2-1.0