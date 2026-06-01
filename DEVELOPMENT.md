# 开发者文档

## 环境搭建

```bash
# 克隆仓库
git clone https://github.com/soft-defoliation/icet_SQS.git
cd icet_SQS

# 自动安装所有依赖（含测试/格式化工具）
pip install -e ".[dev]"
```

---

## 项目结构

```
sqskit_modern.py              # 入口脚本（也可以直接跑）
pyproject.toml                # 包配置、依赖声明（唯一来源）
src/sqs_workflow/
├── cli/modern_interactive.py # 交互式命令行界面
├── core/                     # 核心流水线（4 步）
│   ├── build_clusterspace.py # Step 1：构建 ClusterSpace
│   ├── generate_sqs_enum.py  # Step 2a：枚举法生成 SQS
│   ├── generate_sqs_mc.py    # Step 2b：MC 法生成 SQS
│   ├── validate_export.py    # Step 3：导出结果
│   └── validate_quality.py   # Step 4：质量验证
├── utils/
│   ├── quality_utils.py      # 质量评估工具函数
│   └── template_generator.py # dop.in 模板生成器
├── parser.py                 # dop.in 解析器
├── models.py                 # Pydantic 数据模型
├── constants.py              # 全局常量、阈值、文件名
└── logging_config.py         # 日志配置
tests/
├── test_generality.py        # 跨晶体结构解析测试
├── test_workflow.py          # 核心模块单元测试
└── test_cli.py               # CLI 验证测试
```

---

## 日常开发

### 一键命令

```bash
make check     # 跑完所有质量检查（flake8 → pytest → black）
make format    # 自动格式化
make test      # 只跑测试
make lint      # 只跑 lint
```

### 手动命令

```bash
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
pytest tests/ -v --tb=short
black src/ tests/
```

---

## 代码约定

### `run()` vs `main()` 模式

每个核心模块有两个入口函数：

```python
def run():    # 给其他代码调用的 API，失败抛异常
    ...

def main():   # 给命令行用的，捕获异常后 sys.exit(1)
    ...
```

**调用规则**：从 Python 代码里调永远用 `run()`，不要调 `main()`。

例外：
- `generate_sqs_enum.run()` 返回 `int`（0 成功 / 1 失败），不抛异常
- `validate_export.main()` 直接调 `run()` 没有错误处理

### 数据传递

流水线各步骤之间**通过文件系统传递数据**，没有返回值：

```
dop.in + config.json
       │
  Step 1  →  output/02_clusterspace.cs + output/02_doping_info.json
       │
  Step 2  →  output/03_sqs_structure.json
       │
  Step 3  →  SQS_FINAL.vasp + output/SUMMARY.txt
       │
  Step 4  →  output/QUALITY_REPORT.txt
```

### 导入规范

```python
from sqs_workflow.core import build_clusterspace
from sqs_workflow.parser import StructureParser
```

不是 `from src.xxx`。

### 其他

- `__future__ import annotations` 只在 5 个文件里用，别到处加
- 核心模块用 `print()` 打日志，不用 logger
- icet 日志用 `set_log_config(level='WARNING')` 静音
- Pydantic 模型全放在 `models.py`，常量全放在 `constants.py`

---

## 发布流程

```bash
# 1. 确认所有检查通过
make check

# 2. 打版本（自动更新版本号 + 打 git tag）
make release VER=0.3.0 MSG="新增 xxx 功能"

# 3. 推送到 GitHub
make push
```

版本号遵循语义化版本，更新日志写在 [CHANGELOG.md](CHANGELOG.md) 的 `[Unreleased]` 段，发版时移到对应版本号下。

---

## 常见坑

1. **版本号两个地方**：`pyproject.toml` 和 `src/sqs_workflow/__init__.py` 要一致（`make release` 会自动同步）
2. **没有 requirements.txt**：`pyproject.toml` 是唯一依赖声明
3. **config.json 裸解析**：`build_clusterspace.py` 用 `json.load()` 直接读，没走 Pydantic 模型。改 config 结构时要同步改两处
4. **文件编号缺 01**：中间文件是 `02_*` 和 `03_*`，没 `01_*`，这是故意的
5. **icet 启动慢**：首次 import 要 10-20 秒，不是卡死
6. **MC 方法只支持对角超胞矩阵**：非对角元素必须为 0
