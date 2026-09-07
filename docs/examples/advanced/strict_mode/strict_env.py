import os

# A fixed, minimal environment keeps this example deterministic.
# A real shell easily has 30+ variables unrelated to the config.
os.environ.clear()
os.environ.update(
    {
        "HOST": "localhost",
        "PORT": "8080",
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


conf = dature.Dature(error_display={"max_errors": 3})

conf.load(
    dature.EnvSource(),
    schema=Config,
    strict="error",
)
# --8<-- [end:example]
