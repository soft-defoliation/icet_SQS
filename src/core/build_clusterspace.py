#!/usr/bin/env python3
"""
01_build_clusterspace.py
步骤1：从带标注的POSCAR构建ClusterSpace
直接从dop.in读取掺杂信息，无需额外配置
"""

import json
import sys
from pathlib import Path
from ase import Atoms
from icet import ClusterSpace
from icet.input_output.logging_tools import set_log_config
from collections import OrderedDict

set_log_config(level='WARNING')

from src.constants import FileNames

def parse_labeled_poscar(poscar_file):
    """
    读取带掺杂标注的POSCAR
    格式: x y z Element=conc1,Element2=conc2 # index N
    
    改进: 不依赖头信息的元素数量声明，直接从坐标行读取
    
    返回:
        structure: ASE Atoms对象
        chemical_symbols: 列表，每个元素是允许的元素列表
        target_concentrations: 字典，用于SQS生成
    """
    with open(poscar_file, 'r') as f:
        lines = f.readlines()
    
    # 读取头部信息（只读晶格，不读元素数量）
    scale = float(lines[1].strip())
    
    # 晶格向量
    lattice = []
    for i in range(2, 5):
        parts = lines[i].strip().split()
        lattice.append([float(x) * scale for x in parts])
    
    # 忽略第5-6行的元素和数量声明
    # 直接从第8行开始读取坐标
    
    coords = []
    chemical_symbols = []
    target_concentrations = {}
    disordered_groups = {}
    
    print(f"  开始读取坐标...")
    
    for line_idx, line in enumerate(lines[8:], start=8):
        line = line.strip()
        
        # 跳过空行和注释行
        if not line or line.startswith('#'):
            continue
            
        parts = line.split()
        if len(parts) < 3:
            continue
        
        # 提取坐标
        try:
            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
            coords.append([x, y, z])
        except ValueError:
            continue
        
        # 查找掺杂标注（在坐标后面的部分）
        label = None
        for part in parts[3:]:
            if '=' in part and not part.startswith('#'):
                label = part
                break
        
        # 解析标注
        if label and ',' in label:
            # 多元素掺杂，如 K=0.5,Na=0.5
            allowed_elements = []
            concentration_dict = {}
            
            for item in label.split(','):
                if '=' in item:
                    try:
                        elem, conc = item.split('=')
                        elem = elem.strip()
                        conc = float(conc.strip())
                        allowed_elements.append(elem)
                        concentration_dict[elem] = conc
                    except ValueError:
                        continue
            
            if allowed_elements:
                chemical_symbols.append(allowed_elements)
                
                # 按第一元素分组
                group_key = allowed_elements[0]
                if group_key not in disordered_groups:
                    disordered_groups[group_key] = {
                        'indices': [],
                        'concentration': concentration_dict
                    }
                disordered_groups[group_key]['indices'].append(len(coords) - 1)
            else:
                # 标注解析失败，设为有序（用标注的第一个元素）
                elem = label.split('=')[0].strip() if '=' in label else 'X'
                chemical_symbols.append([elem])
                
        elif label and '=' in label:
            # 单元素标注，如 Nb=1.0
            elem = label.split('=')[0].strip()
            chemical_symbols.append([elem])
        else:
            # 没有标注，报错（必须提供标注）
            raise ValueError(f"第{line_idx+1}行缺少元素标注！格式: x y z Element=1.0")
    
    print(f"  读取了 {len(coords)} 个原子")
    print(f"  其中无序位点: {sum(1 for cs in chemical_symbols if len(cs) > 1)} 个")
    
    # 构建target_concentrations
    for i, (group_key, group_info) in enumerate(disordered_groups.items()):
        sublattice_name = chr(ord('A') + i)  # A, B, C, ...
        target_concentrations[sublattice_name] = group_info['concentration']
    
    # 创建ASE Atoms对象
    symbols = []
    for cs in chemical_symbols:
        symbols.append(cs[0])
    
    structure = Atoms(
        symbols=symbols,
        scaled_positions=coords,  # 使用分数坐标（Direct坐标）
        cell=lattice,
        pbc=True
    )
    
    return structure, chemical_symbols, target_concentrations

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
    
    structure, chemical_symbols, target_concentrations = parse_labeled_poscar(labeled_poscar)
    n_disordered = sum(1 for cs in chemical_symbols if len(cs) > 1)
    n_ordered = len(chemical_symbols) - n_disordered
    
    print(f"  {structure.get_chemical_formula()} | {len(structure)} 原子 | "
          f"{n_disordered} 无序 + {n_ordered} 有序")
    
    if target_concentrations:
        conc_list = [f"{g}={conc}" for g, conc in target_concentrations.items()]
        print(f"  目标浓度: {', '.join(conc_list)}")
        
        errors = validate_concentrations(target_concentrations)
        if errors:
            for error in errors:
                print(f"  ✗ {error}")
            raise BuildClusterSpaceError("浓度验证失败")
    
    if Path(FileNames.CONFIG).exists():
        with open(FileNames.CONFIG, 'r') as f:
            config = json.load(f)
        cutoffs = config.get('cluster_space', {}).get('cutoffs', [5.0])
    else:
        cutoffs = [5.0]
    
    print(f"  cutoffs={cutoffs} Å", end=" ")
    try:
        cs = ClusterSpace(
            structure=structure,
            cutoffs=cutoffs,
            chemical_symbols=chemical_symbols,
            symprec=1e-3,
            position_tolerance=0.1
        )
        print("→ ✓")
    except Exception as e:
        print(f"→ ✗ {e}")
        raise BuildClusterSpaceError(f"ClusterSpace构建失败: {e}") from e
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    cs.write(str(Path(FileNames.CLUSTERSPACE)))
    
    doping_info = {
        'chemical_symbols': chemical_symbols,
        'target_concentrations': target_concentrations,
        'n_atoms': len(structure),
        'n_disordered': n_disordered,
        'n_ordered': n_ordered,
        'cutoffs': cutoffs,
        'structure_file': labeled_poscar
    }
    with open(FileNames.DOPING_INFO, 'w') as f:
        json.dump(doping_info, f, indent=2)
    print()


def main():
    """CLI 入口（向后兼容）"""
    try:
        run()
    except BuildClusterSpaceError as e:
        print(f"\n错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()