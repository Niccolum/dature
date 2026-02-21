from collections.abc import Callable, Sequence
from dataclasses import dataclass, is_dataclass
from typing import cast, get_type_hints

from adaptix._internal.common import Loader
from adaptix._internal.morphing.request_cls import LoaderRequest
from adaptix._internal.provider.essential import Mediator, Provider, RequestHandlerRegisterRecord
from adaptix._internal.provider.request_checkers import AlwaysTrueRequestChecker

from dature.field_path import FieldPath
from dature.protocols import DataclassInstance
from dature.types import FieldMapping, JSONValue


@dataclass(frozen=True, slots=True)
class AliasEntry:
    field_name: str
    aliases: tuple[str, ...]


def _resolve_nested_owner(
    owner: type[DataclassInstance],
    parts: tuple[str, ...],
) -> type[DataclassInstance]:
    """Walk type hints from owner through intermediate parts to find the leaf owner type."""
    current: type = owner
    for part in parts:
        hints = get_type_hints(current)
        if part not in hints:
            msg = f"Type '{current.__name__}' has no field '{part}'"
            raise TypeError(msg)
        current = hints[part]
        if not is_dataclass(current):
            msg = f"Intermediate field '{part}' of type '{current}' is not a dataclass"
            raise TypeError(msg)
    return current


def _build_alias_map(
    field_mapping: FieldMapping,
) -> dict[type[DataclassInstance] | str, list[AliasEntry]]:
    alias_map: dict[type[DataclassInstance] | str, list[AliasEntry]] = {}

    for field_path_key, aliases in field_mapping.items():
        if not isinstance(field_path_key, FieldPath):
            msg = f"field_mapping key must be a FieldPath, got {type(field_path_key).__name__}"
            raise TypeError(msg)
        field_path: FieldPath = field_path_key

        alias_tuple: tuple[str, ...]
        if isinstance(aliases, str):
            alias_tuple = (aliases,)
        else:
            alias_tuple = aliases

        if len(field_path.parts) == 0:
            msg = "FieldPath must contain at least one field name"
            raise ValueError(msg)

        owner: type[DataclassInstance] | str
        if len(field_path.parts) > 1:
            if isinstance(field_path.owner, str):
                msg = (
                    f"Nested FieldPath with string owner '{field_path.owner}' "
                    f"is not supported — cannot resolve intermediate types"
                )
                raise TypeError(msg)

            intermediate_parts = field_path.parts[:-1]
            owner = _resolve_nested_owner(field_path.owner, intermediate_parts)
        else:
            owner = field_path.owner

        field_name = field_path.parts[-1]
        entry = AliasEntry(field_name=field_name, aliases=alias_tuple)

        if owner not in alias_map:
            alias_map[owner] = []
        alias_map[owner].append(entry)

    return alias_map


def _get_entries_for_type(
    alias_map: dict[type[DataclassInstance] | str, list[AliasEntry]],
    target_type: type[DataclassInstance],
) -> list[AliasEntry] | None:
    entries = alias_map.get(target_type)
    if entries is not None:
        return entries

    for owner, owner_entries in alias_map.items():
        if isinstance(owner, str) and owner == target_type.__name__:
            return owner_entries

    return None


def _transform_dict(data: JSONValue, entries: list[AliasEntry]) -> JSONValue:
    if not isinstance(data, dict):
        return data

    result = dict(data)
    for entry in entries:
        if entry.field_name in result:
            continue
        for alias in entry.aliases:
            if alias in result:
                result[entry.field_name] = result.pop(alias)
                break

    return result


class AliasProvider(Provider):
    def __init__(self, field_mapping: FieldMapping) -> None:
        self._alias_map = _build_alias_map(field_mapping)

    def _wrap_handler(
        self,
        mediator: Mediator[Loader[JSONValue]],
        request: LoaderRequest,
    ) -> Callable[[JSONValue], JSONValue]:
        next_handler = mediator.provide_from_next()
        target_type = request.last_loc.type

        if not is_dataclass(target_type):
            return next_handler

        entries = _get_entries_for_type(
            self._alias_map,
            cast("type[DataclassInstance]", target_type),
        )
        if entries is None:
            return next_handler

        def aliased_handler(data: JSONValue) -> JSONValue:
            transformed = _transform_dict(data, entries)
            return next_handler(transformed)

        return aliased_handler

    def get_request_handlers(self) -> Sequence[RequestHandlerRegisterRecord]:
        return [(LoaderRequest, AlwaysTrueRequestChecker(), self._wrap_handler)]
