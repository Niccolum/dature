"""Error format — YAML source."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import dature
from dature.validators.number import Ge

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Config:
    port: Annotated[int, Ge(1)]


dature.load(
    dature.Yaml12Source(file=SOURCES_DIR / "error_format_config.yaml"),
    schema=Config,
)
