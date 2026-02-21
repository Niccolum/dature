from datetime import date, datetime, time
from pathlib import Path
from typing import cast

import json5
from adaptix import loader
from adaptix.provider import Provider

from dature.path_finders.json5_ import Json5PathFinder
from dature.sources_loader.base import BaseLoader
from dature.sources_loader.loaders import (
    bytearray_from_string,
    date_from_string,
    datetime_from_string,
    time_from_string,
)
from dature.types import JSONValue


class Json5Loader(BaseLoader):
    display_name = "json5"
    path_finder_class = Json5PathFinder

    def _additional_loaders(self) -> list[Provider]:
        return [
            loader(date, date_from_string),
            loader(datetime, datetime_from_string),
            loader(time, time_from_string),
            loader(bytearray, bytearray_from_string),
        ]

    def _load(self, path: Path) -> JSONValue:
        with path.open() as file_:
            return cast("JSONValue", json5.load(file_))
