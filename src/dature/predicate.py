from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING, get_type_hints

from dature.field_path import FieldPath, _resolve_field_type, validate_field_path_owner
from dature.protocols import DataclassInstance

if TYPE_CHECKING:
    from dature.metadata import FieldGroup, FieldMergeStrategy, MergeRule


@dataclass(frozen=True, slots=True)
class ResolvedFieldGroup:
    paths: tuple[str, ...]


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


def _expand_dataclass_fields(prefix: str, dc_type: type) -> list[str]:
    result: list[str] = []
    hints = get_type_hints(dc_type)
    for f in fields(dc_type):
        child_path = f"{prefix}.{f.name}" if prefix else f.name
        child_type = hints.get(f.name)
        if child_type is not None and is_dataclass(child_type):
            result.extend(_expand_dataclass_fields(child_path, child_type))
        else:
            result.append(child_path)
    return result


def build_field_group_paths(
    field_groups: "tuple[FieldGroup, ...]",
    dataclass_: type[DataclassInstance],
) -> tuple[ResolvedFieldGroup, ...]:
    resolved: list[ResolvedFieldGroup] = []
    for group in field_groups:
        paths: list[str] = []
        for field in group.fields:
            path = extract_field_path(field, dataclass_)
            if isinstance(field, FieldPath) and isinstance(field.owner, type):
                resolved_type = _resolve_field_type(field.owner, field.parts)
            else:
                resolved_type = _resolve_field_type(dataclass_, tuple(path.split(".")))
            if resolved_type is not None:
                paths.extend(_expand_dataclass_fields(path, resolved_type))
            else:
                paths.append(path)
        resolved.append(ResolvedFieldGroup(paths=tuple(paths)))
    return tuple(resolved)
