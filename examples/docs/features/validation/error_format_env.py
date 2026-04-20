"""Error format — ENV source."""

import os
from dataclasses import dataclass
from typing import Annotated

import dature
from dature.validators.number import Ge

os.environ["APP_PORT"] = "0"


@dataclass
class Config:
    port: Annotated[int, Ge(1)]


dature.load(
    dature.EnvSource(prefix="APP_"),
    schema=Config,
)
