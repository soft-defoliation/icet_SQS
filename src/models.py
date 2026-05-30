"""
SQS Workflow - 数据模型

使用Pydantic进行配置验证和序列化
"""

from __future__ import annotations

from typing import Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator

from src.constants import Defaults, QualityThresholds, CrystalPhases, MethodConfig


# =============================================================================
# 基础模型
# =============================================================================


class SystemConfig(BaseModel):
    """系统配置"""

    name: str = Field(default="SQS_system", description="系统名称")
    description: str = Field(default="SQS生成", description="系统描述")
    target_phase: str = Field(default=CrystalPhases.DEFAULT, description="目标晶体相")

    @field_validator("target_phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        if v not in CrystalPhases.PHASES:
            valid = ", ".join(CrystalPhases.PHASES.keys())
            raise ValueError(f"无效的目标相 '{v}'。有效选项: {valid}")
        return v


class ClusterSpaceConfig(BaseModel):
    """ClusterSpace配置"""

    cutoffs: list[float] = Field(default=Defaults.CUTOFFS, description="团簇截断半径列表 (Å)")
    symprec: float = Field(default=Defaults.SYMPREC, description="对称性容差")
    position_tolerance: float = Field(default=Defaults.POSITION_TOLERANCE, description="位置容差")

    @field_validator("cutoffs")
    @classmethod
    def validate_cutoffs(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("cutoffs不能为空")
        if any(c <= 0 for c in v):
            raise ValueError("截断半径必须为正数")
        return v


class SQSConfig(BaseModel):
    """SQS生成配置"""

    method: str = Field(default=MethodConfig.ENUMERATION, description="生成方法: enumeration 或 mc")

    # 枚举法参数
    max_size: int = Field(default=Defaults.MAX_SIZE, ge=1, description="原胞最大倍数")
    include_smaller_cells: bool = Field(
        default=Defaults.INCLUDE_SMALLER_CELLS, description="允许返回更小的优化结构"
    )

    # MC方法参数
    supercell_matrix: list[list[int]] = Field(
        default=Defaults.SUPERCELL_MATRIX, description="超胞扩胞矩阵"
    )

    # 通用参数
    pbc: tuple[bool, bool, bool] = Field(default=Defaults.PBC, description="周期边界条件")
    tolerance: float = Field(default=Defaults.TOLERANCE, gt=0, description="目标偏差容差")
    random_seed: Optional[int] = Field(default=None, description="随机种子")

    # MC特有参数
    max_iterations: int = Field(default=Defaults.MAX_ITERATIONS, ge=1, description="最大迭代次数")
    early_stop_no_improve: int = Field(
        default=Defaults.EARLY_STOP_NO_IMPROVE, ge=1, description="连续无改进停止阈值"
    )
    save_progress: bool = Field(default=True, description="保存优化进度")
    T_start: float = Field(default=Defaults.T_START, gt=0, description="MC初始温度")
    T_stop: float = Field(default=Defaults.T_STOP, gt=0, description="MC终止温度")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid_methods = [MethodConfig.ENUMERATION, MethodConfig.MONTE_CARLO]
        if v not in valid_methods:
            raise ValueError(f"无效的方法 '{v}'。有效选项: {', '.join(valid_methods)}")
        return v

    @field_validator("supercell_matrix")
    @classmethod
    def validate_supercell_matrix(cls, v: list[list[int]]) -> list[list[int]]:
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("supercell_matrix必须是3x3矩阵")
        # 检查是否是对角矩阵（目前只支持对角）
        for i in range(3):
            for j in range(3):
                if i != j and v[i][j] != 0:
                    raise ValueError("目前只支持对角超胞矩阵")
        if any(v[i][i] <= 0 for i in range(3)):
            raise ValueError("对角元素必须为正整数")
        return v

    @model_validator(mode="after")
    def validate_method_params(self) -> "SQSConfig":
        """验证方法与参数的一致性"""
        if self.method == MethodConfig.ENUMERATION:
            # 枚举法不需要supercell_matrix验证
            pass
        elif self.method == MethodConfig.MONTE_CARLO:
            # MC方法需要supercell_matrix
            if not self.supercell_matrix:
                raise ValueError("MC方法需要指定supercell_matrix")
        return self

    @property
    def supercell_multiplier(self) -> int:
        """计算超胞倍数"""
        if self.supercell_matrix:
            return (
                self.supercell_matrix[0][0]
                * self.supercell_matrix[1][1]
                * self.supercell_matrix[2][2]
            )
        return 1


class OutputConfig(BaseModel):
    """输出配置"""

    directory: str = Field(default=Defaults.OUTPUT_DIR, description="输出目录")
    formats: list[str] = Field(default=Defaults.FORMATS, description="输出格式列表")
    filename_prefix: str = Field(default=Defaults.FILENAME_PREFIX, description="文件名前缀")
    save_intermediate: bool = Field(default=True, description="保存中间文件")

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        valid_formats = ["vasp", "cif", "lammps-data", "json", "xyz", "extxyz"]
        invalid = [f for f in v if f not in valid_formats]
        if invalid:
            raise ValueError(f"无效格式: {invalid}. 有效选项: {valid_formats}")
        return v


class ValidationConfig(BaseModel):
    """验证配置"""

    check_correlation: bool = Field(default=True, description="检查团簇向量相关性")
    tolerance: float = Field(default=QualityThresholds.EXCELLENT, gt=0, description="验证容差")


# =============================================================================
# 掺杂配置模型
# =============================================================================


class DopingSiteConfig(BaseModel):
    """单个掺杂位点配置"""

    elements: list[str] = Field(..., description="允许的元素列表")
    concentration: dict[str, float] = Field(..., description="目标浓度")

    @model_validator(mode="after")
    def validate_concentration(self) -> "DopingSiteConfig":
        """验证浓度总和为1.0"""
        total = sum(self.concentration.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"浓度总和必须等于1.0，当前为{total}")

        # 验证所有浓度元素都在允许列表中
        for elem in self.concentration.keys():
            if elem not in self.elements:
                raise ValueError(f"浓度中的元素 '{elem}' 不在允许列表中")

        return self


# =============================================================================
# 主配置模型
# =============================================================================


class SQSWorkflowConfig(BaseModel):
    """SQS工作流完整配置"""

    system: SystemConfig = Field(default_factory=SystemConfig)
    cluster_space: ClusterSpaceConfig = Field(default_factory=ClusterSpaceConfig)
    sqs: SQSConfig = Field(default_factory=SQSConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    # 可选：掺杂配置（替代dop.in）
    doping: Optional[dict[str, DopingSiteConfig]] = Field(default=None, description="掺杂配置（可选）")

    @classmethod
    def from_file(cls, filepath: Path | str) -> "SQSWorkflowConfig":
        """从JSON文件加载配置"""
        import json

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)

    def to_file(self, filepath: Path | str) -> None:
        """保存配置到JSON文件"""
        import json

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    def get_target_concentrations(self) -> dict[str, dict[str, float]]:
        """获取目标浓度字典格式（兼容icet）"""
        if not self.doping:
            return {}

        return {name: site.concentration for name, site in self.doping.items()}


# =============================================================================
# 结果模型
# =============================================================================


class SQSResult(BaseModel):
    """SQS生成结果"""

    structure_data: dict[str, Any] = Field(..., description="结构数据")
    formula: str = Field(..., description="化学式")
    n_atoms: int = Field(..., description="原子数")
    method: str = Field(..., description="生成方法")
    max_size: int = Field(..., description="超胞倍数")
    deviation: float = Field(..., description="团簇向量偏差")
    quality: str = Field(..., description="质量评级")
    generation_time: float = Field(..., description="生成耗时(秒)")

    # 可选：MC特有
    n_iterations: Optional[int] = Field(default=None, description="迭代次数")
    supercell_matrix: Optional[list[list[int]]] = Field(default=None, description="超胞矩阵")

    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# 配置加载工具
# =============================================================================


def load_config(config_path: Optional[Path | str] = None) -> SQSWorkflowConfig:
    """
    加载配置文件。

    Args:
        config_path: 配置文件路径（None时使用默认配置）

    Returns:
        SQSWorkflowConfig对象
    """
    if config_path is None:
        return SQSWorkflowConfig()
    return SQSWorkflowConfig.from_file(config_path)


def create_default_config(output_path: Path | str) -> None:
    """
    创建默认配置文件模板。

    Args:
        output_path: 输出文件路径
    """
    config = SQSWorkflowConfig()
    config.to_file(output_path)
