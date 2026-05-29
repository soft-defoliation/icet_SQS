#!/usr/bin/env python3
"""
03_generate_sqs_mc.py
MC方法生成SQS (迭代优化，类似ATAT)

特点:
  - 基于用户定义的 dop.in 结构
  - 参数: supercell_matrix (具体超胞矩阵)
  - 结果尺寸固定 (按配置)
  - 迭代优化，直到偏差达标或迭代次数用完
"""

import json
import sys
from pathlib import Path
import time
import numpy as np
from icet import ClusterSpace
from icet.tools.structure_generation import generate_sqs_from_supercells
from icet.input_output.logging_tools import set_log_config
from ase.io import write
from ase.build import make_supercell
from ase import Atoms

set_log_config(level='WARNING')

from src.utils.quality_utils import (
    calculate_cv_deviation,
    evaluate_sqs_quality,
    estimate_achievable_deviation,
    get_system_size_recommendation,
)
from src.parser import StructureParser
from src.constants import FileNames


def generate_sqs_iterative(cs, supercell, target_conc, tolerance=0.001, max_iter=5,
                           progress_file=None, n_disordered=None, early_stop_no_improve=3):
    best_sqs = None
    best_deviation = float('inf')
    no_improve_count = 0
    
    for iteration in range(max_iter):
        try:
            sqs = generate_sqs_from_supercells(
                cluster_space=cs, supercells=[supercell],
                target_concentrations=target_conc,
                T_start=5.0, T_stop=0.001, random_seed=iteration
            )
            deviation = calculate_cv_deviation(cs, sqs, target_concentrations=target_conc,
                                                use_icet_comparison=False)
            quality, passed, _ = evaluate_sqs_quality(deviation, len(supercell), n_disordered, target_conc)
            
            marker = "✓" if deviation < best_deviation - 1e-6 else " "
            print(f"  iter {iteration+1}/{max_iter}: dev={deviation:.6f} {quality} {marker}")
            
            if deviation < best_deviation - 1e-6:
                best_sqs, best_deviation = sqs, deviation
                no_improve_count = 0
                if progress_file:
                    save_progress(progress_file, best_sqs, best_deviation, iteration, [])
            else:
                no_improve_count += 1
            
            if best_deviation < tolerance:
                break
            if no_improve_count >= early_stop_no_improve:
                break
        except Exception as e:
            print(f"  iter {iteration+1}/{max_iter}: ✗ {e}")
            continue
    
    return best_sqs, best_deviation, iteration + 1


def save_progress(progress_file, sqs, deviation, iteration, history):
    try:
        import pickle
        progress_data = {
            'sqs_positions': sqs.positions.tolist(),
            'sqs_numbers': sqs.numbers.tolist(),
            'sqs_cell': sqs.cell.tolist(),
            'deviation': float(deviation),
            'iteration': iteration,
            'history': history,
            'timestamp': time.time()
        }
        with open(progress_file, 'wb') as f:
            pickle.dump(progress_data, f)
    except OSError:
        print(f"  警告: 进度保存失败 ({progress_file})", file=sys.stderr)


def run():
    print("Step 2/4: MC 方法生成 SQS")
    print("-" * 50)

    if not Path(FileNames.CLUSTERSPACE).exists():
        raise RuntimeError("未找到 ClusterSpace，请先运行步骤1")

    cs = ClusterSpace.read(str(Path(FileNames.CLUSTERSPACE)))
    with open(FileNames.DOPING_INFO, 'r') as f:
        doping_info = json.load(f)
    target_concentrations = doping_info.get('target_concentrations', {})

    if Path(FileNames.CONFIG).exists():
        with open(FileNames.CONFIG, 'r') as f:
            sqs_config = json.load(f).get('sqs', {})
    else:
        sqs_config = {}

    supercell_matrix = sqs_config.get('supercell_matrix', [[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    max_size = supercell_matrix[0][0] * supercell_matrix[1][1] * supercell_matrix[2][2]
    tolerance = sqs_config.get('tolerance', 0.001)
    max_iter = sqs_config.get('max_iterations', 5)

    dop_in_file = StructureParser.find_dop_in()
    original_structure, original_lattice, _ = StructureParser().parse_for_supercell(dop_in_file)

    n_mult = f"{supercell_matrix[0][0]}x{supercell_matrix[1][1]}x{supercell_matrix[2][2]}"
    supercell = make_supercell(original_structure, np.array(supercell_matrix))
    print(f"  超胞 {n_mult} ({len(original_structure)}→{len(supercell)} 原子) | "
          f"tolerance={tolerance} | max_iter={max_iter}")

    n_disordered = doping_info.get('n_disordered')
    if n_disordered:
        n_disordered *= max_size

    start = time.time()
    sqs, deviation, n_iter = generate_sqs_iterative(
        cs=cs, supercell=supercell, target_conc=target_concentrations,
        tolerance=tolerance, max_iter=max_iter,
        progress_file=Path(FileNames.PROGRESS_PKL) if sqs_config.get('save_progress', True) else None,
        n_disordered=n_disordered,
        early_stop_no_improve=sqs_config.get('early_stop_no_improve', 3)
    )
    elapsed = time.time() - start

    if sqs is None:
        raise RuntimeError("MC 迭代未能生成有效 SQS 结构")

    # 修正晶格
    expected_lattice = np.array(original_lattice) * np.diag([supercell_matrix[i][i] for i in range(3)])
    sqs = Atoms(symbols=sqs.get_chemical_symbols(), scaled_positions=sqs.get_scaled_positions(),
                cell=expected_lattice, pbc=True)

    print(f"  → {sqs.get_chemical_formula()} | {len(sqs)} 原子 | "
          f"偏差={deviation:.6f} | 迭代={n_iter} | {elapsed:.1f}s")

    # 保存结果
    sqs_data = {
        'cell': np.array(sqs.cell).tolist(),
        'positions': np.array(sqs.positions).tolist(),
        'numbers': sqs.numbers.tolist(),
        'n_atoms': len(sqs), 'formula': sqs.get_chemical_formula(),
        'supercell_matrix': supercell_matrix, 'max_size': max_size,
        'method': 'mc', 'deviation': float(deviation),
        'n_iterations': n_iter, 'generation_time': elapsed
    }
    with open(FileNames.SQS_STRUCTURE, 'w') as f:
        json.dump(sqs_data, f, indent=2)

    # VASP + CIF
    symbols, pos = sqs.get_chemical_symbols(), sqs.positions
    sorted_atoms = sorted(zip(symbols, pos), key=lambda x: x[0])
    sorted_sqs = Atoms(symbols=[a[0] for a in sorted_atoms],
                       positions=np.array([a[1] for a in sorted_atoms]),
                       cell=sqs.cell, pbc=sqs.pbc)
    write(f"output/SQS_mc_{max_size}x.vasp", sorted_sqs, format='vasp', direct=True)
    write(f"output/SQS_mc_{max_size}x.cif", sqs, format='cif')
    print()


def main():
    """CLI 入口（向后兼容）"""
    try:
        run()
    except RuntimeError as e:
        print(f"\n错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
