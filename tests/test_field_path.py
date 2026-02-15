"""Tests for FieldPath lazy field path builder."""

from dataclasses import dataclass

import pytest

from dature.field_path import F, FieldPath


@dataclass
class _Database:
    uri: str


@dataclass
class _Cfg:
    host: str
    database: _Database


class TestFieldPath:
    @pytest.mark.parametrize(
        ("field_path", "expected_path"),
        [
            pytest.param(F[_Cfg].host, "host", id="single_field_class"),
            pytest.param(F[_Cfg].database.uri, "database.uri", id="nested_field_class"),
            pytest.param(F["Config"].host, "host", id="single_field_string"),
            pytest.param(F["Config"].database.uri, "database.uri", id="nested_field_string"),
        ],
    )
    def test_path(self, field_path: FieldPath, expected_path: str):
        assert field_path.as_path() == expected_path

    def test_owner_is_class(self):
        assert F[_Cfg].host.owner is _Cfg

    def test_owner_is_string(self):
        assert F["Config"].host.owner == "Config"

    def test_no_fields_raises_value_error(self):
        with pytest.raises(ValueError, match="at least one field name"):
            F[_Cfg].as_path()

    def test_is_frozen(self):
        fp = F[_Cfg].host
        with pytest.raises(AttributeError):
            fp.owner = "other"

    def test_nonexistent_field_raises_attribute_error(self):
        with pytest.raises(AttributeError, match="'_Cfg' has no field 'nonexistent'"):
            _ = F[_Cfg].nonexistent

    def test_not_a_dataclass_raises_type_error(self):
        class Plain:
            pass

        with pytest.raises(TypeError, match="'Plain' is not a dataclass"):
            F[Plain]

    def test_string_owner_skips_validation(self):
        fp = F["Whatever"].anything.deep.path
        assert fp.as_path() == "anything.deep.path"
