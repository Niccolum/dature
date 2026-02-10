from datetime import date, datetime, time
from pathlib import Path
from typing import cast

import yaml
from adaptix import loader
from adaptix.provider import Provider

from dature.sources_loader.base import ILoader
from dature.sources_loader.loaders import (
    bytearray_from_string,
    date_passthrough,
    datetime_passthrough,
    time_from_int,
    time_from_string,
)
from dature.types import JSONValue


class YamlLoader(ILoader):
    def _additional_loaders(self) -> list[Provider]:
        return [
            loader(date, date_passthrough),
            loader(datetime, datetime_passthrough),
            loader(time, time_from_string),
            loader(time, time_from_int),
            loader(bytearray, bytearray_from_string),
        ]

    def _load(self, path: Path) -> JSONValue:
        with path.open() as file_:
            return cast("JSONValue", yaml.safe_load(file_))
