"""Tests for validators/scan.py — schema-tree traversal for validator discovery."""

from dataclasses import dataclass
from typing import Annotated

from dature import V
from dature.validators.scan import get_validator_providers, validator_target_dataclass_types


@dataclass
class _RecursiveNodeNoValidators:
    """Module-level self-referential schema with no validators anywhere — must be module-level
    so get_type_hints can resolve the string annotation."""

    name: str = ""
    child: "_RecursiveNodeNoValidators | None" = None


@dataclass
class _RecursiveNodeWithValidator:
    child: "Annotated[_RecursiveNodeWithValidator | None, V.check(lambda _: True, error_message='unreachable')]" = None


class TestGetValidatorProviders:
    def test_no_validators_returns_empty(self):
        @dataclass
        class Config:
            name: str
            port: int

        result = get_validator_providers(Config)

        assert result == []

    def test_self_referential_schema_does_not_recurse_unboundedly(self):
        result = get_validator_providers(_RecursiveNodeNoValidators)

        assert result == []


class TestValidatorTargetDataclassTypes:
    def test_no_validators_returns_empty(self):
        @dataclass
        class Cfg:
            name: str = "default"

        assert validator_target_dataclass_types(Cfg) == frozenset()

    def test_nested_type_with_annotated_validator_included(self):
        @dataclass
        class Inner:
            port: int

        @dataclass
        class Cfg:
            inner: Annotated[Inner, V.check(lambda i: i.port > 0, error_message="bad port")]

        assert validator_target_dataclass_types(Cfg) == {Inner}

    def test_nested_type_via_each_on_list_included(self):
        @dataclass
        class Item:
            value: int

        @dataclass
        class Cfg:
            items: Annotated[list[Item], V.each(V.check(lambda i: i.value > 0, error_message="bad value"))]

        assert validator_target_dataclass_types(Cfg) == {Item}

    def test_nested_type_without_direct_validator_excluded(self):
        @dataclass
        class Inner:
            port: int

        @dataclass
        class Cfg:
            inner: Inner

        assert validator_target_dataclass_types(Cfg) == frozenset()

    def test_recurses_into_nested_dataclasses_for_their_own_validators(self):
        @dataclass
        class Innermost:
            value: int

        @dataclass
        class Inner:
            deep: Annotated[Innermost, V.check(lambda i: i.value > 0, error_message="bad value")]

        @dataclass
        class Cfg:
            inner: Inner

        assert validator_target_dataclass_types(Cfg) == {Innermost}

    def test_self_recursive_schema_does_not_infinite_loop(self):
        """A validator directly on the recursive field includes the schema itself in the raw
        result — the caller (``RetortCache``) is the one that must subtract the top-level schema,
        since excluding it here would make the field pass treat the top level as unloadable."""

        result = validator_target_dataclass_types(_RecursiveNodeWithValidator)

        assert result == {_RecursiveNodeWithValidator}
