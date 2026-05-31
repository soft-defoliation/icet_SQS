"""
SQS Workflow - 结构解析器

统一处理dop.in和其他结构文件的解析
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np
from ase import Atoms

from sqs_workflow.constants import FileNames
from sqs_workflow.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DopingSite:
    """掺杂位点信息"""

    index: int
    position: list[float]  # 分数坐标
    allowed_elements: list[str]
    concentration: dict[str, float]
    is_disordered: bool


@dataclass
class ParsedStructure:
    """解析后的结构信息"""

    structure: Atoms
    sites: list[DopingSite]
    target_concentrations: dict[str, dict[str, float]]
    n_disordered: int
    n_ordered: int
    lattice: np.ndarray
    scale: float


class StructureParser:
    """结构文件解析器"""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath
        self._lines: list[str] = []

    @staticmethod
    def find_dop_in(cwd: Optional[Path] = None) -> Path:
        """
        查找dop.in文件

        查找顺序:
            1. ./dop.in
            2. input/dop.in

        Returns:
            dop.in文件路径

        Raises:
            FileNotFoundError: 如果找不到文件
        """
        if cwd is None:
            cwd = Path.cwd()

        for candidate in [cwd / FileNames.DOP_IN, cwd / FileNames.DOP_IN_ALT]:
            if candidate.exists():
                logger.debug(f"找到dop.in: {candidate}")
                return candidate

        raise FileNotFoundError(f"未找到dop.in文件。查找位置: {FileNames.DOP_IN}, {FileNames.DOP_IN_ALT}")

    def parse(self, filepath: Optional[Path] = None) -> ParsedStructure:
        """
        解析带标注的POSCAR文件

        Args:
            filepath: 文件路径（None时使用构造函数传入的路径）

        Returns:
            ParsedStructure对象
        """
        if filepath:
            self.filepath = filepath

        if not self.filepath:
            self.filepath = self.find_dop_in()

        logger.info(f"解析结构文件: {self.filepath}")

        with open(self.filepath, "r") as f:
            self._lines = f.readlines()

        # 解析头部
        scale, lattice = self._parse_header()

        # 解析坐标
        sites = self._parse_coordinates()

        # 构建ASE Atoms
        symbols = [site.allowed_elements[0] for site in sites]
        positions = [site.position for site in sites]

        structure = Atoms(symbols=symbols, scaled_positions=positions, cell=lattice, pbc=True)

        # 计算统计
        n_disordered = sum(1 for s in sites if s.is_disordered)
        n_ordered = len(sites) - n_disordered

        # 构建target_concentrations
        target_concentrations = self._build_target_concentrations(sites)

        result = ParsedStructure(
            structure=structure,
            sites=sites,
            target_concentrations=target_concentrations,
            n_disordered=n_disordered,
            n_ordered=n_ordered,
            lattice=np.array(lattice),
            scale=scale,
        )

        logger.info(f"解析完成: {len(sites)}个原子, {n_disordered}个无序位点")

        return result

    def _parse_header(self) -> tuple[float, list[list[float]]]:
        """解析文件头部（标题、缩放因子、晶格）"""
        # 第2行是缩放因子
        scale = float(self._lines[1].strip())

        # 第3-5行是晶格向量
        lattice = []
        for i in range(2, 5):
            parts = self._lines[i].strip().split()
            lattice.append([float(x) * scale for x in parts])

        return scale, lattice

    def _parse_coordinates(self) -> list[DopingSite]:
        """解析坐标行（第9行开始）"""
        sites = []

        for line_idx, line in enumerate(self._lines[8:], start=0):
            line = line.strip()

            # 跳过空行和注释行
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            # 提取坐标
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                continue

            # 查找掺杂标注
            label = self._extract_label(parts[3:])

            # 解析标注
            if label:
                allowed_elements, concentration = self._parse_label(label)
                is_disordered = len(allowed_elements) > 1
            else:
                raise ValueError(f"第{line_idx+9}行缺少元素标注！" f"格式: x y z Element=1.0 # index N")

            site = DopingSite(
                index=line_idx,
                position=[x, y, z],
                allowed_elements=allowed_elements,
                concentration=concentration,
                is_disordered=is_disordered,
            )
            sites.append(site)

        return sites

    def _extract_label(self, parts: list[str]) -> Optional[str]:
        """从行片段中提取掺杂标注"""
        for part in parts:
            if "=" in part and not part.startswith("#"):
                return part
        return None

    def _parse_label(self, label: str) -> tuple[list[str], dict[str, float]]:
        """
        解析掺杂标注

        格式:
            - 单元素: "K=1.0"
            - 多元素: "K=0.5,Na=0.5"
        """
        allowed_elements = []
        concentration = {}

        for item in label.split(","):
            if "=" in item:
                try:
                    elem, conc = item.split("=")
                    elem = elem.strip()
                    conc = float(conc.strip())
                    allowed_elements.append(elem)
                    concentration[elem] = conc
                except ValueError:
                    continue

        return allowed_elements, concentration

    def _build_target_concentrations(self, sites: list[DopingSite]) -> dict[str, dict[str, float]]:
        """
        按元素分组构建target_concentrations

        将无序位点按主要元素分组（如A位、B位）
        """
        # 按第一个元素分组
        groups: dict[str, list[DopingSite]] = {}

        for site in sites:
            if site.is_disordered:
                key = site.allowed_elements[0]
                if key not in groups:
                    groups[key] = []
                groups[key].append(site)

        # 转换为icet格式
        target_concentrations = {}
        for i, (key, group_sites) in enumerate(sorted(groups.items())):
            # 使用字母标识（A, B, C...）
            group_name = chr(ord("A") + i)
            # 所有位点应该有相同的浓度配置
            if group_sites:
                target_concentrations[group_name] = group_sites[0].concentration

        return target_concentrations

    def parse_for_supercell(
        self, filepath: Optional[Path] = None
    ) -> tuple[Atoms, np.ndarray, float]:
        """
        简化的解析，用于超胞构建

        Returns:
            (structure, lattice, scale)
        """
        if filepath:
            self.filepath = filepath

        if not self.filepath:
            self.filepath = self.find_dop_in()

        with open(self.filepath, "r") as f:
            lines = f.readlines()

        scale = float(lines[1].strip())

        lattice = []
        for i in range(2, 5):
            parts = lines[i].strip().split()
            lattice.append([float(x) * scale for x in parts])

        coords = []
        symbols = []

        for line in lines[8:]:
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    coords.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    label = parts[3]
                    elem = label.split("=")[0] if "=" in label else label
                    symbols.append(elem)
                except (ValueError, IndexError):
                    continue

        structure = Atoms(symbols=symbols, scaled_positions=coords, cell=lattice, pbc=True)

        return structure, np.array(lattice), scale


def parse_dop_in(filepath: Optional[Path] = None) -> ParsedStructure:
    """
    便捷函数：解析dop.in文件

    Args:
        filepath: 文件路径（None时自动查找）

    Returns:
        ParsedStructure对象
    """
    parser = StructureParser(filepath)
    return parser.parse()


def parse_dop_in_for_supercell(filepath: Optional[Path] = None) -> tuple[Atoms, np.ndarray, float]:
    """
    便捷函数：解析dop.in用于超胞构建

    Args:
        filepath: 文件路径（None时自动查找）

    Returns:
        (structure, lattice, scale)
    """
    parser = StructureParser(filepath)
    return parser.parse_for_supercell()
