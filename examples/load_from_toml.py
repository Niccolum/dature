"""Merge multiple sources — tuple-shorthand, LAST_WINS strategy."""

from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, load

SOURCES_DIR = Path(__file__).parent / "sources"

DEFAULTS = LoadMetadata(file_=SOURCES_DIR / "defaults.toml")
OVERRIDES = LoadMetadata(file_=SOURCES_DIR / "overrides.toml")


@dataclass
class Config:
    host: str
    port: int
    debug: bool
    workers: int
    tags: list[str]


config = load((DEFAULTS, OVERRIDES), Config)

assert config.host == "0.0.0.0"
assert config.port == 8080
assert config.debug is True
assert config.workers == 4
assert config.tags == ["web", "api"]
