"""Unit tests for the known-key tree builder — independent of any source or load()."""

from dataclasses import dataclass
from typing import Any

import pytest

from dature.loading.strict.known_keys import ElementsNode, ObjectNode, known_key_tree


@dataclass
class _Db:
    host: str


@pytest.mark.parametrize(
    "field_type",
    [dict[str, _Db], list[_Db], tuple[_Db, ...]],
    ids=["dict-str-db", "list-db", "tuple-db"],
)
def test_container_of_dataclass_is_elements_node(field_type: type) -> None:
    @dataclass
    class Config:
        items: field_type  # type: ignore[valid-type]

    tree = known_key_tree(Config)

    assert isinstance(tree.children["items"], ElementsNode)
    assert isinstance(tree.children["items"].element, ObjectNode)
    assert tree.children["items"].element.keys == frozenset({"host"})


def test_union_dataclass_field_is_object_node() -> None:
    @dataclass
    class Config:
        db: _Db | None = None

    tree = known_key_tree(Config)

    assert isinstance(tree.children["db"], ObjectNode)
    assert tree.children["db"].keys == frozenset({"host"})


@pytest.mark.parametrize(
    "field_type",
    [dict[str, Any], list[str], Any],
    ids=["dict-str-any", "list-str", "any"],
)
def test_opaque_field_type_has_no_child_node(field_type: type) -> None:
    @dataclass
    class Config:
        extra: field_type  # type: ignore[valid-type]

    tree = known_key_tree(Config)

    assert "extra" not in tree.children


@dataclass
class _CyclicNode:
    child: "_CyclicNode | None" = None


def test_cyclic_schema_reuses_same_node_instance() -> None:
    tree = known_key_tree(_CyclicNode)

    assert tree.children["child"] is tree
