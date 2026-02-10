"""Pytest configuration and shared fixtures."""

from collections.abc import Callable
from pathlib import Path

import pytest
from adaptix.load_error import ValidationLoadError


def _collect_validation_errors(
    exc: BaseException,
    errors: list[ValidationLoadError],
) -> None:
    if isinstance(exc, ValidationLoadError):
        errors.append(exc)
    if hasattr(exc, "exceptions"):
        for sub_exc in exc.exceptions:
            _collect_validation_errors(sub_exc, errors)


@pytest.fixture
def collect_validation_errors() -> Callable[[BaseException], list[ValidationLoadError]]:
    def _collect(exc: BaseException) -> list[ValidationLoadError]:
        errors: list[ValidationLoadError] = []
        _collect_validation_errors(exc, errors)
        return errors

    return _collect


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


# ENV fixtures
@pytest.fixture
def prefixed_env_file(fixtures_dir: Path) -> Path:
    """Path to .env file with APP_ prefix."""
    return fixtures_dir / "prefixed.env"


@pytest.fixture
def custom_separator_env_file(fixtures_dir: Path) -> Path:
    """Path to .env file with custom separator (dot instead of __)."""
    return fixtures_dir / "custom_separator.env"


@pytest.fixture
def all_types_env_file(fixtures_dir: Path) -> Path:
    """Path to all_types.env file."""
    return fixtures_dir / "all_types.env"


# YAML fixtures
@pytest.fixture
def yaml_config_with_env_vars_file(fixtures_dir: Path) -> Path:
    """Path to YAML config file with environment variable substitution."""
    return fixtures_dir / "config_with_env_vars.yaml"


@pytest.fixture
def prefixed_yaml_file(fixtures_dir: Path) -> Path:
    """Path to YAML file with prefix."""
    return fixtures_dir / "prefixed.yaml"


@pytest.fixture
def all_types_yaml_file(fixtures_dir: Path) -> Path:
    """Path to all_types.yaml file."""
    return fixtures_dir / "all_types.yaml"


# JSON fixtures
@pytest.fixture
def prefixed_json_file(fixtures_dir: Path) -> Path:
    """Path to JSON file with prefix."""
    return fixtures_dir / "prefixed.json"


@pytest.fixture
def all_types_json_file(fixtures_dir: Path) -> Path:
    """Path to all_types.json file."""
    return fixtures_dir / "all_types.json"


# JSON5 fixtures
@pytest.fixture
def prefixed_json5_file(fixtures_dir: Path) -> Path:
    """Path to JSON5 file with prefix."""
    return fixtures_dir / "prefixed.json5"


@pytest.fixture
def all_types_json5_file(fixtures_dir: Path) -> Path:
    """Path to all_types.json5 file."""
    return fixtures_dir / "all_types.json5"


# TOML fixtures
@pytest.fixture
def prefixed_toml_file(fixtures_dir: Path) -> Path:
    """Path to TOML file with prefix."""
    return fixtures_dir / "prefixed.toml"


@pytest.fixture
def all_types_toml_file(fixtures_dir: Path) -> Path:
    """Path to all_types.toml file."""
    return fixtures_dir / "all_types.toml"


# INI fixtures
@pytest.fixture
def ini_sections_file(fixtures_dir: Path) -> Path:
    """Path to INI file with multiple sections and DEFAULT inheritance."""
    return fixtures_dir / "sections.ini"


@pytest.fixture
def prefixed_ini_file(fixtures_dir: Path) -> Path:
    """Path to INI file with prefix."""
    return fixtures_dir / "prefixed.ini"


@pytest.fixture
def all_types_ini_file(fixtures_dir: Path) -> Path:
    """Path to all_types.ini file."""
    return fixtures_dir / "all_types.ini"
