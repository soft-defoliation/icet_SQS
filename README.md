# SQS Workflow

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![icet](https://img.shields.io/badge/icet-3.2-green.svg)](https://icet.materialsmodeling.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

专业的 SQS (Special Quasirandom Structure) 生成工具，用于 DFT 计算中无序合金/掺杂体系的超胞结构生成。

---

## 安装

### 普通电脑

```bash
pip install -e .
```

如果报 `Python.h: No such file or directory`，先：

```bash
# Ubuntu/Debian
sudo apt install python3-dev

# CentOS/RHEL  
sudo yum install python3-devel

# 然后再装
pip install -e .
```

### 超算 / 无管理员权限

icet 需要 C++ 编译，但 conda 提供预编译包，可以跳过编译：

```bash
# 如果系统有 conda module，先加载
module load conda

# 创建环境并安装（预编译，不需要 C++ 头文件）
conda create -n sqs -c conda-forge python=3.9 icet -y
conda activate sqs

# 安装本项目
pip install -e .
```

> **提示**：首次启动时 icet 加载约需 10-20 秒，这是正常的，不是卡死。

---

## 使用

### 1. 生成输入模板

```bash
sqskit
```

首次运行会自动在当前目录生成 `dop.in` 模板。

### 2. 编辑 dop.in，填写掺杂信息

在坐标行末尾标注每个位点的元素和浓度：

```
  0.000 0.500 0.500 Nb=1.0           # 有序位点：此位置固定为 Nb
  0.000 0.000 0.000 K=0.5,Na=0.5     # 无序位点：K 和 Na 各占 50%
```

- `元素=1.0` → 该位点固定，不会变化
- `K=0.5,Na=0.5` → 该位点上 K 和 Na 随机分布，浓度相加必须等于 1.0

### 3. 生成 SQS

```bash
sqskit
```

选择生成方法：

| 方法 | 适合 | 说明 |
|------|------|------|
| 枚举法 | 中小体系 | 全局最优，尺寸自动优化 |
| MC 方法 | 大体系 | 迭代优化，可精确控制超胞大小 |

### 4. 获得结果

| 文件 | 用途 |
|------|------|
| `SQS_FINAL.vasp` | 最终 SQS 结构，直接用于 VASP |
| `output/QUALITY_REPORT.txt` | 详细质量评估（基于 van de Walle 2013 标准） |
| `output/SUMMARY.txt` | 生成摘要信息 |

---

## 更新

```bash
# 拉取最新版本
git pull

# 重新安装
pip install -e .
```

各版本改动详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 常见问题

### 安装时报 `fatal error: Python.h: No such file or directory`

icet 编译 C++ 时需要 Python 头文件。

- **个人电脑**：`sudo apt install python3-dev`（Ubuntu）或 `sudo yum install python3-devel`（CentOS）
- **超算 / 无 root**：用上方 conda 方式安装，conda 的 icet 是预编译好的，不需要头文件

### 安装时报 `__glibc` 相关错误

系统太旧。先查看 glibc 版本：

```bash
ldd --version
```

假设输出是 `2.17`，则：

```bash
CONDA_OVERRIDE_GLIBC=2.17 conda create -n sqs -c conda-forge python=3.9 icet -y
```

### 运行时报 `sqskit: command not found`

确认安装成功：

```bash
pip show sqs-workflow
```

没输出说明没装上，重新 `pip install -e .`。

---

## 许可证

MIT License
