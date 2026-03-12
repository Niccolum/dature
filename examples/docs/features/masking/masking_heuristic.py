"""Heuristic masking — detect random tokens by string entropy."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, load

log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.DEBUG)
logging.getLogger("dature").addHandler(handler)
logging.getLogger("dature").setLevel(logging.DEBUG)

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Config:
    token: str
    host: str


config = load(
    LoadMetadata(file_=SOURCES_DIR / "masking_heuristic.yaml", mask_secrets=True),
    Config,
    debug=True,
)

assert config.host == "production"
assert config.token == "aK9$mP2xL5vQ8wR3nJ7yB4zT6"

logs = log_stream.getvalue()
assert "'token': 'aK*****T6'" in logs
assert "'host': 'production'" in logs
