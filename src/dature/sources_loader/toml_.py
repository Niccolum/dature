import tomllib
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, cast

from adaptix import loader
from adaptix.provider import Provider

from dature.path_finders.toml_ import TomlPathFinder
from dature.sources_loader.base import BaseLoader
from dature.sources_loader.loaders import (
    bytearray_from_string,
    date_passthrough,
    datetime_passthrough,
    none_from_empty_string,
    optional_from_empty_string,
    time_passthrough,
)
from dature.types import JSONValue


class TomlLoader(BaseLoader):
    display_name = "toml"
    path_finder_class = TomlPathFinder

    def _additional_loaders(self) -> list[Provider]:
        return [
            loader(date, date_passthrough),
            loader(datetime, datetime_passthrough),
            loader(time, time_passthrough),
            loader(bytearray, bytearray_from_string),
            loader(type(None), none_from_empty_string),
            loader(str | None, optional_from_empty_string),
            loader(Any, optional_from_empty_string),
        ]

    def _load(self, path: Path) -> JSONValue:
        with path.open("rb") as file_:
            return cast("JSONValue", tomllib.load(file_))
