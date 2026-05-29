"""
SQS Workflow - 常量定义模块

集中管理所有魔法数字和配置常量，避免分散在各处
"""

from typing import Final


# =============================================================================
# 质量评估阈值 (基于van de Walle 2013标准)
# =============================================================================

class QualityThresholds:
    """SQS质量评估阈值"""
    EXCELLENT: Final[float] = 0.001    # < 0.001: 优秀
    GOOD: Final[float] = 0.01          # < 0.01: 良好  
    ACCEPTABLE: Final[float] = 0.10    # < 0.10: 可用
    MARGINAL: Final[float] = 0.30      # < 0.30: 可接受(有限系统限制)
    
    @classmethod
    def evaluate(cls, deviation: float) -> tuple[str, bool, str]:
        """
        根据偏差值评估质量
        
        Returns:
            (评级, 是否通过, 详细说明)
        """
        if deviation < cls.EXCELLENT:
            return "优秀 ✅", True, "达到理想SQS质量"
        elif deviation < cls.GOOD:
            return "良好 ✓", True, "高质量SQS"
        elif deviation < cls.ACCEPTABLE:
            return "可用", True, "可接受的SQS质量"
        elif deviation < cls.MARGINAL:
            return f"可接受(有限系统限制)", True, "小系统或不对称浓度的物理限制"
        else:
            return "失败 ❌", False, "质量不达标，建议增大超胞或调整参数"


# =============================================================================
# 默认配置值
# =============================================================================

class Defaults:
    """默认配置值"""
    # ClusterSpace
    CUTOFFS: Final[list[float]] = [5.0]
    SYMPREC: Final[float] = 1e-3
    POSITION_TOLERANCE: Final[float] = 0.1
    
    # SQS生成
    MAX_SIZE: Final[int] = 8
    SUPERCELL_MATRIX: Final[list[list[int]]] = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
    INCLUDE_SMALLER_CELLS: Final[bool] = True
    PBC: Final[tuple[bool, bool, bool]] = (True, True, True)
    
    # MC方法
    MAX_ITERATIONS: Final[int] = 5
    TOLERANCE: Final[float] = 0.001
    EARLY_STOP_NO_IMPROVE: Final[int] = 3
    T_START: Final[float] = 5.0
    T_STOP: Final[float] = 0.001
    
    # 输出
    OUTPUT_DIR: Final[str] = "output"
    FILENAME_PREFIX: Final[str] = "SQS"
    FORMATS: Final[list[str]] = ["vasp", "cif"]
    

# =============================================================================
# 文件路径和命名
# =============================================================================

class FileNames:
    """标准文件名"""
    # 输入文件
    DOP_IN: Final[str] = "dop.in"
    DOP_IN_ALT: Final[str] = "input/dop.in"
    CONFIG: Final[str] = "config.json"
    POSCAR: Final[str] = "POSCAR"
    
    # 中间文件 (按执行顺序)
    CLUSTERSPACE: Final[str] = "output/02_clusterspace.cs"
    DOPING_INFO: Final[str] = "output/02_doping_info.json"
    SQS_STRUCTURE: Final[str] = "output/03_sqs_structure.json"
    
    # 输出文件
    FINAL_VASP: Final[str] = "SQS_FINAL.vasp"
    SUMMARY: Final[str] = "output/SUMMARY.txt"
    QUALITY_REPORT: Final[str] = "output/QUALITY_REPORT.txt"
    QUALITY_JSON: Final[str] = "output/quality_validation.json"
    PROGRESS_PKL: Final[str] = "output/sqs_optimization_progress.pkl"
    
    @classmethod
    def get_sqs_vasp_name(cls, method: str, max_size: int) -> str:
        """生成SQS VASP文件名"""
        return f"output/SQS_{method}_{max_size}x.vasp"
    
    @classmethod
    def get_sqs_cif_name(cls, method: str, max_size: int) -> str:
        """生成SQS CIF文件名"""
        return f"output/SQS_{method}_{max_size}x.cif"


# =============================================================================
# 数值容差
# =============================================================================

class Tolerances:
    """数值容差"""
    LATTICE_MATCH: Final[float] = 1e-6
    CONCENTRATION: Final[float] = 1e-6
    MULTIPLIER_CHECK: Final[float] = 0.01
    CV_IMPROVEMENT: Final[float] = 1e-6
    MIN_BOND_LENGTH: Final[float] = 1.0  # 最小键长警告阈值


# =============================================================================
# 晶体相定义
# =============================================================================

class CrystalPhases:
    """支持的晶体相"""
    PHASES: Final[dict[str, tuple[str, str, str]]] = {
        'cubic': ('Pm-3m', '立方相', '高温顺电相'),
        'tetragonal': ('P4mm', '四方相', '铁电相（室温）'),
        'orthorhombic': ('Amm2', '正交相', '低温铁电相'),
        'rhombohedral': ('R3m', '三方相', '极低温相'),
    }
    
    DEFAULT: Final[str] = 'cubic'
    
    @classmethod
    def get_name(cls, phase: str) -> str:
        """获取相的显示名称"""
        if phase in cls.PHASES:
            sg, name, _ = cls.PHASES[phase]
            return f"{sg} ({name})"
        return phase


# =============================================================================
# 日志配置
# =============================================================================

class LoggingConfig:
    """日志配置"""
    DEFAULT_LEVEL: Final[str] = "INFO"
    ICET_LEVEL: Final[str] = "INFO"
    FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


# =============================================================================
# CLI/UI 配置
# =============================================================================

class UIConfig:
    """UI配置"""
    BANNER_WIDTH: Final[int] = 70
    MENU_INDENT: Final[str] = "  "
    
    # ANSI颜色代码
    class Colors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'


# =============================================================================
# 方法配置
# =============================================================================

class MethodConfig:
    """生成方法配置"""
    ENUMERATION: Final[str] = "enumeration"
    MONTE_CARLO: Final[str] = "mc"
    
    DESCRIPTIONS: Final[dict[str, dict[str, str]]] = {
        ENUMERATION: {
            'name': '枚举法',
            'description': '基于 ClusterSpace 原胞',
            'params': 'max_size (原胞倍数)',
            'features': '全局最优解，结果尺寸灵活',
            'suitable': '中小体系，寻找最优结构'
        },
        MONTE_CARLO: {
            'name': 'MC方法',
            'description': '基于用户定义超胞',
            'params': 'supercell_matrix (超胞矩阵)',
            'features': '迭代优化，结果尺寸固定',
            'suitable': '精确控制结构大小'
        }
    }


# 向后兼容的别名
QUALITY_THRESHOLDS = QualityThresholds
DEFAULTS = Defaults
FILE_NAMES = FileNames
