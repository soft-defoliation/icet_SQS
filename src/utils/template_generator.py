#!/usr/bin/env python3
"""
universal_template_generator.py
通用结构模板生成器 - 支持POSCAR和CIF格式

功能：
1. 读取POSCAR或CIF文件
2. 生成带标注的POSCAR模板 (元素=1.0 # index N)
3. 生成原子索引对照表

使用方法：
  python universal_template_generator.py input/POSCAR
  python universal_template_generator.py input/structure.cif

输出：
  - input/dop.in (带标注的掺杂文件)
  - input/atom_index_guide.txt (索引对照表)
"""

import sys
from pathlib import Path
from ase.io import read
from collections import OrderedDict


class UniversalTemplateGenerator:
    """通用模板生成器"""

    def __init__(self, input_file):
        self.input_file = Path(input_file)
        self.structure = None
        self.output_dir = self.input_file.parent

    def load_structure(self):
        """读取结构文件（POSCAR或CIF）"""
        try:
            # ASE自动检测格式
            self.structure = read(str(self.input_file))
            print(f"✓ 成功读取: {self.input_file}")
            print(f"  原子数: {len(self.structure)}")
            print(f"  元素: {sorted(set(self.structure.get_chemical_symbols()))}")
            return True
        except Exception as e:
            print(f"✗ 读取失败: {e}")
            return False

    def generate_labeled_poscar(self):
        """生成带标注的掺杂文件dop.in"""
        output_file = self.output_dir / "dop.in"

        # 获取结构信息
        symbols = self.structure.get_chemical_symbols()
        positions = self.structure.get_scaled_positions()
        cell = self.structure.cell

        with open(output_file, "w") as f:
            # 标题
            f.write("dop.in\n")
            f.write("1.0\n")

            # 晶格向量
            for vec in cell:
                f.write(f"  {vec[0]:20.10f} {vec[1]:20.10f} {vec[2]:20.10f}\n")

            # 统计元素（保持原始顺序）
            elem_count = OrderedDict()
            for sym in symbols:
                elem_count[sym] = elem_count.get(sym, 0) + 1

            # 元素行和数量行
            f.write("  " + "  ".join(elem_count.keys()) + "\n")
            f.write("  " + "  ".join([str(c) for c in elem_count.values()]) + "\n")
            f.write("Direct\n")

            # 带标注的坐标
            for i, (sym, pos) in enumerate(zip(symbols, positions)):
                f.write(
                    f"  {pos[0]:15.9f} {pos[1]:15.9f} " f"{pos[2]:15.9f}   {sym}=1.0  # index {i}\n"
                )

        print(f"✓ 已生成: {output_file}")
        return output_file

    def generate_index_guide(self):
        """生成原子索引对照表"""
        output_file = self.output_dir / "atom_index_guide.txt"

        symbols = self.structure.get_chemical_symbols()
        positions = self.structure.get_scaled_positions()

        lines = []
        lines.append("使用说明：")
        lines.append("  1. 编辑 dop.in 文件")
        lines.append("  2. 将需要掺杂的位置从 '元素=1.0' 改为 '元素1=比例1,元素2=比例2'")
        lines.append("  3. 比例总和必须等于1.0")
        lines.append("")
        lines.append("示例：")
        lines.append("  修改前: K=1.0 → K=0.5,Na=0.5")
        lines.append("  修改后: K=0.5,Na=0.5 (表示K和Na各占50%)")
        lines.append("=" * 80)
        lines.append(
            f"{'Index':<8} | {'Element':<8} | " f"{'Status':<15} | {'Fractional coordinates':<30}"
        )
        lines.append("-" * 80)

        # 每个原子
        elem_stats = {}
        for i, (sym, pos) in enumerate(zip(symbols, positions)):
            coord_str = f"{pos[0]:7.4f} {pos[1]:7.4f} {pos[2]:7.4f}"
            lines.append(f"{i:<8} | {sym:<8} | {coord_str:<30} | {sym}=1.0")

            if sym not in elem_stats:
                elem_stats[sym] = []
            elem_stats[sym].append(i)

        lines.append("-" * 80)
        lines.append("")

        # 统计
        lines.append("Summary by Element:")
        for elem in sorted(elem_stats.keys()):
            indices = elem_stats[elem]
            lines.append(f"  {elem}: indices {min(indices)}-{max(indices)} ({len(indices)} atoms)")

        lines.append("")
        lines.append("=" * 80)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✓ 已生成: {output_file}")
        return output_file


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python universal_template_generator.py <结构文件>")
        print("支持格式: POSCAR, CIF")
        print("")
        print("示例:")
        print("  python universal_template_generator.py input/POSCAR")
        print("  python universal_template_generator.py input/structure.cif")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"错误: 文件不存在: {input_file}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print("通用结构模板生成器")
    print(f"{'='*80}")
    print(f"输入文件: {input_file}\n")

    # 创建生成器并运行
    generator = UniversalTemplateGenerator(input_file)

    if generator.load_structure():
        template_file = generator.generate_labeled_poscar()
        guide_file = generator.generate_index_guide()

        print(f"\n{'='*80}")
        print("生成完成!")
        print(f"{'='*80}")
        print("\n输出文件:")
        print(f"  1. {template_file}")
        print("     (带标注的POSCAR模板)")
        print(f"  2. {guide_file}")
        print("     (原子索引对照表)")
        print("\n下一步:")
        print("  编辑模板文件，修改掺杂配置")
        print("  例如: 将 'K=1.0' 改为 'K=0.5,Na=0.5'")
        print("\n然后运行SQS工作流生成超胞")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
