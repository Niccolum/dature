import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, cast

from adaptix import loader
from adaptix.provider import Provider

from dature.env_expand import expand_env_vars
from dature.protocols import ValidatorProtocol
from dature.sources_loader.base import ILoader
from dature.sources_loader.loaders import (
    bool_loader,
    bytearray_from_json_string,
    date_from_string,
    datetime_from_string,
    none_from_empty_string,
    optional_from_empty_string,
    time_from_string,
)
from dature.types import DotSeparatedPath, ExpandEnvVarsMode, FieldMapping, JSONValue, NameStyle


def _set_nested(d: dict[Any, Any], keys: list[str], value: str) -> None:
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


class EnvLoader(ILoader):
    def __init__(
        self,
        *,
        prefix: DotSeparatedPath | None = None,
        split_symbols: str = "__",
        name_style: NameStyle | None = None,
        field_mapping: FieldMapping | None = None,
        root_validators: tuple[ValidatorProtocol, ...] | None = None,
        expand_env_vars: ExpandEnvVarsMode = "default",
    ) -> None:
        self._split_symbols = split_symbols
        super().__init__(
            prefix=prefix,
            name_style=name_style,
            field_mapping=field_mapping,
            root_validators=root_validators,
            expand_env_vars=expand_env_vars,
        )

    def _additional_loaders(self) -> list[Provider]:
        return [
            loader(date, date_from_string),
            loader(datetime, datetime_from_string),
            loader(time, time_from_string),
            loader(bytearray, bytearray_from_json_string),
            loader(type(None), none_from_empty_string),
            loader(str | None, optional_from_empty_string),
            loader(bool, bool_loader),
        ]

    def _load(self, _: Path) -> JSONValue:
        return cast("JSONValue", os.environ)

    def _pre_processing(self, data: JSONValue) -> JSONValue:
        data_dict = cast("dict[str, str]", data)
        result: dict[str, JSONValue] = {}

        for key, value in data_dict.items():
            self._pre_processed_row(key=key, value=value, result=result)

        expanded = expand_env_vars(result, mode=self._expand_env_vars_mode)
        return self._parse_string_values(expanded)

    def _pre_processed_row(self, key: str, value: str, result: dict[str, JSONValue]) -> None:
        if self._prefix and not key.startswith(self._prefix):
            return

        processed_key = key[len(self._prefix) :] if self._prefix else key
        processed_key = processed_key.lower()

        parts = processed_key.split(self._split_symbols)
        if len(parts) > 1:
            _set_nested(result, parts, value)
        else:
            result[processed_key] = value


class EnvFileLoader(EnvLoader):
    def _load(self, path: Path) -> JSONValue:
        env_vars: dict[str, JSONValue] = {}

        with path.open() as file_:
            for raw_line in file_:
                if not (line := raw_line.strip()) or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                self._pre_processed_row(key=key, value=value, result=env_vars)

        return env_vars

    def _pre_processing(self, data: JSONValue) -> JSONValue:
        expanded = expand_env_vars(data, mode=self._expand_env_vars_mode)
        return self._parse_string_values(expanded)
