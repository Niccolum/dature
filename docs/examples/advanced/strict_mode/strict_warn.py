import io
import logging
from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.WARNING)
logging.getLogger("dature").addHandler(handler)
logging.getLogger("dature").setLevel(logging.WARNING)

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str


config = dature.load(
    dature.JsonSource(file=SOURCES_DIR / "strict_json.json"),
    schema=Config,
    strict="warn",
)

assert config.host == "localhost"
# --8<-- [end:example]

print(log_stream.getvalue().strip())
