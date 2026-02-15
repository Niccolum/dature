from typing import TYPE_CHECKING

from dature.field_path import FieldPath

if TYPE_CHECKING:
    from dature.metadata import FieldMergeStrategy, MergeRule


def extract_field_path(predicate: object) -> str:
    if not isinstance(predicate, FieldPath):
        msg = f"Expected FieldPath, got {type(predicate).__name__}"
        raise TypeError(msg)
    return predicate.as_path()


def build_field_merge_map(field_merges: "tuple[MergeRule, ...]") -> "dict[str, FieldMergeStrategy]":
    result: dict[str, FieldMergeStrategy] = {}
    for rule in field_merges:
        path = extract_field_path(rule.predicate)
        result[path] = rule.strategy
    return result
