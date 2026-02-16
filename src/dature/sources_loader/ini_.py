import configparser
from datetime import date, datetime, time
from pathlib import Path
from typing import cast

from adaptix import loader
from adaptix.provider import Provider

from dature.sources_loader.base import ILoader
from dature.sources_loader.loaders import (
    bool_from_string,
    bytearray_from_json_string,
    date_from_string,
    datetime_from_string,
    dict_from_json_string,
    frozenset_from_json_string,
    list_from_json_string,
    none_from_empty_string,
    optional_from_empty_string,
    set_from_json_string,
    time_from_string,
    tuple_from_json_string,
)
from dature.types import JSONValue


class IniLoader(ILoader):
    def _additional_loaders(self) -> list[Provider]:
        return [
            loader(date, date_from_string),
            loader(datetime, datetime_from_string),
            loader(time, time_from_string),
            loader(bytearray, bytearray_from_json_string),
            loader(type(None), none_from_empty_string),
            loader(str | None, optional_from_empty_string),
            loader(bool, bool_from_string),
            loader(dict, dict_from_json_string),
            loader(list, list_from_json_string),
            loader(tuple, tuple_from_json_string),
            loader(set, set_from_json_string),
            loader(frozenset, frozenset_from_json_string),
        ]

    def _load(self, path: Path) -> JSONValue:
        config = configparser.ConfigParser(interpolation=None)
        with path.open() as f:
            config.read_file(f)
        if self._prefix and self._prefix in config:
            result: dict[str, JSONValue] = dict(config[self._prefix])
            child_prefix = self._prefix + "."
            for section in config.sections():
                if section.startswith(child_prefix):
                    nested_key = section[len(child_prefix) :]
                    result[nested_key] = dict(config[section])
            return {self._prefix: result}

        all_sections: dict[str, JSONValue] = {}
        if config.defaults():
            all_sections["DEFAULT"] = dict(config.defaults())
        for section in config.sections():
            parts = section.split(".")
            target = all_sections
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = cast("dict[str, JSONValue]", target[part])
            target[parts[-1]] = dict(config[section])
        return all_sections
