"""测试核心模块：parser、models、constants"""

import pytest
import tempfile
from pathlib import Path

from src.parser import StructureParser, ParsedStructure
from src.models import SQSWorkflowConfig, SQSConfig, ClusterSpaceConfig
from src.constants import QualityThresholds, FileNames, Defaults, MethodConfig


class TestStructureParser:
    """dop.in 解析器测试"""

    @pytest.fixture
    def valid_dop_in(self):
        content = """KNN dop.in
1.0
  5.6573  0.0000  0.0000
  0.0000  3.9551  0.0000
  0.0000  0.0000  5.6717
Nb O K Na
2 6 2 2
Direct
  0.000  0.500  0.500  Nb=1.0
  0.500  0.500  0.000  Nb=1.0
  0.000  0.000  0.000  K=0.5,Na=0.5
  0.500  0.000  0.500  K=0.5,Na=0.5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
            f.write(content)
        tmp_path = Path(f.name)
        dop_path = tmp_path.parent / "dop.in"
        tmp_path.rename(dop_path)
        yield dop_path
        dop_path.unlink()

    def test_parse_structure(self, valid_dop_in):
        parsed = StructureParser(valid_dop_in).parse()
        assert isinstance(parsed, ParsedStructure)
        assert len(parsed.sites) == 4
        assert parsed.n_disordered == 2
        assert parsed.n_ordered == 2
        assert "A" in parsed.target_concentrations

    def test_parse_doping_sites(self, valid_dop_in):
        parsed = StructureParser(valid_dop_in).parse()
        ordered = [s for s in parsed.sites if not s.is_disordered]
        disordered = [s for s in parsed.sites if s.is_disordered]
        assert len(ordered) == 2
        assert len(disordered) == 2
        assert ordered[0].concentration == {"Nb": 1.0}
        assert disordered[0].concentration == {"K": 0.5, "Na": 0.5}

    def test_find_dop_in_cwd(self, valid_dop_in, monkeypatch):
        monkeypatch.chdir(valid_dop_in.parent)
        found = StructureParser.find_dop_in()
        assert found == valid_dop_in

    def test_find_dop_in_not_found(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            StructureParser.find_dop_in()


class TestPydanticModels:
    """Pydantic 配置模型验证"""

    def test_default_config(self):
        config = SQSWorkflowConfig()
        assert config.sqs.method == MethodConfig.ENUMERATION
        assert config.sqs.max_size == Defaults.MAX_SIZE
        assert config.cluster_space.cutoffs == Defaults.CUTOFFS

    def test_invalid_method_rejected(self):
        with pytest.raises(ValueError):
            SQSConfig(method="invalid_method")

    def test_invalid_cutoffs_rejected(self):
        with pytest.raises(ValueError):
            ClusterSpaceConfig(cutoffs=[])

    def test_supercell_matrix_validation(self):
        with pytest.raises(ValueError):
            SQSConfig(method="mc", supercell_matrix=[[1, 1, 0], [0, 1, 0], [0, 0, 1]])

    def test_json_roundtrip(self, tmp_path):
        config = SQSWorkflowConfig()
        config_file = tmp_path / "config.json"
        config.to_file(config_file)
        loaded = SQSWorkflowConfig.from_file(config_file)
        assert loaded.sqs.method == config.sqs.method


class TestQualityThresholds:
    """质量阈值测试"""

    @pytest.mark.parametrize(
        "deviation,expected_grade,expected_pass",
        [
            (0.0005, "优秀 ✅", True),
            (0.005, "良好 ✓", True),
            (0.05, "可用", True),
            (0.15, "可接受(有限系统限制)", True),
            (0.50, "失败 ❌", False),
        ],
    )
    def test_thresholds(self, deviation, expected_grade, expected_pass):
        grade, passed, _ = QualityThresholds.evaluate(deviation)
        assert grade == expected_grade
        assert passed == expected_pass


class TestFileNames:
    """文件名常量测试"""

    def test_all_names_defined(self):
        for attr in [
            "DOP_IN",
            "CONFIG",
            "CLUSTERSPACE",
            "DOPING_INFO",
            "SQS_STRUCTURE",
            "FINAL_VASP",
            "SUMMARY",
            "QUALITY_REPORT",
        ]:
            assert hasattr(FileNames, attr)

    def test_output_paths_have_prefix(self):
        assert FileNames.CLUSTERSPACE.startswith("output/")
        assert FileNames.DOPING_INFO.startswith("output/")
        assert FileNames.SQS_STRUCTURE.startswith("output/")


class TestQualityAnalysis:
    """新质量分析函数测试"""

    def test_perfect_matches(self):
        from src.utils.quality_utils import count_perfect_matches
        import numpy as np

        cv_sqs = np.array([1.0, 0.001, 0.0005])
        cv_target = np.array([1.0, 0.0, 0.0])
        result = count_perfect_matches(cv_sqs, cv_target)
        assert result["excellent"]["matched"] == 2
        assert result["good"]["matched"] == 3

    def test_count_perfect_matches_all_zero(self):
        from src.utils.quality_utils import count_perfect_matches
        import numpy as np

        cv = np.zeros(5)
        result = count_perfect_matches(cv, cv)
        assert result["excellent"]["matched"] == 5
        assert result["excellent"]["percent"] == 100.0

    def test_deviation_bar(self):
        from src.core.validate_quality import _deviation_bar

        bar_zero = _deviation_bar(0.0)
        assert "✓" in bar_zero
        bar_bad = _deviation_bar(0.5)
        assert "✗" in bar_bad
