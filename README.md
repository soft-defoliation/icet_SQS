# SQS Workflow

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![icet](https://img.shields.io/badge/icet-3.2-green.svg)](https://icet.materialsmodeling.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

专业的 SQS (Special Quasirandom Structure) 生成工具，基于 [icet](https://icet.materialsmodeling.org/) 构建。适用于 DFT 计算中无序合金/掺杂体系的代表性超胞结构生成。

---

## 安装

icet 是一个带 C++ 扩展的科学计算库，`pip install icet` 需要本地编译。根据你的环境选择合适的方式：

### 方式一：conda（推荐，适用于超算 / 无 root 环境）

conda 提供 icet 的预编译包，完全跳过 C++ 编译：

```bash
# 1. 创建环境并安装 icet（预编译，无需 python3-dev）
conda create -n sqs -c conda-forge python=3.9 icet -y
conda activate sqs

# 2. 克隆仓库
git clone https://github.com/soft-defoliation/icet_SQS.git
cd icet_SQS

# 3. 安装项目
pip install -e .
```

> **超算提示**：如果系统已预装 conda module，先执行 `module load conda` 再按上述操作。

### 方式二：pip（需要 python3-dev）

如果你的机器有 root 权限或已安装 Python 开发头文件：

```bash
git clone https://github.com/soft-defoliation/icet_SQS.git
cd icet_SQS

# 安装
pip install -e .

# 开发依赖（测试、格式化）
pip install -e ".[dev]"
```

> **注意**：启动时 icet 库加载约需 10-20 秒，属于正常现象，不是卡死。

### 方式三：icet 已预装时跳过依赖编译

如果 icet 已经在系统里装好了，跳过 icet 重装：

```bash
pip install -e . --no-deps
```

---

## 快速开始

```bash
sqskit
```

首次运行会自动生成 `dop.in` 模板，编辑掺杂浓度后重新运行即可完成 SQS 生成。

```bash
# 查看版本
sqskit --version
```

---

## 使用流程

```
首次运行 → 生成 dop.in 模板 → 编辑掺杂浓度 → 再次运行 → 选择方法 → 得到 SQS_FINAL.vasp
```

### dop.in 格式

在标准 POSCAR 的坐标行末尾追加元素标注：

```
  0.000 0.500 0.500 Nb=1.0           # 有序位点：固定元素
  0.000 0.000 0.000 K=0.5,Na=0.5     # 无序位点：浓度和为 1.0
```

### 生成方法

| 方法 | 适用场景 | 特点 |
|------|---------|------|
| **枚举法** | 中小体系 | 全局最优解，结果尺寸灵活 |
| **MC 方法** | 大体系 / 精确控制 | 迭代优化，保留空间群对称性 |

### 输出文件

| 文件 | 说明 |
|------|------|
| `SQS_FINAL.vasp` | 最终 SQS 结构（VASP POSCAR 格式） |
| `output/QUALITY_REPORT.txt` | 详细质量报告（van de Walle 2013 标准） |
| `output/SUMMARY.txt` | 生成摘要 |

---

## 开发

### 一键命令

项目根目录提供了 `Makefile`，日常开发只需：

| 命令 | 作用 |
|------|------|
| `make check` | 完整质量检查（flake8 + pytest + black） |
| `make format` | 自动格式化代码 |
| `make lint` | 仅 flake8 检查 |
| `make test` | 仅运行测试 |
| `make release VER=0.3.0` | 发布新版本（自动 check → 更新版本号 → 打标签） |
| `make push` | 推送代码和标签到 GitHub |

### 手动命令

```bash
# Lint
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

# 测试
pytest tests/ -v --tb=short

# 格式化
black src/ tests/
```

### 导入使用

```python
from sqs_workflow.core import build_clusterspace, generate_sqs_enum

build_clusterspace.run()  # Step 1
generate_sqs_enum.run()   # Step 2a
```

---

## 发布流程

```bash
# 1. 检查质量
make check

# 2. 打版本（自动更新 pyproject.toml 和 __init__.py 中的版本号）
make release VER=0.3.0 MSG="新功能说明"

# 3. 推送到 GitHub
make push
```

版本号遵循 [语义化版本规范](https://semver.org/lang/zh-CN/)，更新日志见 [CHANGELOG.md](CHANGELOG.md)。

---

## 常见问题

### pip install 报 `fatal error: Python.h: No such file or directory`

icet 的 C++ 扩展需要 Python 头文件来编译。解决方案：

1. **有 root 权限**：`sudo apt install python3-dev`
2. **无 root 权限（超算）**：用 conda 安装（见上方方式一），conda 提供预编译包无需 C++ 编译
3. **icet 已装好**：`pip install -e . --no-deps`

### conda 报 `__glibc >=2.28` 不满足

系统的 glibc 版本太老。先 `ldd --version` 确认版本号，然后用：

```bash
CONDA_OVERRIDE_GLIBC=2.34 conda create -n sqs -c conda-forge python=3.9 icet -y
```

### sqskit 命令找不到

确认已执行 `pip install -e .` 且当前在 conda 环境中。检查：

```bash
pip show sqs-workflow
```

---

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| icet | ≥ 3.2.0 | 核心 SQS 引擎 |
| ase | ≥ 3.22.0 | 结构操作 |
| numpy | ≥ 1.20.0 | 数值计算 |
| rich | ≥ 13.0.0 | CLI 彩色输出 |
| questionary | ≥ 1.10.0 | 交互式菜单 |
| pydantic | ≥ 1.10.0 | 配置模型 |

---

## 许可证

MIT License
