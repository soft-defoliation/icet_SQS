# SQS Workflow

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![icet 3.2](https://img.shields.io/badge/icet-3.2-green.svg)](https://icet.materialsmodeling.org/)

专业的 SQS (Special Quasirandom Structure) 生成工具。

## 快速开始

### 方式一：从 GitHub 克隆（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/soft-defoliation/icet_SQS.git
cd icet_SQS

# 2. 安装
pip install -e .

# 3. 运行
sqskit
```

### 方式二：本地安装

```bash
# 1. 进入项目目录
cd /path/to/SQS

# 2. 安装
pip install -e .

# 3. 运行
sqskit
```

首次运行会自动生成 `dop.in` 模板，编辑掺杂浓度后重新运行即可。

> **注意**：启动时 icet 库加载需要约 10-20 秒，属于正常现象。

## 特性

- ✅ **现代化界面** - 彩色输出、键盘导航、进度显示
- ✅ **双方法支持** - Enumeration (小系统) + Monte Carlo (大系统)
- ✅ **质量验证** - 基于 van de Walle 2013 标准
- ✅ **通用性强** - 支持任意晶体结构和掺杂系统
- ✅ **简单易用** - 单一入口，清晰直观

## 项目结构

```
sqskit_modern.py              # 主入口
requirements.txt              # 依赖
src/
├── cli/modern_interactive.py # 交互式界面
├── core/                     # 核心流水线
│   ├── build_clusterspace.py
│   ├── generate_sqs_enum.py
│   ├── generate_sqs_mc.py
│   ├── validate_export.py
│   └── validate_quality.py
├── utils/                    # 工具函数
│   ├── quality_utils.py
│   └── template_generator.py
├── parser.py                 # 结构解析
└── models.py                 # 数据模型
tests/                        # 测试
```

## 使用流程

1. **首次运行** - 生成 `dop.in` 模板
2. **编辑模板** - 设置掺杂浓度
3. **再次运行** - 选择方法并生成 SQS
4. **查看结果** - `SQS_FINAL.vasp` 和质量报告

## 输出文件

- `SQS_FINAL.vasp` - 最终 SQS 结构
- `output/QUALITY_REPORT.txt` - 质量报告
- `output/SUMMARY.txt` - 生成摘要

## 测试

```bash
pytest tests/ -v --tb=short
```

## 依赖

- Python 3.8+
- icet >= 3.2.0
- ase >= 3.22.0
- numpy >= 1.20.0
- questionary >= 1.10.0
- rich >= 13.0.0

## 许可证

MIT License

---

**简洁、专业、易用** 🚀
