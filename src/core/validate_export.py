"""Step 3: 导出 SQS 最终结果"""

import json
import numpy as np
from pathlib import Path
from ase import Atoms
from ase.io import write

from src.constants import FileNames


def run():
    """导出 SQS 最终结果"""
    with open(FileNames.SQS_STRUCTURE, 'r') as f:
        sqs_data = json.load(f)

    sqs = Atoms(positions=sqs_data['positions'], numbers=sqs_data['numbers'],
                cell=sqs_data['cell'], pbc=True)

    # 写入 SUMMARY.txt
    symbols = sqs.get_chemical_symbols()
    lines = [f"SQS: {sqs_data['formula']} | {sqs_data['n_atoms']} atoms | "
             f"method={sqs_data.get('method','?')} | "
             f"deviation={sqs_data.get('deviation','?')}"]
    lines.append("Element distribution:")
    for sym in sorted(set(symbols)):
        lines.append(f"  {sym}: {symbols.count(sym)}")
    Path(FileNames.SUMMARY).parent.mkdir(exist_ok=True)
    Path(FileNames.SUMMARY).write_text('\n'.join(lines))

    # 按元素排序导出 SQS_FINAL.vasp
    sorted_atoms = sorted(zip(symbols, sqs.positions), key=lambda x: x[0])
    sorted_sqs = Atoms(symbols=[a[0] for a in sorted_atoms],
                       positions=np.array([a[1] for a in sorted_atoms]),
                       cell=sqs.cell, pbc=True)
    write(FileNames.FINAL_VASP, sorted_sqs, format='vasp', direct=True)

    print(f"Step 3/4: 导出结果")
    print(f"-" * 50)
    print(f"  {sqs_data['formula']} | {sqs_data['n_atoms']} 原子 | "
          f"{sqs_data.get('method','?')} | {sqs_data.get('generation_time',0):.1f}s")
    print(f"  → {FileNames.FINAL_VASP} | output/ (中间文件) | "
          f"output/QUALITY_REPORT.txt (详细报告)")
    print()


def main():
    run()

if __name__ == '__main__':
    main()
