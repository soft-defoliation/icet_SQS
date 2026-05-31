"""通用性测试 — 测试对不同晶体结构和掺杂体系的支持"""

import pytest

from pathlib import Path

from sqs_workflow.parser import StructureParser
from sqs_workflow.utils.template_generator import UniversalTemplateGenerator


class TestBinaryAlloyParsing:
    """二元合金 dop.in 解析"""

    @pytest.fixture
    def fcc_dop_in(self, tmp_path):
        content = """Cu-Au FCC
1.0
3.615 0.0 0.0
0.0 3.615 0.0
0.0 0.0 3.615
Cu Au
1 1
Direct
 0.0 0.0 0.0 Cu=0.5,Au=0.5
 0.5 0.5 0.0 Cu=0.5,Au=0.5
 0.5 0.0 0.5 Cu=0.5,Au=0.5
 0.0 0.5 0.5 Cu=0.5,Au=0.5
"""
        dop_file = tmp_path / "dop.in"
        dop_file.write_text(content)
        return dop_file

    def test_parse_fcc_binary_alloy(self, fcc_dop_in):
        parsed = StructureParser(fcc_dop_in).parse()
        assert len(parsed.sites) == 4
        assert parsed.n_disordered == 4
        assert parsed.n_ordered == 0

    def test_fcc_all_sites_disordered(self, fcc_dop_in):
        parsed = StructureParser(fcc_dop_in).parse()
        for site in parsed.sites:
            assert site.is_disordered
            assert site.concentration == {"Cu": 0.5, "Au": 0.5}


class TestSpinelParsing:
    """尖晶石结构 dop.in 解析（A位无序，B位有序）"""

    @pytest.fixture
    def spinel_dop_in(self, tmp_path):
        content = """MgAl2O4 Spinel
1.0
8.08 0.0 0.0
0.0 8.08 0.0
0.0 0.0 8.08
Mg Al O
1 2 4
Direct
 0.125 0.125 0.125 Mg=0.5,Al=0.5
 0.500 0.500 0.500 Al=1.0
 0.500 0.500 0.500 Al=1.0
 0.260 0.260 0.260 O=1.0
 0.740 0.740 0.740 O=1.0
 0.260 0.740 0.740 O=1.0
 0.740 0.260 0.740 O=1.0
"""
        dop_file = tmp_path / "dop.in"
        dop_file.write_text(content)
        return dop_file

    def test_parse_spinel(self, spinel_dop_in):
        parsed = StructureParser(spinel_dop_in).parse()
        assert len(parsed.sites) == 7
        ordered = [s for s in parsed.sites if not s.is_disordered]
        disordered = [s for s in parsed.sites if s.is_disordered]
        assert len(disordered) == 1
        assert len(ordered) == 6

    def test_spinel_disordered_site_has_mixed_occupancy(self, spinel_dop_in):
        parsed = StructureParser(spinel_dop_in).parse()
        disordered = [s for s in parsed.sites if s.is_disordered]
        assert disordered[0].concentration == {"Mg": 0.5, "Al": 0.5}


class TestTemplateGenerator:
    """模板生成器测试"""

    def test_module_exists(self):
        assert Path("src/sqs_workflow/utils/template_generator.py").exists()

    def test_class_importable(self):
        assert UniversalTemplateGenerator is not None


class TestSingleElementSystem:
    """纯元素体系（无掺杂）"""

    @pytest.fixture
    def pure_dop_in(self, tmp_path):
        content = """Pure Nb
1.0
3.3 0.0 0.0
0.0 3.3 0.0
0.0 0.0 3.3
Nb
1
Direct
 0.0 0.0 0.0 Nb=1.0
 0.5 0.5 0.5 Nb=1.0
"""
        dop_file = tmp_path / "dop.in"
        dop_file.write_text(content)
        return dop_file

    def test_parse_pure_system(self, pure_dop_in):
        parsed = StructureParser(pure_dop_in).parse()
        assert parsed.n_disordered == 0
        assert parsed.n_ordered == 2
        assert parsed.target_concentrations == {}
