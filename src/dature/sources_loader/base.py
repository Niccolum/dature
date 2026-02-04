import abc
from pathlib import Path
from typing import TypeVar

from adaptix import NameStyle as AdaptixNameStyle
from adaptix import Retort, loader, name_mapping
from adaptix.provider import Provider

from dature.sources_loader.loaders.base import bytes_from_string, complex_from_string
from dature.types import DotSeparatedPath, FieldMapping, JSONValue, NameStyle

T = TypeVar("T")


class ILoader(abc.ABC):
    def __init__(
        self,
        prefix: DotSeparatedPath | None = None,
        name_style: NameStyle | None = None,
        field_mapping: FieldMapping | None = None,
    ) -> None:
        self._prefix = prefix
        self._name_style = name_style
        self._field_mapping = field_mapping
        self._retort = self._create_retort()

    def _additional_loaders(self) -> list[Provider]:
        return []

    def _get_adaptix_name_style(self) -> AdaptixNameStyle | None:  # noqa: PLR0911
        if self._name_style is None:
            return None

        match self._name_style:
            case "lower_snake":
                return AdaptixNameStyle.LOWER_SNAKE
            case "upper_snake":
                return AdaptixNameStyle.UPPER_SNAKE
            case "lower_camel":
                return AdaptixNameStyle.CAMEL
            case "upper_camel":
                return AdaptixNameStyle.PASCAL
            case "lower_kebab":
                return AdaptixNameStyle.LOWER_KEBAB
            case "upper_kebab":
                return AdaptixNameStyle.UPPER_KEBAB
            case _:
                return None

    def _get_name_mapping_provider(self) -> list[Provider]:
        providers: list[Provider] = []

        adaptix_name_style = self._get_adaptix_name_style()
        if adaptix_name_style is not None:
            providers.append(name_mapping(name_style=adaptix_name_style))

        if self._field_mapping:
            providers.append(name_mapping(map=self._field_mapping))

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
        return self._retort.load(data, dataclass_)

    def load(self, path: Path, dataclass_: type[T]) -> T:
        data = self._load(path)
        pre_processed_data = self._pre_processing(data)
        return self._transform_to_dataclass(pre_processed_data, dataclass_)
