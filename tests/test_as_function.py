"""Tests for main functionality.

This module tests the @load main itself, not the underlying loaders.
Loader functionality is tested in tests/sources_loader/.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from dature import load


class TestLoadAsFunction:
    @pytest.mark.parametrize(
        ("extension", "content", "prefix"),
        [
            (".env", "test_var=value", None),
            (".yaml", "test_var: value", None),
            (".yml", "test_var: value", None),
            (".json", '{"test_var": "value"}', None),
            (".toml", 'test_var = "value"', None),
            (".ini", "[DEFAULT]\ntest_var = value", "DEFAULT"),
            (".cfg", "[DEFAULT]\ntest_var = value", "DEFAULT"),
        ],
    )
    def test_success(self, tmp_path: Path, extension: str, content: str, prefix: str):
        """Test that main correctly detects loader type by file extension."""
        config_file = tmp_path / f"config{extension}"
        config_file.write_text(content)

        @dataclass
        class Config:
            test_var: str

        expected_data = Config(test_var="value")

        result = load(file_=str(config_file), prefix=prefix, dataclass_=Config)

        assert result == expected_data

    def test_load_as_function_from_env(self, monkeypatch):
        """Test load() as function from environment variables."""
        monkeypatch.setenv("APP_NAME", "EnvFunctionTest")
        monkeypatch.setenv("APP_DEBUG", "true")

        @dataclass
        class Config:
            name: str
            debug: bool

        expected_data = Config(name="EnvFunctionTest", debug=True)

        config = load(prefix="APP_", dataclass_=Config)

        assert config == expected_data
