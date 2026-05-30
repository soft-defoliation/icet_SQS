"""pytest 全局配置和共享 fixtures"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_workdir():
    """在临时目录中运行测试（隔离文件系统副作用）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original = Path.cwd()
        import os

        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original)
