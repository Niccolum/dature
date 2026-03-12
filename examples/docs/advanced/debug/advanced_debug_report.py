"""Debug report — get_load_report() to inspect which source provided each field."""

from dataclasses import dataclass
from pathlib import Path

from dature import LoadMetadata, MergeMetadata, get_load_report, load

SHARED_DIR = Path(__file__).parents[2] / "shared"


@dataclass
class Config:
    host: str
    port: int
    debug: bool
    workers: int
    tags: list[str]


config = load(
    MergeMetadata(
        sources=(
            LoadMetadata(file_=SHARED_DIR / "common_defaults.yaml"),
            LoadMetadata(file_=SHARED_DIR / "common_overrides.yaml"),
        ),
    ),
    Config,
    debug=True,
)

report = get_load_report(config)
assert report is not None

origins = report.field_origins
assert len(origins) == 5

assert origins[0].key == "debug"
assert origins[0].value is True
assert origins[0].source_index == 1
assert origins[0].source_file == str(SHARED_DIR / "common_overrides.yaml")

assert origins[1].key == "host"
assert origins[1].value == "production.example.com"
assert origins[1].source_index == 1
assert origins[1].source_file == str(SHARED_DIR / "common_overrides.yaml")

assert origins[2].key == "port"
assert origins[2].value == 8080
assert origins[2].source_index == 1
assert origins[2].source_file == str(SHARED_DIR / "common_overrides.yaml")

assert origins[3].key == "tags"
assert origins[3].value == ["web", "api"]
assert origins[3].source_index == 1
assert origins[3].source_file == str(SHARED_DIR / "common_overrides.yaml")

assert origins[4].key == "workers"
assert origins[4].value == 4
assert origins[4].source_index == 1
assert origins[4].source_file == str(SHARED_DIR / "common_overrides.yaml")
