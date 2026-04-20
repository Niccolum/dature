"""Error format — custom validator on a dataclass-typed field."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import dature

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Endpoint:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class NonEmptyHost:
    error_message: str = "Endpoint host must not be empty"

    def get_validator_func(self) -> Callable[[Endpoint], bool]:
        def validate(value: Endpoint) -> bool:
            return bool(value.host)

        return validate

    def get_error_message(self) -> str:
        return self.error_message


@dataclass
class Config:
    endpoint: Annotated[Endpoint, NonEmptyHost()]


dature.load(
    dature.Yaml12Source(file=SOURCES_DIR / "error_format_dataclass.yaml"),
    schema=Config,
)
