import os
import re
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

_env_pattern: re.Pattern[str] = re.compile(r"\${(\w+)}")


def _env_var_constructor(loader_: yaml.SafeLoader, node: yaml.Node) -> str | int | float | bool | None:
    if not isinstance(node, yaml.ScalarNode):
        return None

    value = loader_.construct_scalar(node)
    if not isinstance(value, str):
        return value

    if not (match := _env_pattern.match(value)):
        return value

    env_var_name = match.group(1)
    return os.environ.get(env_var_name, value)


yaml.add_implicit_resolver("!ENV", _env_pattern, first="$", Loader=yaml.SafeLoader)
yaml.add_constructor("!ENV", _env_var_constructor, Loader=yaml.SafeLoader)


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
