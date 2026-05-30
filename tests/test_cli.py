"""测试 CLI 验证方法和常量定义"""

import pytest
from src.cli.modern_interactive import ModernSQSInterface
from src.constants import UIConfig


class TestInputValidation:
    """ModernSQSInterface._validate_float / _validate_int"""

    @pytest.mark.parametrize(
        "value,min_val,max_val,expected",
        [
            ("5", 0, 10, True),
            ("0", 0, 10, True),
            ("10", 0, 10, True),
            ("-1", 0, 10, False),
            ("15", 0, 10, False),
            ("abc", 0, 10, False),
            ("", 0, 10, False),
        ],
    )
    def test_validate_int(self, value, min_val, max_val, expected):
        assert ModernSQSInterface._validate_int(value, min_val, max_val) == expected

    @pytest.mark.parametrize(
        "value,min_val,max_val,expected",
        [
            ("3.14", 0.0, 10.0, True),
            ("0.0", 0.0, 10.0, True),
            ("-0.1", 0.0, 10.0, False),
            ("10.1", 0.0, 10.0, False),
            ("abc", 0.0, 10.0, False),
        ],
    )
    def test_validate_float(self, value, min_val, max_val, expected):
        assert ModernSQSInterface._validate_float(value, min_val, max_val) == expected


class TestColors:
    """UIConfig.Colors 常量"""

    @pytest.fixture(autouse=True)
    def colors(self):
        return UIConfig.Colors

    def test_colors_exist(self, colors):
        for attr in ["HEADER", "OKGREEN", "FAIL", "ENDC", "WARNING"]:
            assert hasattr(colors, attr)

    def test_colors_are_strings(self, colors):
        assert isinstance(colors.HEADER, str)
        assert isinstance(colors.OKGREEN, str)
        assert isinstance(colors.FAIL, str)
        assert isinstance(colors.ENDC, str)

    def test_colors_are_ansi_escape(self, colors):
        assert colors.HEADER.startswith("\033[")
        assert colors.ENDC.startswith("\033[")
