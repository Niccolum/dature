"""Caching — decorator mode with cache enabled/disabled."""

import os
from dataclasses import dataclass

import dature

os.environ["CACHE_HOST"] = "localhost"
os.environ["CACHE_PORT"] = "6379"


@dature.load(dature.Source(prefix="CACHE_"), cache=True)
@dataclass
class CachedConfig:
    host: str
    port: int


config1 = CachedConfig()
os.environ["CACHE_PORT"] = "9999"
config2 = CachedConfig()
assert config1.port == 6379
assert config2.port == 6379

os.environ["NOCACHE_HOST"] = "localhost"
os.environ["NOCACHE_PORT"] = "6379"


@dature.load(dature.Source(prefix="NOCACHE_"), cache=False)
@dataclass
class UncachedConfig:
    host: str
    port: int


config3 = UncachedConfig()
os.environ["NOCACHE_PORT"] = "9999"
config4 = UncachedConfig()
assert config3.port == 6379
assert config4.port == 9999
