from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str


dature.load(
    dature.EnvFileSource(file=SOURCES_DIR / "strict_env_file.env"),
    schema=Config,
    strict="error",
)
# --8<-- [end:example]
