from typing import TYPE_CHECKING

from dature.field_path import FieldPath, validate_field_path_owner
from dature.protocols import DataclassInstance

if TYPE_CHECKING:
    from dature.metadata import FieldMergeStrategy, MergeRule


def extract_field_path(predicate: object, dataclass_: type[DataclassInstance] | None = None) -> str:
    if not isinstance(predicate, FieldPath):
        msg = f"Expected FieldPath, got {type(predicate).__name__}"
        raise TypeError(msg)
    if dataclass_ is not None:
        validate_field_path_owner(predicate, dataclass_)
    return predicate.as_path()


def build_field_merge_map(
    field_merges: "tuple[MergeRule, ...]",
    dataclass_: type[DataclassInstance] | None = None,
) -> "dict[str, FieldMergeStrategy]":
    result: dict[str, FieldMergeStrategy] = {}
    for rule in field_merges:
        path = extract_field_path(rule.predicate, dataclass_)
        result[path] = rule.strategy
    return result
