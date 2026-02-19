from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from dature.loader_type import LoaderType, get_loader_type

if TYPE_CHECKING:
    from dature.field_path import FieldPath
    from dature.protocols import ValidatorProtocol
    from dature.types import DotSeparatedPath, FieldMapping, NameStyle


class MergeStrategy(StrEnum):
    LAST_WINS = "last_wins"
    FIRST_WINS = "first_wins"
    RAISE_ON_CONFLICT = "raise_on_conflict"


class FieldMergeStrategy(StrEnum):
    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"
    APPEND = "append"
    APPEND_UNIQUE = "append_unique"
    PREPEND = "prepend"
    PREPEND_UNIQUE = "prepend_unique"
    MAX = "max"
    MIN = "min"


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadMetadata:
    file_: str | None = None
    loader: "LoaderType | None" = None
    prefix: "DotSeparatedPath | None" = None
    split_symbols: str = "__"
    name_style: "NameStyle | None" = None
    field_mapping: "FieldMapping | None" = None
    root_validators: "tuple[ValidatorProtocol, ...] | None" = None
    enable_expand_env_vars: bool = True
    skip_if_broken: bool | None = None
    skip_if_invalid: "bool | tuple[FieldPath, ...] | None" = None

    def __repr__(self) -> str:
        loader_type = get_loader_type(self.loader, self.file_)
        if self.file_ is not None:
            return f"{loader_type} '{self.file_}'"
        return loader_type


@dataclass(frozen=True, slots=True)
class MergeRule:
    predicate: object
    strategy: FieldMergeStrategy


@dataclass(frozen=True, slots=True)
class FieldGroup:
    fields: tuple[object, ...]

    def __init__(self, *fields: object) -> None:
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True, slots=True, kw_only=True)
class MergeMetadata:
    sources: tuple[LoadMetadata, ...]
    strategy: MergeStrategy = MergeStrategy.LAST_WINS
    field_merges: tuple[MergeRule, ...] = ()
    field_groups: tuple[FieldGroup, ...] = ()
    skip_broken_sources: bool = False
    skip_invalid_fields: bool = False
