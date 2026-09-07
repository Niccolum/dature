import os

os.environ.clear()
os.environ.update(
    {
        "APP_HOST": "localhost",
        "APP_PORT": "8080",
        "LANG": "C",
        "TZ": "UTC",
        "SHELL": "/bin/sh",
        "TERM": "dumb",
        "USER": "demo",
        "PWD": "/app",
    }
)

# --8<-- [start:example]
from dataclasses import dataclass

import dature


@dataclass
class Config:
    host: str
    port: int


config = dature.load(
    dature.EnvSource(prefix="APP_"),
    schema=Config,
    strict="error",
)

assert config.host == "localhost"
assert config.port == 8080
# --8<-- [end:example]

print("loaded silently")
