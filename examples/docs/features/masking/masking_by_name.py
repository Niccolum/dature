"""Masking by name — auto-detect secrets by field name patterns."""

from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, load

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Config:
    api_key: str
    password: str
    host: str
    card_number: str
    metadata: str


config = load(
    LoadMetadata(file_=SOURCES_DIR / "masking_secrets.yaml", mask_secrets=True),
    Config,
    debug=True,
)

assert config.host == "api.example.com"
assert config.password == "**********"
assert config.api_key == "**********"
assert config.card_number == "4111111111111111"
assert config.metadata == "aK9$mP2xL5vQ8wR3nJ7yB4zT6"
