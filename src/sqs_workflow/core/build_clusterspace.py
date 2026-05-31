#!/usr/bin/env python3
"""
01_build_clusterspace.py
步骤1：从带标注的POSCAR构建ClusterSpace
直接从dop.in读取掺杂信息，无需额外配置
"""

import json
import sys
from pathlib import Path
from icet import ClusterSpace
from icet.input_output.logging_tools import set_log_config

set_log_config(level="WARNING")

from sqs_workflow.constants import FileNames  # noqa: E402
from sqs_workflow.parser import StructureParser  # noqa: E402


def validate_concentrations(target_concentrations):
    """验证浓度总和是否为1.0"""
    errors = []

    for group_name, conc_dict in target_concentrations.items():
        total = sum(conc_dict.values())
        if abs(total - 1.0) > 1e-6:
            errors.append(f"组 '{group_name}': 浓度总和={total:.6f} ≠ 1.0")

    return errors


class BuildClusterSpaceError(RuntimeError):
    """ClusterSpace 构建错误"""

    pass


def run():
    """构建 ClusterSpace（可导入调用，异常替代 sys.exit）"""
    print("Step 1/4: 构建 ClusterSpace")
    print("-" * 50)

    labeled_poscar = None
    if Path(FileNames.DOP_IN).exists():
        labeled_poscar = FileNames.DOP_IN
    elif Path(FileNames.DOP_IN_ALT).exists():
        labeled_poscar = FileNames.DOP_IN_ALT
    if not labeled_poscar:
        raise BuildClusterSpaceError("未找到 dop.in")

    parser = StructureParser(Path(labeled_poscar))
    parsed = parser.parse()
    structure = parsed.structure
    chemical_symbols = [site.allowed_elements for site in parsed.sites]
    target_concentrations = parsed.target_concentrations
    n_disordered = parsed.n_disordered
    n_ordered = parsed.n_ordered

    print(
        f"  {structure.get_chemical_formula()} | {len(structure)} 原子 | "
        f"{n_disordered} 无序 + {n_ordered} 有序"
    )

    if target_concentrations:
        conc_list = [f"{g}={conc}" for g, conc in target_concentrations.items()]
        print(f"  目标浓度: {', '.join(conc_list)}")

        errors = validate_concentrations(target_concentrations)
        if errors:
            for error in errors:
                print(f"  ✗ {error}")
            raise BuildClusterSpaceError("浓度验证失败")

    if Path(FileNames.CONFIG).exists():
        with open(FileNames.CONFIG, "r") as f:
            config = json.load(f)
        cutoffs = config.get("cluster_space", {}).get("cutoffs", [5.0])
    else:
        cutoffs = [5.0]

    print(f"  cutoffs={cutoffs} Å", end=" ")
    try:
        cs = ClusterSpace(
            structure=structure,
            cutoffs=cutoffs,
            chemical_symbols=chemical_symbols,
            symprec=1e-3,
            position_tolerance=0.1,
        )
        print("→ ✓")
    except Exception as e:
        print(f"→ ✗ {e}")
        raise BuildClusterSpaceError(f"ClusterSpace构建失败: {e}") from e

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    cs.write(str(Path(FileNames.CLUSTERSPACE)))

    doping_info = {
        "chemical_symbols": chemical_symbols,
        "target_concentrations": target_concentrations,
        "n_atoms": len(structure),
        "n_disordered": n_disordered,
        "n_ordered": n_ordered,
        "cutoffs": cutoffs,
        "structure_file": labeled_poscar,
    }
    with open(FileNames.DOPING_INFO, "w") as f:
        json.dump(doping_info, f, indent=2)
    print()


def main():
    """CLI 入口（向后兼容）"""
    try:
        run()
    except BuildClusterSpaceError as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
