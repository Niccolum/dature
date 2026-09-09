"""Tests for skip_field_provider.py."""

from dataclasses import dataclass, field

import pytest
from adaptix import Retort
from adaptix.load_error import LoadError

from dature.skip_field_provider import (
    ModelToDictProvider,
    RequireUnsafeFactoryFieldsProvider,
    SkipFieldProvider,
    filter_invalid_fields,
)


@dataclass
class _Inner:
    a: int
    b: int


@dataclass
class _HostPort:
    host: str
    port: int


@dataclass
class _FactoryConfig:
    inner: _Inner = field(default_factory=_Inner)


@pytest.fixture
def probe_retort() -> Retort:
    return Retort(strict_coercion=False, recipe=[SkipFieldProvider(), ModelToDictProvider()])


@pytest.fixture
def factory_retort() -> Retort:
    return Retort(recipe=[RequireUnsafeFactoryFieldsProvider()])


class TestFilterInvalidFields:
    def test_all_fields_valid(self, probe_retort: Retort):
        raw = {"host": "localhost", "port": 8080}
        result = filter_invalid_fields(raw, probe_retort, _HostPort, None)

        assert result.cleaned_dict == {"host": "localhost", "port": 8080}
        assert result.skipped_paths == []

    def test_one_field_invalid(self, probe_retort: Retort):
        raw = {"host": "localhost", "port": "abc"}
        result = filter_invalid_fields(raw, probe_retort, _HostPort, None)

        assert result.cleaned_dict == {"host": "localhost"}
        assert result.skipped_paths == ["port"]

    def test_nested_field_invalid(self, probe_retort: Retort):
        @dataclass
        class Database:
            host: str
            port: int

        @dataclass
        class Config:
            db: Database

        raw = {"db": {"host": "localhost", "port": "abc"}}
        result = filter_invalid_fields(raw, probe_retort, Config, None)

        assert result.cleaned_dict == {"db": {"host": "localhost"}}
        assert result.skipped_paths == ["db.port"]

    def test_allowed_fields_restricts_skip(self, probe_retort: Retort):
        @dataclass
        class Config:
            host: str
            port: int
            timeout: int

        raw = {"host": "localhost", "port": "abc", "timeout": "bad"}
        result = filter_invalid_fields(raw, probe_retort, Config, {"port"})

        assert result.cleaned_dict == {"host": "localhost", "timeout": "bad"}
        assert result.skipped_paths == ["port"]

    def test_non_dict_input(self, probe_retort: Retort):
        result = filter_invalid_fields("not a dict", probe_retort, _HostPort, None)

        assert result.cleaned_dict == "not a dict"
        assert result.skipped_paths == []


class TestRequireUnsafeFactoryFieldsProvider:
    def test_unsafe_factory_field_becomes_required(self, factory_retort: Retort):
        with pytest.raises(LoadError):
            factory_retort.load({}, _FactoryConfig)

    def test_unsafe_factory_field_loads_when_present(self, factory_retort: Retort):
        result = factory_retort.load({"inner": {"a": 1, "b": 2}}, _FactoryConfig)

        assert result == _FactoryConfig(inner=_Inner(a=1, b=2))

    def test_safe_factory_schema_passes_through_to_default_recipe(self, factory_retort: Retort):
        @dataclass
        class Config:
            items: list[int] = field(default_factory=list)

        result = factory_retort.load({}, Config)

        assert result == Config(items=[])

    def test_optional_field_before_unsafe_factory_field_still_loads(self, factory_retort: Retort):
        """Declaration order puts an optional field before the now-required one — params must
        be rebuilt as KW_ONLY or positional ordering would break."""

        @dataclass
        class Config:
            debug: bool = False
            inner: _Inner = field(default_factory=_Inner)

        result = factory_retort.load({"debug": True, "inner": {"a": 1, "b": 2}}, Config)

        assert result == Config(debug=True, inner=_Inner(a=1, b=2))
