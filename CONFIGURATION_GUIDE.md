# SQS Workflow - 可控参数帮助文档

## 简介

本文档详细说明 SQS (Special Quasirandom Structure) 生成工具中所有可配置的参数。

---

## 配置文件

### 1. config.json - 主配置文件

此文件控制 SQS 生成的所有技术参数。

#### 1.1 ClusterSpace 配置 (`cluster_space`)

ClusterSpace 是 SQS 生成的核心组件，用于描述晶体的团簇展开。

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `cutoffs` | float[] | `[5.0]` | 1.0 - 20.0 Å | 团簇截断半径列表。可以设置多个截断半径，用于构建不同尺度的团簇。较大的值包含更多结构信息，但计算成本更高。 |
| `symprec` | float | `0.001` | 1e-6 - 1.0 | 对称性容差。用于判断晶体对称性的精度阈值。较小的值要求更严格的对称性匹配。 |
| `position_tolerance` | float | `0.1` | 0.01 - 1.0 | 位置容差。判断原子位置是否相同的精度阈值。 |

**示例：**
```json
{
  "cluster_space": {
    "cutoffs": [5.0],
    "symprec": 0.001,
    "position_tolerance": 0.1
  }
}
```

#### 1.2 SQS 生成配置 (`sqs`)

控制 SQS 生成过程的参数。

**通用参数：**

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `method` | string | `"enumeration"` | `enumeration` / `mc` | 生成方法。`enumeration` (枚举法) 适合中小体系，寻找全局最优；`mc` (蒙特卡洛) 适合精确控制结构大小。 |
| `pbc` | bool[] | `[true, true, true]` | - | 周期边界条件。三个布尔值分别控制 x, y, z 方向的周期性。 |
| `tolerance` | float | `0.001` | 0.0001 - 1.0 | 目标偏差容差。SQS 优化目标为团簇向量与理想随机分布的偏差小于此值。 |
| `random_seed` | int/null | `null` | - | 随机种子。设置固定值可使结果可复现。留空或不设置则使用随机种子。 |

**枚举法专用参数：**

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `max_size` | int | `8` | 1 - 200 | 原胞最大倍数。控制搜索的超胞尺寸上限。较大的值提供更多可能的结构，但搜索空间指数增长。 |
| `include_smaller_cells` | bool | `false` | - | 允许返回更小的优化结构。如果开启，当更小的超胞能达到目标偏差时，会返回更小的结构而非最大的。 |

**MC方法专用参数：**

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `supercell_matrix` | int[][] | `[[2,0,0],[0,2,0],[0,0,2]]` | - | 超胞扩胞矩阵。3x3 对角矩阵，定义超胞相对于原胞的倍数。目前只支持对角矩阵。 |
| `max_iterations` | int | `5` | 1 - 100 | 最大迭代次数。MC 模拟的退火循环次数。 |
| `early_stop_no_improve` | int | `3` | 1 - 20 | 连续无改进停止阈值。当连续 N 次迭代没有改进时提前停止。 |
| `save_progress` | bool | `true` | - | 保存优化进度。保存中间状态以便恢复或分析。 |
| `T_start` | float | `5.0` | 0.01 - 100.0 | MC 初始温度。模拟退火的起始温度，较高温度允许接受更多不利移动。 |
| `T_stop` | float | `0.001` | 0.0001 - 10.0 | MC 终止温度。模拟退火的终止温度，较低温度使系统趋于稳定。 |

**示例：**
```json
{
  "sqs": {
    "method": "enumeration",
    "max_size": 8,
    "include_smaller_cells": false,
    "tolerance": 0.001,
    "random_seed": null
  }
}
```

#### 1.3 输出配置 (`output`)

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `directory` | string | `"output"` | - | 输出目录路径。所有输出文件将保存到此目录。 |
| `formats` | string[] | `["vasp", "cif"]` | 见下方 | 输出格式列表。支持多种格式同时输出。 |
| `filename_prefix` | string | `"SQS"` | - | 文件名前缀。生成的文件名将以此前缀开头。 |
| `save_intermediate` | bool | `true` | - | 保存中间文件。保存 ClusterSpace、掺杂信息、SQS 结构等中间结果。 |

**支持的输出格式：**
- `vasp` - VASP POSCAR 格式
- `cif` - Crystallographic Information File
- `lammps-data` - LAMMPS 数据文件
- `json` - JSON 格式
- `xyz` - XYZ 坐标格式
- `extxyz` - 扩展 XYZ 格式

**示例：**
```json
{
  "output": {
    "directory": "output",
    "formats": ["vasp", "cif"],
    "filename_prefix": "SQS",
    "save_intermediate": true
  }
}
```

#### 1.4 验证配置 (`validation`)

| 参数名 | 类型 | 默认值 | 取值范围 | 说明 |
|--------|------|--------|----------|------|
| `check_correlation` | bool | `true` | - | 检查团簇向量相关性。验证生成的 SQS 是否具有正确的团簇相关性。 |
| `tolerance` | float | `0.001` | 0.0001 - 1.0 | 验证容差。质量评估时判断是否通过的质量阈值。 |

**质量评估标准（基于 van de Walle 2013）：**
- **优秀** (< 0.001): 达到理想 SQS 质量 ✅
- **良好** (< 0.01): 高质量 SQS ✓
- **可用** (< 0.10): 可接受的 SQS 质量
- **可接受** (< 0.30): 小系统或不对称浓度的物理限制
- **失败** (≥ 0.30): 质量不达标，建议增大超胞或调整参数 ❌

**示例：**
```json
{
  "validation": {
    "check_correlation": true,
    "tolerance": 0.001
  }
}
```

---

### 2. dop.in - 掺杂配置文件

`dop.in` 文件定义晶体结构中的掺杂位点和浓度。文件格式基于 VASP POSCAR，但添加了掺杂标记。

#### 文件格式

```
dop.in                          # 注释行，可为任意文字
1.0                             # 晶格常数缩放因子
  a11  a12  a13                 # 晶格向量第一行
  a21  a22  a23                 # 晶格向量第二行
  a31  a32  a33                 # 晶格向量第三行
  Nb  O  K  Na                  # 元素符号列表
  2   6  2  2                   # 各元素的原子数量
Direct                          # 坐标类型 (Direct/Cartesian)
  0.0  0.5  0.5  Nb=1.0         # 原子坐标 + 掺杂标记
  0.5  0.5  0.0  Nb=1.0
  0.25 0.5  0.22 O=1.0
  ...
  0.0  0.0  0.0  K=0.5,Na=0.5   # 混合掺杂：K和Na各占50%
```

#### 掺杂标记格式

掺杂标记位于每行原子坐标之后，格式为：

```
元素1=浓度1[,元素2=浓度2,...]
```

**规则：**
- 单元素位点: `Nb=1.0` - 该位点固定为 Nb
- 混合掺杂: `K=0.5,Na=0.5` - 该位点为 K 和 Na 的混合物，各占 50%
- 浓度总和必须等于 1.0
- 允许的元素种类不限，但至少需要一种

#### 掺杂位点索引

在生成的 `atom_index_guide.txt` 文件中，每个原子都有对应的索引，可用于精确控制掺杂：

```
Atom Index Reference Guide
==========================

Index 0: Nb=1.0 (site 0)
Index 1: Nb=1.0 (site 1)
Index 8: K=0.5,Na=0.5 (site 8)
...
```

---

## 参数配置级别

系统提供三种配置级别，适用于不同的使用场景：

### 快速模式 (Quick)

仅配置最基本的参数，适合快速尝试或简单系统。

**可调参数：**
- 团簇截断半径 (`cutoffs`)
- 最大原胞倍数 (`max_size`) 或 超胞矩阵 (`supercell_matrix`)

### 标准模式 (Standard)

配置常用参数，适合大多数场景。

**可调参数（除快速模式外）：**
- 目标偏差容差 (`tolerance`)
- MC 方法：最大迭代次数、无改进停止次数、初始/终止温度
- 枚举法：是否允许更小结构

### 专家模式 (Expert)

配置所有高级参数，适合精细调优。

**可调参数（除标准模式外）：**
- ClusterSpace 高级参数（多个截断半径、容差设置）
- 随机种子 (`random_seed`)
- 周期边界条件 (`pbc`)
- 保存优化进度 (`save_progress`)
- 输出目录和文件名前缀
- 验证相关参数

---

## 完整配置示例

### 枚举法配置示例

```json
{
  "cluster_space": {
    "cutoffs": [5.0],
    "symprec": 0.001,
    "position_tolerance": 0.1
  },
  "sqs": {
    "max_size": 8,
    "include_smaller_cells": false,
    "pbc": [true, true, true],
    "tolerance": 0.001,
    "random_seed": null
  },
  "output": {
    "directory": "output",
    "formats": ["vasp", "cif"],
    "filename_prefix": "SQS",
    "save_intermediate": true
  },
  "validation": {
    "check_correlation": true,
    "tolerance": 0.001
  }
}
```

### MC方法配置示例

```json
{
  "cluster_space": {
    "cutoffs": [5.0],
    "symprec": 0.001,
    "position_tolerance": 0.1
  },
  "sqs": {
    "supercell_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
    "pbc": [true, true, true],
    "tolerance": 0.001,
    "random_seed": 42,
    "max_iterations": 5,
    "early_stop_no_improve": 3,
    "save_progress": true,
    "T_start": 5.0,
    "T_stop": 0.001
  },
  "output": {
    "directory": "output",
    "formats": ["vasp", "cif", "lammps-data"],
    "filename_prefix": "SQS_MC",
    "save_intermediate": true
  },
  "validation": {
    "check_correlation": true,
    "tolerance": 0.001
  }
}
```

---

## 输出文件说明

根据配置，系统会生成以下文件：

### 主要输出文件

| 文件 | 说明 |
|------|------|
| `SQS_FINAL.vasp` | 最终生成的 SQS 结构（VASP 格式） |
| `output/SUMMARY.txt` | 生成摘要信息 |
| `output/QUALITY_REPORT.txt` | 详细质量评估报告 |
| `output/quality_validation.json` | 质量评估数据（JSON 格式） |

### 中间文件（当 `save_intermediate` 为 true）

| 文件 | 说明 |
|------|------|
| `output/02_clusterspace.cs` | ClusterSpace 对象（二进制） |
| `output/02_doping_info.json` | 掺杂信息 |
| `output/03_sqs_structure.json` | SQS 结构数据 |
| `output/sqs_optimization_progress.pkl` | MC 优化进度（MC 方法） |

---

## 使用建议

### 选择生成方法

**枚举法适用场景：**
- 中小尺寸体系（< 100 原子）
- 需要全局最优解
- 对结构大小没有严格要求
- 掺杂浓度对称

**MC方法适用场景：**
- 大尺寸体系（> 100 原子）
- 需要精确控制超胞大小
- 与实验晶胞尺寸匹配
- 计算资源受限

### 参数调优建议

1. **截断半径 (`cutoffs`)**
   - 从 5.0 Å 开始尝试
   - 如果质量不达标，可增大到 8.0 或 10.0 Å
   - 注意：增大截断半径会显著增加计算时间

2. **目标偏差 (`tolerance`)**
   - 默认 0.001 是良好的起点
   - 如需更高质量，可减小到 0.0001
   - 对于困难体系，可适当放宽到 0.01

3. **超胞大小 (`max_size` 或 `supercell_matrix`)**
   - 对于非 1:1 掺杂比例，需要足够大的超胞
   - 如果质量不达标，尝试增大超胞
   - 对于 75:25 比例，建议至少 2x2x2 超胞

4. **MC 温度参数**
   - 初始温度 `T_start`：通常设为 5.0
   - 终止温度 `T_stop`：通常设为 0.001
   - 对于复杂体系，可尝试更高的 `T_start` (10-20)
   - 对于需要更精细优化的体系，可尝试更低的 `T_stop` (0.0001)

---

## 故障排除

### 常见问题及解决

**问题：质量评估显示"失败"**
- 增大 `max_size` 或超胞矩阵尺寸
- 检查 `dop.in` 中的浓度设置是否合理
- 增大 `cutoffs` 以包含更多结构信息

**问题：MC 方法收敛慢**
- 增加 `max_iterations`
- 调整 `T_start` 和 `T_stop` 到更合适的范围
- 减小 `early_stop_no_improve` 以提前停止

**问题：掺杂位点识别错误**
- 检查 `dop.in` 文件的坐标精度
- 确保原子索引与 `atom_index_guide.txt` 一致
- 调整 `position_tolerance` 参数

---

## 参考

- [icet 文档](https://icet.materialsmodeling.org/)
- van de Walle et al., *Efficient stochastic generation of special quasirandom structures*, Calphad 42, 13-18 (2013)
