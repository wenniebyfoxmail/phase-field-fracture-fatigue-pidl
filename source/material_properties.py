
# Defines material properties
class MaterialProperties:
    def __init__(self, mat_E, mat_nu, w1, l0):
        self.mat_E = mat_E
        self.mat_nu = mat_nu
        self.w1 = w1
        self.l0 = l0

        # Lamé parameters
        # μ = 抗剪能力（shear stiffness），抵抗滑动
        # λ = 抗体积压缩能力（volumetric stiffness），抵抗压缩
        # 工程上更常见E和v（Young’s modulus and Poisson ratio），但是lame常数理论公式更方便
        # 所以用胡克定律的张量形式进行转换
        # 后面用来计算线弹性应力 应力 = 剪切部分 + 体积部分
        # \sigma = 2\mu \varepsilon + \lambda \, tr(\varepsilon) I
        self.mat_lmbda = self.mat_E*self.mat_nu/(1+self.mat_nu)/(1-2*self.mat_nu)
        self.mat_mu = self.mat_E/(1+self.mat_nu)/2.0

    def __call__(self):
        return self.mat_lmbda, self.mat_mu, self.w1, self.l0
    