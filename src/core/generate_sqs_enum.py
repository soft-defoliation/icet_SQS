#!/usr/bin/env python3
"""
02_generate_sqs_enum.py
Enumeration method for SQS generation.

基于 icet 最佳实践重构版本：
- 添加类型注解和完整文档
- 启用 icet 日志支持
- 标准化浓度验证
- 修复质量阈值不一致
- 优化错误处理

References:
- icet docs: https://icet.materialsmodeling.org/en/3.2/
- icet-sqs-gui: https://github.com/bracerino/icet-sqs-gui
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional, Any

import numpy as np
from ase import Atoms
from ase.io import write
from icet import ClusterSpace
from icet.tools.structure_generation import generate_sqs_by_enumeration
from icet.input_output.logging_tools import set_log_config

# 配置 icet 日志
set_log_config(level="WARNING")

from src.utils.quality_utils import calculate_cv_deviation, evaluate_sqs_quality  # noqa: E402
from src.constants import Tolerances, FileNames  # noqa: E402


def validate_target_concentrations(
    target_concentrations: dict[str, dict[str, float]], tolerance: float = Tolerances.CONCENTRATION
) -> bool:
    """
    验证目标浓度配置。

    检查:
        1. 每个位点的浓度总和为 1.0 (在容差范围内)
        2. 浓度值在 [0, 1] 范围内

    Args:
        target_concentrations: 目标浓度配置
        tolerance: 浓度总和容差

    Returns:
        bool: 验证是否通过

    Raises:
        ValueError: 如果验证失败
    """
    for site_label, conc_dict in target_concentrations.items():
        total = sum(conc_dict.values())
        if abs(total - 1.0) > tolerance:
            raise ValueError(f"位点 '{site_label}' 的浓度总和为 {total:.6f}，必须等于 1.0")

        for elem, conc in conc_dict.items():
            if not 0 <= conc <= 1:
                raise ValueError(f"位点 '{site_label}' 中元素 '{elem}' 的浓度 " f"{conc} 超出 [0, 1] 范围")

    return True


def generate_sqs_on_fixed_supercell(
    cs: ClusterSpace,
    user_supercell: Atoms,
    doping_info: dict[str, Any],
    max_size: Optional[int] = None,
) -> tuple[Atoms, Atoms, float]:
    """
    在用户固定超胞晶格上生成 SQS。

    策略:
        1. 在原胞上使用枚举法获得最优原子排列
        2. 从枚举结果提取无序位点占据信息
        3. 将占据映射到用户超胞位置
        4. 返回具有精确用户晶格的 SQS

    Args:
        cs: ClusterSpace 对象
        user_supercell: ASE Atoms，具有用户的固定晶格
        doping_info: 掺杂信息字典，包含 chemical_symbols 和 target_concentrations
        max_size: 原胞倍数 (可选，None 时自动计算)

    Returns:
        tuple: (用户晶格 SQS, 原胞 SQS, 生成耗时秒数)

    Raises:
        ValueError: 如果原子数不匹配或浓度无效
        RuntimeError: 如果枚举失败
    """
    n_target = len(user_supercell)
    user_cell = np.array(user_supercell.cell)
    prim = cs.primitive_structure
    n_prim = len(prim)

    # 使用公共 API 获取化学符号，避免访问私有属性
    try:
        prim_chemical_symbols = cs.chemical_symbols
    except AttributeError:
        # 回退：从原胞结构推断
        prim_chemical_symbols = [[s] for s in prim.get_chemical_symbols()]

    multiplier_needed = n_target / n_prim

    if max_size is None:
        max_size = int(np.ceil(multiplier_needed))

    target_concentrations = doping_info.get("target_concentrations", {})

    # 验证浓度配置
    if target_concentrations:
        try:
            validate_target_concentrations(target_concentrations)
        except ValueError as e:
            print(f"\n  ✗ 浓度配置错误: {e}")
            raise

    print(f"\n{'=' * 70}")
    print("固定超胞枚举生成")
    print(f"{'=' * 70}")
    print(f"  目标超胞: {n_target} 原子")
    print(f"  ClusterSpace 原胞: {n_prim} 原子")
    print(f"  需要倍数: {multiplier_needed:.1f}")
    print(f"  max_size 参数: {max_size}")

    if not abs(multiplier_needed - round(multiplier_needed)) < Tolerances.MULTIPLIER_CHECK:
        print(f"\n  ⚠ 警告: 超胞原子数 {n_target} 不是原胞 {n_prim} 的整数倍")
        print(f"  建议: 调整 supercell_matrix 使原子数为 {n_prim} 的整数倍")

    print("\n  开始枚举搜索 (icet generate_sqs_by_enumeration)...")
    start = time.time()

    try:
        sqs_prim = generate_sqs_by_enumeration(
            cluster_space=cs,
            max_size=max_size,
            target_concentrations=target_concentrations,
            include_smaller_cells=False,
            pbc=(True, True, True),
        )
    except Exception as e:
        print(f"  ✗ 枚举失败: {e}")
        raise RuntimeError(f"SQS 枚举失败: {e}") from e

    elapsed = time.time() - start
    n_sqs = len(sqs_prim)

    print(f"  ✓ 枚举完成: {n_sqs} 原子 (耗时 {elapsed:.2f} 秒)")

    if n_sqs != n_target:
        print(f"\n  ✗ 错误: 枚举结果 ({n_sqs} 原子) ≠ 目标超胞 ({n_target} 原子)")
        print(f"  原因: max_size={max_size} 时无法生成精确 {n_target} 原子的结构")
        print("  建议: 调整 max_size 或 supercell_matrix")
        raise ValueError(f"原子数不匹配: {n_sqs} != {n_target}")

    # 找出原胞中的无序位点
    disordered_site_indices_in_prim = [
        i for i, cs_list in enumerate(prim_chemical_symbols) if len(cs_list) > 1
    ]

    if not disordered_site_indices_in_prim:
        print("  ⚠ 警告: 未发现无序位点，直接返回用户超胞")
        return user_supercell.copy(), sqs_prim, elapsed

    # 提取占据信息
    n_prim_cells = n_sqs // n_prim
    occupations = []
    sqs_symbols = sqs_prim.get_chemical_symbols()

    for cell_idx in range(n_prim_cells):
        for site_idx in disordered_site_indices_in_prim:
            atom_idx = cell_idx * n_prim + site_idx
            occupations.append(sqs_symbols[atom_idx])

    print(f"  提取了 {len(occupations)} 个无序位点 occupation")

    # 获取用户超胞的无序位点
    user_chemical_symbols = doping_info.get("chemical_symbols", [])
    n_user_atoms_per_cell = len(user_chemical_symbols)
    n_user_cells = n_target // n_user_atoms_per_cell

    user_disordered_indices = []
    for cell_idx in range(n_user_cells):
        for site_idx, cs_list in enumerate(user_chemical_symbols):
            if len(cs_list) > 1:
                user_disordered_indices.append(cell_idx * n_user_atoms_per_cell + site_idx)

    print(f"  用户超胞有 {len(user_disordered_indices)} 个无序位点")

    if len(occupations) != len(user_disordered_indices):
        print(
            f"\n  ✗ 错误: occupation 数量 ({len(occupations)}) "
            f"≠ 用户无序位点数 ({len(user_disordered_indices)})"
        )
        print("  原因: 原胞与常规晶胞的无序位点比例不匹配")
        print("  建议: 检查 dop.in 配置，确保与 ClusterSpace 一致")
        raise ValueError(
            f"Occupation 数量不匹配: " f"{len(occupations)} != {len(user_disordered_indices)}"
        )

    # 构建最终 SQS
    user_symbols = list(user_supercell.get_chemical_symbols())
    for idx, occ in zip(user_disordered_indices, occupations):
        user_symbols[idx] = occ

    sqs = Atoms(
        symbols=user_symbols,
        scaled_positions=user_supercell.get_scaled_positions(),
        cell=user_cell,
        pbc=True,
    )

    print("  ✓ 已映射到用户超胞晶格")
    print(f"  ✓ 替换了 {len(occupations)} 个无序位点")

    return sqs, sqs_prim, elapsed


def evaluate_and_report_sqs_quality(
    cs: ClusterSpace, sqs: Atoms, doping_info: dict[str, Any], elapsed: float, sc_mult: int
) -> tuple[float, str, bool]:
    """
    评估并报告 SQS 质量。

    Args:
        cs: ClusterSpace 对象
        sqs: SQS 结构
        doping_info: 掺杂信息
        elapsed: 生成耗时
        sc_mult: 超胞倍数

    Returns:
        tuple: (偏差值, 质量评级, 是否通过)
    """
    target_concentrations = doping_info.get("target_concentrations", {})
    deviation = calculate_cv_deviation(cs, sqs, target_concentrations=target_concentrations)

    n_atoms = len(sqs)
    n_disordered = doping_info.get("n_disordered", 0) * sc_mult

    quality, passed, context = evaluate_sqs_quality(
        deviation, n_atoms, n_disordered, target_concentrations
    )

    print(f"\n{'=' * 70}")
    print("SQS 质量评估")
    print(f"{'=' * 70}")
    print(f"  团簇向量偏差: {deviation:.6f}")
    print(f"  质量评级: {quality}")
    if context:
        print(f"  评估: {context}")

    return deviation, quality, passed


def save_sqs_results(sqs: Atoms, sqs_data: dict[str, Any], max_size: int, output_dir: Path) -> None:
    """
    保存 SQS 结果到文件。

    Args:
        sqs: SQS 结构
        sqs_data: 元数据字典
        max_size: 原胞倍数
        output_dir: 输出目录
    """
    # JSON 数据
    with open(output_dir / "03_sqs_structure.json", "w") as f:
        json.dump(sqs_data, f, indent=2)
    print("\n  结构数据已保存")

    # 按元素排序的 VASP 格式
    sorted_atoms = sorted(zip(sqs.get_chemical_symbols(), sqs.positions), key=lambda x: x[0])
    sorted_symbols = [a[0] for a in sorted_atoms]
    sorted_positions = np.array([a[1] for a in sorted_atoms])

    sorted_sqs = Atoms(
        symbols=sorted_symbols, positions=sorted_positions, cell=sqs.cell, pbc=sqs.pbc
    )

    vasp_file = output_dir / f"SQS_enum_{max_size}x.vasp"
    write(str(vasp_file), sorted_sqs, format="vasp", direct=True)
    print(f"  VASP: {vasp_file}")

    cif_file = output_dir / f"SQS_enum_{max_size}x.cif"
    write(str(cif_file), sqs, format="cif")
    print(f"  CIF: {cif_file}")


def main() -> int:
    """CLI 入口（向后兼容）"""
    return run()


def run() -> int:
    """
    生成 SQS（枚举法）。可导入调用。"""
    print("=" * 70)
    print("Step 2a: SQS Generation (Enumeration)")
    print("=" * 70)
    print()

    # 加载 ClusterSpace
    cs_file = Path(FileNames.CLUSTERSPACE)
    if not cs_file.exists():
        print("✗ Error: ClusterSpace 文件未找到。请先运行步骤 1。")
        return 1

    print("Loading ClusterSpace...")
    try:
        cs = ClusterSpace.read(str(cs_file))
    except Exception as e:
        print(f"✗ 加载 ClusterSpace 失败: {e}")
        return 1

    prim = cs.primitive_structure
    prim_atoms = len(prim)
    print("  ClusterSpace 已加载")
    print(f"  原胞: {prim_atoms} 原子 ({prim.get_chemical_formula()})")

    # 加载掺杂信息
    doping_file = Path(FileNames.DOPING_INFO)
    if not doping_file.exists():
        print("✗ Error: doping_info 文件未找到。请先运行步骤 1。")
        return 1

    try:
        with open(doping_file, "r") as f:
            doping_info = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ 解析 doping_info 失败: {e}")
        return 1

    target_concentrations = doping_info.get("target_concentrations", {})

    print("\n结构信息:")
    print(f"  ClusterSpace原胞: {prim_atoms} 原子 ({prim.get_chemical_formula()})")
    print(f"  无序位点: {doping_info.get('n_disordered', 0)}")

    if target_concentrations:
        print("\n目标浓度:")
        for group, conc in target_concentrations.items():
            print(f"  {group}: {conc}")

    # 加载配置
    config_file = Path(FileNames.CONFIG)
    sqs_config: dict[str, Any] = {}
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            sqs_config = config.get("sqs", {})
        except json.JSONDecodeError as e:
            print(f"⚠ 警告: 解析 config.json 失败: {e}，使用默认配置")

    max_size: int = sqs_config.get("max_size", 8)
    include_smaller = sqs_config.get("include_smaller_cells", False)

    expected_atoms = prim_atoms * max_size

    print("\n枚举参数:")
    print(f"  max_size: {max_size} (原胞倍数)")
    print(f"  目标原子数: {expected_atoms} ({prim_atoms} × {max_size})")
    print(f"  include_smaller_cells: {include_smaller}")
    print()

    # 直接调用 icet 枚举法
    print("开始枚举...")
    start = time.time()
    try:
        sqs = generate_sqs_by_enumeration(
            cluster_space=cs,
            max_size=max_size,
            target_concentrations=target_concentrations,
            include_smaller_cells=include_smaller,
            pbc=(True, True, True),
        )
        elapsed = time.time() - start
    except Exception as e:
        print(f"\n✗ 枚举失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    n_sqs = len(sqs)
    print(f"✓ 枚举完成: {n_sqs} 原子 (耗时 {elapsed:.2f} 秒)")

    if n_sqs != expected_atoms and not include_smaller:
        print(f"⚠ 警告: 实际原子数 ({n_sqs}) 与期望值 ({expected_atoms}) 不符")

    # 评估质量
    deviation, quality, passed = evaluate_and_report_sqs_quality(
        cs, sqs, doping_info, elapsed, max_size
    )

    # 元素分布统计
    print("\nSQS 结构信息:")
    print(f"  总原子数: {len(sqs)}")
    print(f"  化学式: {sqs.get_chemical_formula()}")

    symbols = sqs.get_chemical_symbols()
    unique = sorted(set(symbols))
    print("\n  元素分布:")
    for sym in unique:
        count = symbols.count(sym)
        frac = count / len(sqs) * 100
        print(f"    {sym}: {count} ({frac:.1f}%)")

    # 保存结果
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    sqs_data: dict[str, Any] = {
        "cell": np.array(sqs.cell).tolist(),
        "positions": np.array(sqs.positions).tolist(),
        "numbers": sqs.numbers.tolist(),
        "n_atoms": len(sqs),
        "formula": sqs.get_chemical_formula(),
        "max_size": max_size,
        "method": "enumeration",
        "deviation": float(deviation),
        "quality": quality,
        "generation_time": elapsed,
    }

    save_sqs_results(sqs, sqs_data, max_size, output_dir)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
