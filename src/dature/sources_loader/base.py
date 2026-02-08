import abc
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import TypeVar, cast, get_args, get_origin, get_type_hints

from adaptix import NameStyle as AdaptixNameStyle
from adaptix import Retort, loader, name_mapping
from adaptix.provider import Provider

from dature.sources_loader.loaders.base import bytes_from_string, complex_from_string
from dature.types import DotSeparatedPath, FieldMapping, JSONValue, NameStyle
from dature.validators.base import (
    create_root_validator_providers,
    create_validator_providers,
    extract_validators_from_type,
)
from dature.validators.protocols import DataclassInstance, ValidatorProtocol

T = TypeVar("T")


class ILoader(abc.ABC):
    def __init__(
        self,
        prefix: DotSeparatedPath | None = None,
        name_style: NameStyle | None = None,
        field_mapping: FieldMapping | None = None,
        root_validators: tuple[ValidatorProtocol, ...] | None = None,
    ) -> None:
        self._prefix = prefix
        self._name_style = name_style
        self._field_mapping = field_mapping
        self._root_validators = root_validators or ()
        self._retorts: dict[type, Retort] = {}

    def _additional_loaders(self) -> list[Provider]:
        return []

    def _get_adaptix_name_style(self) -> AdaptixNameStyle | None:
        if self._name_style is None:
            return None

        name_style_map = {
            "lower_snake": AdaptixNameStyle.LOWER_SNAKE,
            "upper_snake": AdaptixNameStyle.UPPER_SNAKE,
            "lower_camel": AdaptixNameStyle.CAMEL,
            "upper_camel": AdaptixNameStyle.PASCAL,
            "lower_kebab": AdaptixNameStyle.LOWER_KEBAB,
            "upper_kebab": AdaptixNameStyle.UPPER_KEBAB,
        }
        return name_style_map.get(self._name_style)

    def _get_name_mapping_provider(self) -> list[Provider]:
        providers: list[Provider] = []

        adaptix_name_style = self._get_adaptix_name_style()
        if adaptix_name_style is not None:
            providers.append(name_mapping(name_style=adaptix_name_style))

        if self._field_mapping:
            providers.append(name_mapping(map=self._field_mapping))

        return providers

    def _get_validator_providers(self, dataclass_: type[T]) -> list[Provider]:
        providers: list[Provider] = []
        type_hints = get_type_hints(dataclass_, include_extras=True)

        for field in fields(cast("type[DataclassInstance]", dataclass_)):
            if field.name not in type_hints:
                continue

            field_type = type_hints[field.name]
            validators = extract_validators_from_type(field_type)

            if validators:
                field_providers = create_validator_providers(dataclass_, field.name, validators)
                providers.extend(field_providers)

            base_type = field_type
            if get_origin(field_type) is not None:
                args = get_args(field_type)
                if args:
                    base_type = args[0]

            if is_dataclass(base_type):
                nested_providers = self._get_validator_providers(
                    cast("type[DataclassInstance]", base_type),
                )
                providers.extend(nested_providers)

        return providers

    def _create_retort(self) -> Retort:
        default_loaders: list[Provider] = [
            loader(bytes, bytes_from_string),
            loader(complex, complex_from_string),
        ]
        return Retort(
            strict_coercion=False,
            recipe=[
                *default_loaders,
                *self._additional_loaders(),
                *self._get_name_mapping_provider(),
            ],
        )

    def _create_validating_retort(self, dataclass_: type[T]) -> Retort:
        root_validator_providers = create_root_validator_providers(
            dataclass_,
            self._root_validators,
        )
        return Retort(
            strict_coercion=False,
            recipe=[
                *self._get_validator_providers(dataclass_),
                *root_validator_providers,
            ],
        )

    @abc.abstractmethod
    def _load(self, path: Path) -> JSONValue: ...

    def _apply_prefix(self, data: JSONValue) -> JSONValue:
        if not self._prefix:
            return data

        for key in self._prefix.split("."):
            if not isinstance(data, dict):
                return {}
            if key not in data:
                return {}
            data = data[key]

        return data

    def _pre_processing(self, data: JSONValue) -> JSONValue:
        return self._apply_prefix(data)

    def _transform_to_dataclass(self, data: JSONValue, dataclass_: type[T]) -> T:
        if dataclass_ not in self._retorts:
            self._retorts[dataclass_] = self._create_retort()
        return self._retorts[dataclass_].load(data, dataclass_)

    def load(self, path: Path, dataclass_: type[T]) -> T:
        data = self._load(path)
        pre_processed_data = self._pre_processing(data)
        return self._transform_to_dataclass(pre_processed_data, dataclass_)
