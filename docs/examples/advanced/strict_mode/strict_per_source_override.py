import os
from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

# A fixed, minimal environment keeps this example deterministic.
os.environ.clear()
os.environ.update({"APP_HOST": "localhost", "APP_TYPO": "irrelevant"})

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str


dature.load(
    dature.JsonSource(file=SOURCES_DIR / "strict_json.json", strict="error"),
    dature.EnvSource(prefix="APP_"),  # not checked — strict is unset, so it
    # falls back to load()'s "off" default
    schema=Config,
)
# --8<-- [end:example]
