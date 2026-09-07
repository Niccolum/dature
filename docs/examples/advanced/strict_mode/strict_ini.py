from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str


dature.load(
    dature.IniSource(file=SOURCES_DIR / "strict_ini.ini", prefix="app"),
    schema=Config,
    strict="error",
)
# --8<-- [end:example]
