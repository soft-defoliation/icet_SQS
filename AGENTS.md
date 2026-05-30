# AGENTS.md

This file provides guidance to AI agents working in this repository.

## Project Overview

SQS Workflow — A specialized SQS (Special Quasirandom Structure) generation tool built on [icet](https://icet.materialsmodeling.org/). Generates representative supercell structures for disordered alloy/doped systems for DFT calculations.

## Entry Points

```bash
# 运行（安装后直接使用）
sqskit  # → src.cli.modern_interactive:main

# 也可以直接运行入口文件
python sqskit_modern.py

# Individual pipeline steps (importable)
# src.core.build_clusterspace.run()   # Step 1
# src.core.generate_sqs_enum.run()    # Step 2a
# src.core.generate_sqs_mc.run()      # Step 2b
# src.core.validate_export.run()      # Step 3
# src.core.validate_quality.run()     # Step 4
```

## Development Setup

```bash
pip install -e .                # Required before any imports work
pip install -e ".[dev]"         # Includes pytest, black, flake8
```

**All commands must run from project root.** The package uses `src` as a top-level package (not `src/sqs_workflow`), so `import src.parser` works after editable install.

## Verification Commands

```bash
# Lint (must match CI flags)
flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503

# Test
pytest tests/ -v --tb=short

# Format check
black --check --diff src/ tests/

# Single test file
pytest tests/test_generality.py -v
pytest tests/test_workflow.py -v
```

CI runs all three in order: `flake8 → pytest → black --check` (see `.github/workflows/ci.yml`).

## Pipeline Data Flow

Four steps pass data through the **filesystem** (not return values):

```
dop.in + config.json
       │
  Step 1  build_clusterspace  →  output/02_clusterspace.cs + output/02_doping_info.json
       │
  Step 2  generate_sqs        →  output/03_sqs_structure.json + output/SQS_*.vasp
       │
  Step 3  validate_export     →  SQS_FINAL.vasp + output/SUMMARY.txt
       │
  Step 4  validate_quality    →  output/QUALITY_REPORT.txt + output/quality_validation.json
```

Each step reads previous outputs from disk and writes its own. The CLI (`modern_interactive.py`) orchestrates by calling each `run()` sequentially.

## `run()` vs `main()` Pattern

Every pipeline module has two entry functions:
- **`run()`** — importable API. Raises exceptions on failure (no `sys.exit`).
- **`main()`** — CLI wrapper. Calls `run()`, catches exceptions, calls `sys.exit(1)`.

When calling from other Python code, always use `run()`. Never call `main()` programmatically.

## dop.in Input Format

Extended POSCAR with element annotations appended to coordinate lines:

```
dop.in                          # Title (any string)
1.0                             # Scale factor
  5.6573  0.0000  0.0000        # Lattice vectors
  0.0000  3.9551  0.0000
  0.0000  0.0000  5.6717
Nb  O  K  Na                    # Element names (informational only, parser ignores)
2  6  2  2                      # Counts (informational only, parser ignores)
Direct                          # Coordinate type
  0.000 0.500 0.500 Nb=1.0      # Ordered site: single element = 1.0
  0.000 0.000 0.000 K=0.5,Na=0.5  # Disordered site: concentrations must sum to 1.0
```

Annotation rules:
- `Element=1.0` → ordered site (fixed element)
- `K=0.5,Na=0.5` → disordered site (mixed occupancy, sum must equal 1.0)
- Parser reads annotations from coordinate lines only; lines 6-7 (element names/counts) are ignored

On first run without `dop.in`, the CLI auto-generates a template from `POSCAR`.

## Configuration

`config.json` is generated at runtime by the CLI, controls SQS parameters. **Gitignored** (per-user/per-system).

| Field | Meaning | Default |
|-------|---------|---------|
| `cluster_space.cutoffs` | Cluster cutoff radii (Å) | `[5.0]` |
| `sqs.method` | Generation method | `"enumeration"` or `"mc"` |
| `sqs.max_size` | Max unit cell multiplier (enumeration) | `8` |
| `sqs.supercell_matrix` | Supercell matrix (MC) | `[[2,0,0],[0,2,0],[0,0,2]]` |
| `sqs.tolerance` | Target deviation | `0.001` |

MC method **only supports diagonal supercell matrices** (non-diagonal elements must be 0). Validated in Pydantic model.

## Key Dependencies

```
icet>=3.2.0      # Core SQS engine (hard dependency, irreplaceable)
ase>=3.22.0      # Structure manipulation
pydantic>=1.10.0 # Config models (uses v2-style validators: field_validator, model_validator)
rich, questionary # CLI interface
numpy>=1.20.0
```

## Quality Thresholds (van de Walle 2013)

| Grade | Cluster Vector Deviation | Meaning |
|-------|--------------------------|---------|
| Excellent | < 0.001 | Ideal SQS |
| Good | < 0.01 | High quality |
| Acceptable | < 0.10 | Usable |
| Marginal | < 0.30 | Physical limit of small systems |
| Fail | ≥ 0.30 | Increase supercell size |

Defined as `QualityThresholds` class in `src/constants.py`.

## Code Conventions

- Imports: `from __future__ import annotations` in most files (not all — don't assume universal)
- Logging: `from src.logging_config import get_logger` → `logger = get_logger(__name__)`
- Pydantic models: all in `src/models.py`, never scattered across modules
- Constants: all magic numbers and thresholds in `src/constants.py`
- File path constants: `src/constants.py` → `FileNames` class
- icet log level set to WARNING in core modules: `set_log_config(level='WARNING')`
- VASP output: atoms sorted by element symbol before writing

## Testing

Tests use **pytest** with `conftest.py` fixtures:
- `tmp_path` — pytest built-in for temporary file isolation
- `monkeypatch` — for `chdir` in file-finding tests
- `temp_workdir` in conftest.py — chdir-based fixture (available but some tests use `tmp_path` directly)

Test files:
- `test_generality.py` — parsing across crystal structures (FCC binary, spinel, pure element)
- `test_workflow.py` — parser, Pydantic models, constants, quality thresholds
- `test_cli.py` — input validation helpers, UI constants

## Known Quirks

1. **Duplicate parser**: `src/core/build_clusterspace.py` has its own `parse_labeled_poscar()` function instead of using `src/parser.py`. Changes to dop.in parsing must update both.
2. **File numbering gap**: Intermediate files are numbered `02_*`, `03_*` (no `01_*`). This is by design — Step 1 output starts at `02`.
3. **Dead code**: `validate_quality.py` line 323-324 has `return results` duplicated — the second is unreachable.
4. **Console script**: `pyproject.toml` defines `sqskit` CLI entry point, but `requirements.txt` is missing `rich` and `questionary` (only in `pyproject.toml`).
5. **Enumeration vs MC**: Enumeration guarantees global optimum but only for small/medium systems. MC works for large systems but may find local optima.
6. **Entry file location**: `sqskit_modern.py` is in the repo root, NOT inside `src/`.
7. **Gitignored runtime files**: `config.json`, `dop.in`, `output/*`, `SQS_FINAL.vasp`, `atom_index_guide.txt` — never committed.

## Source Structure

```
sqskit_modern.py              # ← Main entry (repo root)
pyproject.toml                # Package config
requirements.txt              # Note: incomplete vs pyproject.toml
src/
├── cli/modern_interactive.py # Interactive CLI (rich + questionary)
├── core/                     # Pipeline steps
│   ├── build_clusterspace.py # Step 1: Build ClusterSpace
│   ├── generate_sqs_enum.py  # Step 2a: Enumeration SQS
│   ├── generate_sqs_mc.py    # Step 2b: MC SQS
│   ├── validate_export.py    # Step 3: Export results
│   └── validate_quality.py   # Step 4: Quality validation
├── utils/
│   ├── quality_utils.py      # Quality evaluation utilities
│   └── template_generator.py # dop.in template generator
├── parser.py                 # dop.in parser (StructureParser class)
├── models.py                 # Pydantic data models (all models here)
├── constants.py              # Global constants & thresholds
└── logging_config.py         # Logging configuration
tests/
├── conftest.py               # Shared fixtures
├── test_generality.py        # Cross-structure parsing tests
├── test_workflow.py          # Core module tests
└── test_cli.py               # CLI validation tests
```
