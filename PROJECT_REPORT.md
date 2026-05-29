# SQS Workflow 项目技术报告

## 目录

1. [引言与背景](#1-引言与背景)
2. [理论基础](#2-理论基础)
3. [工具选型：icet vs ATAT](#3-工具选型icet-vs-atat)
4. [项目架构与实现](#4-项目架构与实现)
5. [示例应用：K₀.₅Na₀.₅NbO₃ 体系](#5-示例应用k₀₅na₀₅nbo₃-体系)
6. [总结与展望](#6-总结与展望)
7. [参考文献](#7-参考文献)

---

## 1. 引言与背景

本章概述无序合金计算中的核心挑战，引出 Special Quasirandom Structure（SQS）的概念、物理意义及其在现代计算材料科学中的应用价值。

### 1.1 无序合金的计算挑战

在材料科学中，大量具有重要应用价值的合金和功能材料属于**无序固溶体**（disordered solid solutions）。这类材料的特征是：在晶格的特定亚晶格位点上，两种或多种原子以随机（或近随机）的方式占据。例如，不锈钢中的 Fe-Cr 合金、锂电池正极材料中的 NMC（Ni-Mn-Co）混合氧化物，以及本报告所关注的 K₀.₅Na₀.₅NbO₃ 无铅压电陶瓷等。

从计算材料学的角度，对这类无序体系进行第一性原理（ab initio）计算面临一个根本性的困难：**密度泛函理论（DFT）需要周期性边界条件**，因此只能处理有限大小的超胞（supercell）。然而，真正完全随机的无序合金只有在无穷大超胞（即热力学极限）中才能被严格描述。如果直接使用较小的超胞来建模，有限的原子数会引入系统性误差——超胞中的原子排列并不能真实反映随机态的统计特征。

一种直观的解决方案是构建尽可能大的超胞。但 DFT 的计算量通常与原子数的三次方成正比（$\mathcal{O}(N^3)$），当超胞原子数超过数百时，计算成本将变得难以承受。这就构成了一个基本矛盾：**需要足够大的超胞来逼近随机态，但计算资源限制了超胞的尺寸**。

Special Quasirandom Structure（SQS）正是在这一背景下被提出的。它通过巧妙的原子排列设计，在有限的超胞尺寸下，尽可能精确地再现完全随机态的短程结构特征，从而为 DFT 计算提供了一个既高效又足够精确的无序合金近似模型。

### 1.2 什么是 Special Quasirandom Structure (SQS)

**SQS（特殊准随机结构）** 是 Zunger、Wei、Ferreira 和 Bernard 于 1990 年提出的概念 [1]。其核心思想可以概括为：

> **在有限大小的周期性超胞中，通过优化原子排列，使超胞内的局域团簇相关函数（cluster correlation functions）尽可能接近完全随机态的对应值。**

换言之，SQS 并不试图在有限超胞中实现"真正的随机"——这在数学上是不可能的。它追求的是一个更实际的目标：在团簇展开（Cluster Expansion）的框架下，使得 SQS 与完全随机合金在短程结构上"尽可能相似"。这种相似性通过量化比较两者的**团簇相关函数**来度量。

从物理直觉上理解，可以将 SQS 视为随机合金的一个**最优代表性样本**：虽然它只是一个周期性的小超胞，但其中原子的排列方式经过精心优化，使得当我们用 DFT 计算这个结构的能量、电子密度等性质时，得到的结果能够很好地近似真实无序合金的平均性质。

SQS 方法自 1990 年提出以来，已成为无序合金第一性原理研究的标准工具之一，广泛应用于形成能计算、相图预测、弹性性质研究、以及高通量材料筛选等领域。

### 1.3 SQS 的物理意义与应用场景

SQS 在计算材料科学中有广泛的应用场景：

- **形成能与混合能计算**：通过 SQS 获得无序相的能量，与有序相的 DFT 能量对比，计算形成能和混合焓，进而预测合金的稳定性。
- **相图计算**：SQS 提供无序相的自由能参考点，结合 Cluster Expansion 方法，可以构建完整的温度-成分相图。
- **电子结构分析**：通过 SQS 计算，可以获得无序合金的态密度（DOS）、能带结构等电子性质，研究无序度对电子行为的影响。
- **弹性与力学性质**：SQS 可用于计算无序合金的弹性常数、体模量、剪切模量等力学性质随成分的变化。
- **功能材料设计**：对于压电、铁电、热电等功能材料中的无序固溶体，SQS 使得通过 DFT 研究其功能性质成为可能。

本项目的具体应用对象是 **K₀.₅Na₀.₅NbO₃（KNN）体系**——一种重要的无铅压电陶瓷候选材料。在 KNN 的钙钛矿结构中，A 位的 K 和 Na 原子以近似随机的方式占据，这种无序性对材料的压电性能有重要影响。通过 SQS 建模，可以为后续的 DFT 计算提供代表性的结构模型。

---

## 2. 理论基础

本章介绍 SQS 方法的数学基础，包括团簇展开形式理论、SQS 的数学原理，以及质量评估的量化标准。

### 2.1 团簇展开（Cluster Expansion）形式理论

团簇展开（Cluster Expansion, CE）是描述多组元固溶体热力学性质的通用理论框架，由 Sánchez、Ducastelle 和 Gratias 于 1984 年系统建立 [2]。

**核心思想**是将构型依赖的物理量（如形成能）展开为一系列"团簇"的贡献。具体而言，对于由 $N$ 个格点组成的晶格，每个格点可以被 $M$ 种原子占据。一个特定的原子构型记为 $\sigma$，则体系的形成能可以表示为：

$$E(\sigma) = \sum_{\alpha} V_{\alpha} \cdot \Gamma_{\alpha}(\sigma)$$

其中：
- 求和遍历所有团簇 $\alpha$（包括空团簇、单点、点对、三体、四体等）
- $V_{\alpha}$ 是**有效团簇相互作用**（Effective Cluster Interactions, ECI），描述特定团簇类型对能量的贡献
- $\Gamma_{\alpha}(\sigma)$ 是**团簇相关函数**（cluster correlation function），描述构型 $\sigma$ 中团簇 $\alpha$ 的平均占据模式

团簇按其包含的格点数和最大格点间距（直径）分类。例如：
- **空团簇**（empty cluster）：0 个格点，对应常数项
- **单点团簇**（point cluster）：1 个格点，描述化学势/浓度
- **对团簇**（pair cluster）：2 个格点，描述最近邻、次近邻等双体相互作用
- **多体团簇**（triplet, quadruplet, ...）：3 个及以上格点，描述多体效应

团簇相关函数 $\Gamma_{\alpha}$ 构成了构型空间的一组正交完备基。在 CE 框架下，我们只需要截断到一定直径范围内的团簇（因为长程团簇对能量的贡献通常快速衰减），就可以用有限个 ECI 参数来精确描述构型-能量映射。

### 2.2 SQS 的数学原理

在 CE 框架下，SQS 的目标变得清晰：**找到有限超胞中使团簇相关函数最接近完全随机态值的原子排列**。

对于完全随机的二元固溶体 A$_{1-x}$B$_x$，团簇相关函数的目标值 $\Gamma^{\text{target}}_{\alpha}$ 可以解析给出。最简单的例子：
- 单点相关函数：$\Gamma^{\text{target}}_{\text{point}} = 1 - 2x$（对于等浓度 $x=0.5$，目标值为 0）
- 对相关函数：$\Gamma^{\text{target}}_{\text{pair}} = (1-2x)^2$

对于一个给定的超胞结构，其团簇向量（cluster vector）是所有团簇相关函数的有序排列：

$$\vec{\Gamma}^{\text{SQS}} = (\Gamma^{\text{SQS}}_0, \Gamma^{\text{SQS}}_1, \Gamma^{\text{SQS}}_2, \ldots)$$

对应的目标团簇向量为 $\vec{\Gamma}^{\text{target}}$。SQS 的优化目标是最小化两者之间的距离：

$$\Delta = \|\vec{\Gamma}^{\text{SQS}} - \vec{\Gamma}^{\text{target}}\|$$

在实际实现中，由于计算所有团簇既不必要也不可行，通常只匹配**截断半径**（cutoff）内的团簇。这是因为：
1. 短程团簇对能量和性质的贡献最大
2. 长程团簇的相关函数在有限超胞中受周期性边界条件的影响较大
3. 匹配过多团簇会导致搜索空间爆炸

icet 库提供了 `compare_cluster_vectors` 函数，结合 `optimality_weight` 参数对团簇向量进行加权比较，使短程团簇（物理上更重要）获得更高的权重。

### 2.3 质量评估标准——van de Walle 2013 准则

SQS 的质量评估是确保结果可靠性的关键环节。van de Walle 等 [3] 在 2013 年提出了改进的 SQS 生成和评估方法，核心贡献是将优化目标从"最小化总偏差"改进为"**最大化完美匹配的团簇数量**"。

传统做法是优化一个全局距离度量（如 L2 范数），但这可能导致每个团簇都有一点偏差，而没有"完美匹配"任何一个团簇。van de Walle 的改进思路是：通过在目标函数中引入奖励项，鼓励尽可能多的团簇达到完美匹配（偏差为零），同时对未匹配团簇的偏差施加加权惩罚。

在本项目中，采用以下阈值体系进行质量分级：

| 质量等级 | 团簇向量偏差 | 判定 |
|---------|-----------|------|
| 优秀（Excellent） | $\Delta < 0.001$ | 达到理想 SQS 质量 |
| 良好（Good） | $\Delta < 0.01$ | 高质量 SQS |
| 可用（Acceptable） | $\Delta < 0.10$ | 可接受的 SQS 质量 |
| 有限系统可接受 | $\Delta < 0.30$ | 小系统或不对称浓度的物理限制 |
| 失败 | $\Delta \geq 0.30$ | 质量不达标，需增大超胞或调整参数 |

需要特别注意的是，对于原子数较少的小系统（如 $N < 200$），由于离散化效应，完全随机态的团簇相关函数本身就会偏离理论目标值。因此，偏差 $< 0.30$ 在小系统中是可接受的物理限制，并不一定意味着 SQS 质量不好。

---

## 3. 工具选型：icet vs ATAT

本章介绍 SQS 生成领域的两大主流工具——ATAT/mcsqs 和 icet，并进行系统的对比分析，阐明本项目选择 icet 的技术理由。

### 3.1 ATAT/mcsqs 简介

**ATAT（Alloy Theoretic Automated Toolkit）** 是由 Axel van de Walle 等开发的合金理论自动化工具包，首次发布于 2002 年 [4]。ATAT 提供了一整套用于合金热力学计算的工具，包括：

- **maps/mcsqs**：SQS 结构生成（基于 Monte Carlo 模拟退火）
- **corrconv**：团簇相关函数转换
- **cvm**：团簇变分法计算
- **phb**：相边界计算

ATAT 中的 **mcsqs** 工具是早期最广泛使用的 SQS 生成程序。其核心算法是 Monte Carlo 模拟退火：从随机初始化的超胞出发，通过随机交换原子位置，配合逐步降温的退火策略，搜索使团簇相关函数最优匹配目标值的结构。

mcsqs 的优势在于经过了长期的实际应用验证，在 CALPHAD（CALculation of PHAse Diagrams）和第一性原理热力学领域有着广泛的使用基础。然而，mcsqs 基于 Monte Carlo 方法，本质上是一种**启发式搜索**，无法保证找到全局最优解。

ATAT 使用 Perl 和 C 编写，通过命令行操作，输入输出格式为自定义文本格式，与其他现代计算材料学工具（如 Python 生态）的集成需要额外的胶水代码。

### 3.2 icet 简介

**icet（Integrated Cluster Expansion Toolkit）** 是由 Ångqvist 等于 2019 年发布的现代化 Cluster Expansion 工具库 [5]。icet 的设计理念是提供**灵活、可扩展、易于集成**的 Python 接口，同时通过 C++ 后端保证计算性能。

icet 的核心功能包括：

- **ClusterSpace 构建**：从晶体结构和化学信息构建团簇空间
- **CE 训练**：支持线性回归、LASSO、贝叶斯回归、交叉验证、特征选择等多种训练策略
- **结构枚举**：基于对称性约化，枚举所有对称不等价的结构
- **Monte Carlo 采样**：支持规范系综和半巨正则系综的 MC 模拟
- **SQS 生成**：提供两种路径

在 SQS 生成方面，icet 提供了两种互补的方法：

1. **枚举法**（`generate_sqs_by_enumeration`）：穷举搜索给定尺寸范围内的所有可能超胞，保证找到全局最优的 SQS。icet 官方文档明确指出：*"Generation of SQS by enumeration is preferable for small systems because with enumeration there is no risk that the optimal SQS cell is missed."* [6]

2. **Monte Carlo 法**（`generate_sqs_from_supercells`）：在用户指定的超胞上进行模拟退火优化，适用于大体系。

这种双路径设计使得研究者可以根据体系规模灵活选择：小体系用枚举法确保最优，大体系用 MC 法保证可扩展性。

### 3.3 对比分析

| 对比维度 | ATAT/mcsqs | icet |
|---------|-----------|------|
| **编程语言** | Perl/C | Python（C++ 后端加速） |
| **安装方式** | 源码编译，依赖管理复杂 | `pip install icet`，一键安装 |
| **SQS 生成方法** | 仅 Monte Carlo 模拟退火 | 枚举法 + Monte Carlo 双路径 |
| **小系统最优保证** | MC 无法保证全局最优 | 枚举法保证全局最优 |
| **Python 集成** | 无原生支持，需额外封装 | 原生 Python API |
| **多亚晶格支持** | 有限 | 原生支持多亚晶格、空位等 |
| **CE 训练能力** | 基础（SIM/Connolly-Williams） | 丰富（线性/贝叶斯回归、交叉验证、特征选择） |
| **与其他工具集成** | 自定义格式，需手动对接 | 原生支持 ASE、pymatgen 等生态 |
| **文档质量** | 手册式文档 | 详尽的在线文档 + 教程 + API 参考 |
| **可视化支持** | 无内置可视化 | 通过 ASE/Matplotlib 轻松实现 |
| **社区活跃度** | 维护模式，更新较少 | 活跃开发中，持续迭代 |
| **可扩展性** | 有限，难以嵌入自动化流程 | 可与 ML/数据分析流水线无缝集成 |

### 3.4 选择 icet 的理由

综合以上对比，本项目选择 icet 作为 SQS 生成引擎，主要基于以下考量：

1. **双路径 SQS 生成**：枚举法 + MC 法的双路径设计，使得工具能够覆盖从中小体系（枚举法保证全局最优）到大体系（MC 法可扩展）的完整应用场景。这是 icet 相对于 ATAT 的独特优势。

2. **Python 原生生态**：icet 的 Python API 与 ASE（Atomic Simulation Environment）、pymatgen 等现代计算材料学工具无缝集成，便于构建端到端的自动化工作流。对于本项目，这意味着可以直接读取 VASP 的 POSCAR 格式、输出 VASP 可用的 SQS 结构文件。

3. **安装简便**：`pip install icet` 一条命令即可完成安装，相比 ATAT 的源码编译和 Perl 依赖配置，大幅降低了使用门槛。

4. **丰富的 CE 训练能力**：虽然当前项目聚焦于 SQS 生成，但 icet 提供的完整 CE 训练能力（交叉验证、正则化、特征选择等）为未来扩展到相图预测、热力学性质计算等高级应用奠定了基础。

5. **活跃的社区与完善的文档**：icet 拥有活跃的开发团队和详尽的在线文档 [6]，包括 API 参考、使用教程和理论背景介绍，降低了学习和使用的难度。

---

## 4. 项目架构与实现

本章从软件工程的角度，详细介绍 SQS Workflow 项目的整体架构、核心模块实现、辅助工具以及用户界面设计。

### 4.1 总体架构设计

项目采用**模块化流水线架构**，将 SQS 生成过程分解为四个独立的阶段，各阶段通过文件系统传递中间数据，实现了解耦和可恢复性。

```
                    ┌─────────────┐
                    │   dop.in    │  ← 带标注的晶体结构
                    │ config.json │  ← 运行参数配置
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Step 1     │  构建 ClusterSpace
                    │ 01_build_   │
                    │ clusterspace│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──────┐     │     ┌──────▼─────────┐
    │ output/        │     │     │ output/        │
    │ 02_clusterspace│     │     │ 02_doping_info │
    │     .cs        │     │     │    .json       │
    └─────────┬──────┘     │     └──────┬─────────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──────┐  ┌──▼───────────▼──┐
    │  Step 2a       │  │  Step 2b        │
    │ 枚举法         │  │  MC 法          │
    │ 02_generate_   │  │ 02_generate_    │
    │ sqs_enum       │  │ sqs_mc          │
    └───────┬────────┘  └───────┬─────────┘
            │                   │
            └────────┬──────────┘
                     │
            ┌────────▼────────┐
            │ output/         │
            │ 03_sqs_         │
            │ structure.json  │
            │ SQS_enum/MC_*.  │
            │    vasp / cif   │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  Step 3         │  导出最终结果
            │ 03_validate_    │
            │ export          │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │ SQS_FINAL.vasp  │
            │ SUMMARY.txt     │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  Step 4         │  质量验证
            │ 04_validate_    │
            │ quality         │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │ QUALITY_REPORT  │
            │     .txt        │
            │ quality_        │
            │ validation.json │
            └─────────────────┘
```

**设计理念**：

- **解耦性**：每个阶段是独立的 Python 脚本，通过文件系统传递数据，可以单独运行、调试和恢复
- **可追溯性**：中间产物（ClusterSpace、掺杂信息、SQS 结构数据）均持久化到磁盘，便于事后审查
- **可恢复性**：如果某个阶段失败，修复问题后可以从该阶段重新开始，无需从头运行
- **双路径支持**：Step 2 提供枚举法和 MC 法两种选择，共享相同的输入和输出格式

### 4.2 核心模块详解

#### 4.2.1 输入格式设计（dop.in）

`dop.in` 是项目的核心输入文件，采用**扩展 POSCAR 格式**。设计理念是在标准 VASP POSCAR 的基础上做最小化扩展，通过在坐标行末尾添加元素标注来表达掺杂信息。

标注语法规则：
- 单元素标注：`Nb=1.0` 表示该位点完全由 Nb 占据（**有序位点**）
- 多元素标注：`K=0.5,Na=0.5` 表示该位点由 K 和 Na 以 50%/50% 的概率占据（**无序位点**）
- 约束：每行标注的浓度之和必须为 1.0

示例（K₀.₅Na₀.₅NbO₃ 体系）：

```
dop.in
1.0
  5.6573  0.0000  0.0000
  0.0000  3.9551  0.0000
  0.0000  0.0000  5.6717
Nb  O  K  Na
2  6  2  2
Direct
  0.000  0.500  0.500  Nb=1.0            # index 0
  0.500  0.500  0.000  Nb=1.0            # index 1
  0.249  0.500  0.218  O=1.0             # index 2
  ...                                        (O 位点省略)
  0.000  0.000  0.000  K=0.5,Na=0.5      # index 8 (无序位点)
  0.500  0.000  0.500  K=0.5,Na=0.5      # index 9 (无序位点)
```

解析逻辑的关键设计决策是：**不依赖头部第 6-7 行的元素声明和数量**，而是直接从坐标行的标注中读取。这是因为头部声明只反映一种可能的元素排列方式，而标注行包含了完整的掺杂信息。这种设计避免了两处信息不一致的风险。

#### 4.2.2 ClusterSpace 构建（01_build_clusterspace.py）

Step 1 负责从 `dop.in` 解析晶体结构和掺杂信息，构建 icet 的 `ClusterSpace` 对象。

**核心流程**：

1. **解析 dop.in**：`parse_labeled_poscar()` 函数读取晶格向量、原子坐标和元素标注，生成三个核心数据结构：
   - `structure`：ASE `Atoms` 对象，表示晶体结构（有序位点用标注的第一个元素填充）
   - `chemical_symbols`：列表的列表，如 `[['Nb'], ['Nb'], ['O'], ..., ['K', 'Na'], ['K', 'Na']]`，每个子列表表示该位点允许的元素集合
   - `target_concentrations`：字典，如 `{'A': {'K': 0.5, 'Na': 0.5}}`，按无序位点分组记录目标浓度

2. **浓度验证**：确保每个无序位点的浓度之和为 1.0（容差 $10^{-6}$）

3. **构建 ClusterSpace**：调用 icet 的 `ClusterSpace()` 构造函数，传入：
   - `structure`：晶体结构
   - `cutoffs`：团簇截断半径列表（默认 `[5.0]` Å）
   - `chemical_symbols`：位点允许的元素列表
   - `symprec`：对称性容差（设为 $10^{-3}$，比默认值宽松，提高对实验结构的兼容性）
   - `position_tolerance`：位置容差（设为 0.1 Å）

4. **输出**：
   - `output/02_clusterspace.cs`：icet 的 ClusterSpace 二进制文件
   - `output/02_doping_info.json`：掺杂信息的 JSON 记录

`chemical_symbols` 的设计是该模块的精髓：它告诉 icet 哪些位点是"固定的"（只有一种元素），哪些位点是"可变的"（有多种元素），从而让 icet 只在可变位点上进行 SQS 优化。对于 K₀.₅Na₀.₅NbO₃ 体系，这意味着 icet 只需要优化 2 个 A 位位点的 K/Na 分布，而 8 个有序位点（2 Nb + 6 O）保持不变。

#### 4.2.3 枚举法 SQS 生成（02_generate_sqs_enum.py）

枚举法是 icet 提供的两种 SQS 生成路径之一，适用于中小体系。

**工作原理**：

icet 的 `generate_sqs_by_enumeration` 函数在内部执行以下步骤：
1. 枚举所有可能的超胞尺寸（从 1 到 `max_size`）
2. 对于每个超胞尺寸，枚举所有对称不等价的原子排列
3. 计算每种排列的团簇向量与目标团簇向量的偏差
4. 返回偏差最小的结构

**关键参数**：
- `cluster_space`：Step 1 构建的 ClusterSpace 对象
- `max_size`：最大原胞倍数（控制搜索空间的上限）
- `target_concentrations`：目标浓度（约束搜索范围）
- `include_smaller_cells`：是否允许返回更小的优化结构
- `pbc`：周期性边界条件

**优势**：由于穷举了所有可能，枚举法**保证找到全局最优解**，不存在陷入局部最优的风险。

**适用场景**：中小体系（`max_size` 通常 ≤ 8-12）。当体系变大时，枚举的计算量呈指数增长，此时应切换到 MC 法。

#### 4.2.4 MC 法 SQS 生成（02_generate_sqs_mc.py）

MC 法是处理大体系 SQS 生成的主要方法。

**工作原理**：

icet 的 `generate_sqs_from_supercells` 函数采用**模拟退火**（simulated annealing）策略：
1. 从用户指定的超胞出发
2. 初始化为随机原子排列
3. 在高温（`T_start`，默认 5.0）下随机交换无序位点上的原子
4. 逐步降温到低温（`T_stop`，默认 0.001），在每步接受或拒绝交换（Metropolis 准则）
5. 最终得到团簇向量偏差较小的结构

**迭代优化策略**：

本项目的 MC 模块在单次模拟退火的基础上，增加了**多轮迭代**机制：
- 进行 `max_iterations`（默认 5）次独立的模拟退火（使用不同的随机种子）
- 每次与当前最佳结果比较，保留偏差最小的结构
- 如果连续 `early_stop_no_improve`（默认 3）次无改进，则提前停止
- 可选地保存优化进度（`sqs_optimization_progress.pkl`），支持中断恢复

**晶格修正**：

icet 在 SQS 生成过程中可能对晶格参数做微小调整。本项目通过晶格修正步骤，将 icet 输出的结构映射回用户在 `dop.in` 中定义的精确晶格，确保输出结构与输入结构的晶格完全一致。

**适用场景**：大体系或需要精确控制超胞尺寸的场景。超胞尺寸由 `supercell_matrix` 参数完全控制（如 `[[2,0,0],[0,2,0],[0,0,1]]` 表示在 a、b 方向各扩展 2 倍）。

#### 4.2.5 结果导出（03_validate_export.py）

Step 3 读取 Step 2 生成的 `03_sqs_structure.json`，进行最终导出：

- **重建 ASE Atoms**：从 JSON 中的晶格、位置和原子序数信息重建结构
- **元素排序**：按元素符号排序原子（VASP 格式的标准要求）
- **输出文件**：
  - `SQS_FINAL.vasp`：最终的 SQS 结构（VASP POSCAR 格式，可直接用于 VASP 计算）
  - `output/SUMMARY.txt`：生成摘要（化学式、原子数、方法、耗时等）

#### 4.2.6 质量验证（04_validate_quality.py）

Step 4 对生成的 SQS 进行全面的质量评估，采用 `SQSQualityValidator` 类实现四维质量检查：

1. **团簇向量检查**：计算 SQS 与目标团簇向量的偏差，优先使用 icet 的 `compare_cluster_vectors` 函数（如果可用），否则回退到 L2 范数距离
2. **浓度检查**：验证 SQS 中各元素的实际浓度与目标浓度的匹配度，支持分组分析（A 位、B 位等）
3. **结构检查**：基本结构验证，包括晶格参数、体积、密度、最近邻距离等
4. **综合报告**：汇总以上检查结果，生成 `output/QUALITY_REPORT.txt`（人类可读）和 `output/quality_validation.json`（机器可读）

### 4.3 辅助模块

项目包含多个辅助模块，为核心流水线提供支撑能力：

- **`quality_utils.py`**：质量评估工具函数库。提供团簇向量偏差计算（`calculate_cv_deviation`）、质量评级（`evaluate_sqs_quality`）、可达偏差估计（`estimate_achievable_deviation`）、系统尺寸建议（`get_system_size_recommendation`）等功能。关键设计特点是对 icet API 可用性的柔性处理——当 icet 的高级 API 不可用时，自动回退到简单的数学实现，确保工具在不同环境中均可运行。

- **`template_generator.py`**：首次运行引导工具。当项目中不存在 `dop.in` 时，自动检测 `POSCAR` 文件，生成带标注的 `dop.in` 模板和 `atom_index_guide.txt`（原子索引对照表），帮助新用户快速上手。

- **`models.py`**：基于 Pydantic 的数据模型定义。包含 `SystemConfig`、`SQSConfig`、`OutputConfig`、`ValidationConfig`、`SQSWorkflowConfig`、`SQSResult` 等强类型模型，提供自动字段验证、默认值管理和 JSON 序列化/反序列化能力。

- **`constants.py`**：集中管理全局常量。将质量阈值、默认参数值、文件名约定、晶体相对称性信息、日志配置等统一管理在 `QualityThresholds`、`Defaults`、`FileNames`、`CrystalPhases` 等类中，确保全局一致性。

- **`io_file.py`**：集中化文件 IO 工具。提供 `StructureIO`（结构保存/加载）、`ProgressIO`（进度保存/恢复）、`DopingInfoIO`（掺杂信息读写）、`ConfigIO`（配置读写）、`ReportWriter`（报告生成）等类，统一处理多格式（JSON、VASP、CIF、pickle）的输入输出。

- **`parser.py`**：结构解析核心。使用 Python dataclass 定义 `DopingSite` 和 `ParsedStructure` 数据结构，提供 `StructureParser` 类，封装 `dop.in` 的查找和解析逻辑。

### 4.4 用户界面设计

项目的用户界面设计遵循**"渐进式复杂度"**原则，通过三档配置模式满足不同层次用户的需求。

**入口与初始化**：

用户通过 `python sqskit_modern.py` 启动程序。程序首先检查 `dop.in` 是否存在：
- 如果不存在，进入**首次运行引导**：检测 `POSCAR` 文件，使用 `UniversalTemplateGenerator` 生成 `dop.in` 模板和原子索引对照表，然后退出并提示用户编辑 `dop.in`
- 如果存在，进入主交互界面

**三档配置模式**：

| 配置级别 | 参数数量 | 适用人群 | 配置内容 |
|---------|---------|---------|---------|
| 快速模式 | 2-3 个 | 新手/快速实验 | 团簇截断半径 + max_size 或超胞矩阵 |
| 标准模式 | 5-7 个 | 日常使用 | 快速模式 + tolerance + 迭代参数（MC）或 include_smaller_cells（枚举） |
| 专家模式 | 全部参数 | 高级用户 | 标准 + ClusterSpace 高级参数 + SQS 高级参数 + 输出/验证参数 |

**交互组件**：

- **questionary**：提供命令行中的向导式交互（选择菜单、文本输入、确认对话框），所有输入均有范围校验
- **rich**：提供彩色输出、表格（配置确认）、进度条（工作流执行）、面板（欢迎/结果展示）

**错误处理**：

- `KeyboardInterrupt`：捕获后显示友好提示并干净退出
- 子进程超时：每个流水线阶段有 600 秒超时限制
- 异常捕获：全局异常处理器输出错误信息和完整 traceback，便于问题定位
- 用户确认：执行前展示配置表格，经用户确认后才启动计算

---

## 5. 示例应用：K₀.₅Na₀.₅NbO₃ 体系

本章以 K₀.₅Na₀.₅NbO₃（KNN）体系为实例，展示 SQS Workflow 工具的完整使用过程和生成结果。

### 5.1 体系简介

K₀.₅Na₀.₅NbO₃（简称 KNN）是一种钙钛矿结构的氧化物，属于**无铅压电陶瓷**的重要候选材料。在环保要求日益严格的背景下，KNN 被视为替代传统含铅 PZT（Pb(Zr,Ti)O₃）压电陶瓷的有前途的材料。

KNN 的晶体结构为正交钙钛矿（空间群 Amm2），其中：
- **B 位**（Nb）：完全由铌占据，形成 NbO₆ 八面体骨架
- **A 位**（K/Na）：钾和钠以近似等比例随机占据
- **O 位**：氧原子有序占据

KNN 中 A 位 K/Na 的无序性对材料的宏观性能（特别是压电和介电性质）有重要影响。通过 SQS 建模，可以为后续的 DFT 计算提供具有代表性的无序结构模型，使得研究 A 位无序对电子结构、自发极化等性质的影响成为可能。

### 5.2 输入配置与参数设置

**dop.in 配置**：

KNN 的原胞包含 10 个原子（2 Nb + 6 O + 2 A 位），其中 2 个 A 位为无序位点（K=0.5, Na=0.5）：

```
dop.in
1.0
  5.6573  0.0000  0.0000
  0.0000  3.9551  0.0000
  0.0000  0.0000  5.6717
Nb  O  K  Na
2  6  2  2
Direct
  0.000  0.500  0.500  Nb=1.0            # index 0
  0.500  0.500  0.000  Nb=1.0            # index 1
  0.249  0.500  0.218  O=1.0             # index 2
  0.751  0.500  0.218  O=1.0             # index 3
  0.749  0.500  0.718  O=1.0             # index 4
  0.251  0.500  0.718  O=1.0             # index 5
  0.000  0.000  0.461  O=1.0             # index 6
  0.500  0.000  0.961  O=1.0             # index 7
  0.000  0.000  0.000  K=0.5,Na=0.5     # index 8
  0.500  0.000  0.500  K=0.5,Na=0.5     # index 9
```

**config.json 参数选择**：

| 参数 | 值 | 选择理由 |
|-----|---|---------|
| cutoffs | [5.0] Å | 覆盖最近邻和次近邻对团簇，平衡精度与计算量 |
| max_size | 8 | 枚举法最大搜索到 80 原子超胞 |
| supercell_matrix | [[2,0,0],[0,2,0],[0,0,1]] | MC 法：在 a、b 方向各扩展 2 倍，生成 40 原子超胞 |
| tolerance | 0.001 | 目标达到"优秀"质量等级 |
| max_iterations | 5 | MC 法最多 5 轮独立优化 |

### 5.3 生成结果与质量评估

**ClusterSpace 构建结果**（Step 1）：

```
结构信息:
  原子数: 10
  化学式: K2Nb2O6

掺杂统计:
  无序位点: 2
  有序位点: 8

目标浓度配置:
  A: {'K': 0.5, 'Na': 0.5}

✓ 浓度验证通过
✓ ClusterSpace构建成功!
```

ClusterSpace 成功识别出 10 原子原胞中的 2 个无序位点和 8 个有序位点，目标浓度为 A 位 K:Na = 50%:50%。

**MC 法已生成的结果**：

项目 output 目录中已包含 MC 法的历史运行结果：

| 文件 | 说明 |
|-----|------|
| `SQS_mc_4x.vasp` | 4 倍超胞（40 原子），VASP 格式 |
| `SQS_mc_4x.cif` | 4 倍超胞，CIF 格式 |
| `SQS_mc_8x.vasp` | 8 倍超胞（80 原子），VASP 格式 |
| `SQS_mc_8x.cif` | 8 倍超胞，CIF 格式 |
| `QUALITY_REPORT.txt` | 质量评估报告 |
| `quality_validation.json` | 质量评估数据 |
| `SUMMARY.txt` | 生成摘要 |
| `sqs_optimization_progress.pkl` | MC 优化进度快照 |

**输出文件的使用**：

最终的 `SQS_FINAL.vasp` 文件可以直接用于 VASP 的 DFT 计算。该文件已按 VASP 标准格式排列（按元素排序、分数坐标），包含了经过质量验证的 SQS 结构。研究人员可以将其作为 `POSCAR` 直接启动 VASP 计算，获取 KNN 无序体系的电子结构、总能量、弹性性质等第一性原理数据。

---

## 6. 总结与展望

### 6.1 项目特点总结

本项目实现了一套**基于 icet 库的专业 SQS 生成工具**，具有以下核心特点：

1. **现代化技术栈**：基于 Python 生态（icet + ASE + rich + questionary），利用现代计算材料学工具链的优势，实现了从输入到输出的完整自动化工作流。

2. **双方法支持**：同时提供枚举法和 Monte Carlo 法两种 SQS 生成路径。枚举法适用于中小体系，保证全局最优；MC 法适用于大体系，支持精确控制超胞尺寸。两种方法共享统一的输入输出接口，用户可根据需求灵活选择。

3. **模块化流水线**：四步流水线设计（ClusterSpace 构建 → SQS 生成 → 结果导出 → 质量验证）实现了清晰的关注点分离。每个阶段独立运行，通过文件系统传递数据，支持断点恢复和单独调试。

4. **完善的质量评估**：基于 van de Walle 2013 准则的四维质量检查体系（团簇向量、浓度、结构、综合评估），确保生成的 SQS 满足科学计算的精度要求。

5. **友好的用户体验**：三档配置模式（快速/标准/专家）覆盖从新手到专家的全层次需求；首次运行自动引导生成输入模板；交互式 CLI 提供彩色的配置确认和进度显示。

6. **通用性**：支持任意晶体结构和掺杂体系，不限于特定材料或对称性。只需准备符合格式的 `dop.in` 文件，即可为任何多组元体系生成 SQS。

### 6.2 潜在改进方向

1. **增强测试覆盖**：当前测试主要覆盖基础解析和模块存在性检查。未来可增加端到端集成测试（从 `dop.in` 到 `SQS_FINAL.vasp` 的完整流水线测试）和更多边界条件测试。

2. **统一 IO 层**：当前各核心脚本（枚举法和 MC 法）内部实现了独立的保存逻辑。可以将所有文件读写操作统一到 `io_file.py` 模块，减少代码重复，提升一致性。

3. **更多输入格式支持**：除 VASP POSCAR 格式外，支持 CIF、XYZ、LAMMPS data 等格式作为直接输入，进一步降低使用门槛。

4. **可视化能力**：添加团簇向量匹配图（SQS vs 目标的对比柱状图）、MC 优化收敛曲线、结构可视化预览等图形输出，增强结果的可解释性。

5. **批量生成与参数扫描**：支持对不同超胞尺寸、不同截断半径、不同浓度组合的批量 SQS 生成和系统化比较，便于寻找最优参数配置。

6. **与 pymatgen 更深度集成**：利用 pymatgen 的对称性分析、相图工具等高级功能，扩展工具的能力边界。

---

## 7. 参考文献

[1] Zunger, A., Wei, S.-H., Ferreira, L. G., & Bernard, J. E. (1990). Special quasirandom structures. *Physical Review Letters*, 65(3), 353–356. https://doi.org/10.1103/PhysRevLett.65.353

[2] Sánchez, J. M., Ducastelle, F., & Gratias, D. (1984). Generalized cluster description of multicomponent systems. *Physica A*, 128(1-2), 334–350. https://doi.org/10.1016/0378-4371(84)90096-7

[3] van de Walle, A., Tiwary, P., de Jong, M., Olmsted, D. L., Asta, M., Dick, A., Shin, D., Wang, Y., Liu, L.-Q., & Chen, Z.-K. (2013). Efficient stochastic generation of special quasirandom structures. *Calphad*, 42, 13–18. https://doi.org/10.1016/j.calphad.2013.06.006

[4] van de Walle, A., Asta, M., & Ceder, G. (2002). The Alloy Theoretic Automated Toolkit: A user guide. *Calphad*, 26(4), 539–553. https://arxiv.org/abs/cond-mat/0212159

[5] Ångqvist, M., Muñoz, V. A., Rahm, J. M., Fransson, E., Durniak, C., Rozyczko, P., Rod, T. H., & Erhart, P. (2019). ICET – A Python Library for Constructing and Sampling Alloy Cluster Expansions. *Advanced Theory and Simulations*, 2(12), 1900015. https://doi.org/10.1002/adts.201900015

[6] icet 官方文档. Special quasirandom structures. https://icet.materialsmodeling.org/advanced_topics/sqs_generation.html
