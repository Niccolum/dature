from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str


dature.load(
    dature.Toml10Source(file=SOURCES_DIR / "strict_toml.toml"),
    schema=Config,
    strict="error",
)
# --8<-- [end:example]
