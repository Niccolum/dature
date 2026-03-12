"""dature.load() with DockerSecretsLoader — load config from a directory of secret files."""

from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, load
from dature.sources_loader.docker_secrets import DockerSecretsLoader

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class DbConfig:
    host: str
    port: int


@dataclass
class AppConfig:
    name: str
    debug: bool
    db: DbConfig


secrets_dir = SOURCES_DIR / "app_secrets"
secrets_dir.mkdir(exist_ok=True)
(secrets_dir / "name").write_text("MyApp")
(secrets_dir / "debug").write_text("true")
(secrets_dir / "db__host").write_text("localhost")
(secrets_dir / "db__port").write_text("5432")

config = load(
    LoadMetadata(file_=secrets_dir, loader=DockerSecretsLoader),
    AppConfig,
)

assert config.name == "MyApp"
assert config.debug is True
assert config.db.host == "localhost"
assert config.db.port == 5432
