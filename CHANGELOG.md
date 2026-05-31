# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **包结构重构**: `src/*` → `src/sqs_workflow/*`，用户现在通过 `import sqs_workflow.parser` 导入，而非 `import src.parser`
- **版本号统一**: `src/__init__.py` 从 `2.1.0` 改为 `0.2.0`，与 `pyproject.toml` 一致
- **pyproject.toml 完善**: 补全 `authors`, `license`, `readme`, `classifiers`, `urls` 等元数据字段
- **代码风格**: 全项目运行 `black` 格式化，统一引号、缩进、行宽

### Added
- `AGENTS.md` 指南文件，帮助 AI 代理快速上手
- `CHANGELOG.md` 更新日志
- `pyproject.toml` 中添加 PyPI 发布所需的 classifiers 和 urls

### Fixed
- 修复 `quality_utils.py` 中 `except Exception: pass` 静默吞异常的问题，改为区分 `ImportError` 和一般异常并输出警告
- 修复 `validate_quality.py` 中重复 `return None` 死代码
- 修复 ~250+ flake8 问题（未使用导入、f-string 占位符、尾随空格、行过长等）
- 修复 README.md 中过时的 `requirements.txt` 引用

### Removed
- 删除不存在的 `requirements.txt` 引用（`pyproject.toml` 为唯一依赖声明）

## [0.1.0] - 2024

### Added
- SQS Workflow 初始版本
- 四大核心流水线：ClusterSpace 构建、SQS 生成（枚举法 + MC）、结果导出、质量验证
- 交互式 CLI（rich + questionary）
- `dop.in` 格式结构解析器 (StructureParser)
- Pydantic 配置模型 (SQSWorkflowConfig)
- van de Walle 2013 标准质量评估
- pytest 测试套件（41 个测试用例）
- GitHub Actions CI (flake8 + pytest + black)
