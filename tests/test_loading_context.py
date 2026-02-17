"""Tests for loading_context.py."""

from dataclasses import dataclass, fields
from typing import Any

from dature.loading_context import merge_fields


class TestMergeFields:
    @dataclass
    class Config:
        name: str
        port: int
        debug: bool

    @dataclass
    class Loaded:
        name: str = "loaded_name"
        port: int = 8080
        debug: bool = True

    def _field_list(self) -> tuple[Any, ...]:
        return fields(self.Config)

    def test_no_explicit_fields(self):
        loaded = self.Loaded()

        result = merge_fields(loaded, self._field_list(), (), {})

        assert result == {"name": "loaded_name", "port": 8080, "debug": True}

    def test_all_kwargs_explicit(self):
        loaded = self.Loaded()
        kwargs = {"name": "explicit", "port": 9090, "debug": False}

        result = merge_fields(loaded, self._field_list(), (), kwargs)

        assert result == {"name": "explicit", "port": 9090, "debug": False}

    def test_partial_kwargs(self):
        loaded = self.Loaded()

        result = merge_fields(loaded, self._field_list(), (), {"name": "explicit"})

        assert result == {"name": "explicit", "port": 8080, "debug": True}

    def test_positional_args(self):
        loaded = self.Loaded()

        result = merge_fields(loaded, self._field_list(), ("positional_name",), {})

        assert result == {"port": 8080, "debug": True}

    def test_mixed_args_and_kwargs(self):
        loaded = self.Loaded()

        result = merge_fields(
            loaded,
            self._field_list(),
            ("positional_name",),
            {"debug": False},
        )

        assert result == {"port": 8080, "debug": False}

    def test_args_beyond_field_count_ignored(self):
        loaded = self.Loaded()

        result = merge_fields(
            loaded,
            self._field_list(),
            ("a", "b", "c", "extra"),
            {},
        )

        assert result == {}
