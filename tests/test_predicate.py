"""Tests for predicate path extraction utilities."""

from dataclasses import dataclass

import pytest

from dature.field_path import F
from dature.metadata import FieldMergeStrategy, MergeRule
from dature.predicate import build_field_merge_map, extract_field_path


class TestExtractFieldPath:
    def test_single_field(self):
        @dataclass
        class Config:
            host: str

        assert extract_field_path(F[Config].host) == "host"

    def test_nested_field(self):
        @dataclass
        class Database:
            uri: str

        @dataclass
        class Config:
            database: Database

        assert extract_field_path(F[Config].database.uri) == "database.uri"

    def test_no_fields_raises_value_error(self):
        @dataclass
        class Config:
            host: str

        with pytest.raises(ValueError, match="at least one field name"):
            extract_field_path(F[Config])


class TestBuildFieldMergeMap:
    def test_builds_map_from_rules(self):
        @dataclass
        class Config:
            host: str
            port: int
            tags: list[str]

        rules = (
            MergeRule(F[Config].host, FieldMergeStrategy.FIRST_WINS),
            MergeRule(F[Config].tags, FieldMergeStrategy.APPEND),
        )

        result = build_field_merge_map(rules)

        assert result == {
            "host": FieldMergeStrategy.FIRST_WINS,
            "tags": FieldMergeStrategy.APPEND,
        }

    def test_empty_rules(self):
        result = build_field_merge_map(())
        assert result == {}

    def test_nested_field_path(self):
        @dataclass
        class Database:
            host: str

        @dataclass
        class Config:
            database: Database

        rules = (MergeRule(F[Config].database.host, FieldMergeStrategy.LAST_WINS),)

        result = build_field_merge_map(rules)

        assert result == {"database.host": FieldMergeStrategy.LAST_WINS}
