from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dature.sources_loader.resolver import LoaderType
    from dature.types import DotSeparatedPath, FieldMapping, NameStyle
    from dature.validators.base import RootValidatorProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadMetadata:
    file_: str | None = None
    loader: "LoaderType | None" = None
    prefix: "DotSeparatedPath | None" = None
    name_style: "NameStyle | None" = None
    field_mapping: "FieldMapping | None" = None
    root_validators: "tuple[RootValidatorProtocol, ...] | None" = None
