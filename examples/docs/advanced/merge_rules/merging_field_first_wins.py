"""Per-field merge — FIRST_WINS keeps tags from the first source."""

from dataclasses import dataclass
from pathlib import Path

import dature

SOURCES_DIR = Path(__file__).parent / "sources"


@dataclass
class Config:
    tags: list[str]


config = dature.load(
    dature.Merge(
        dature.Source(file=SOURCES_DIR / "merging_field_base.yaml"),
        dature.Source(file=SOURCES_DIR / "merging_field_override.yaml"),
        field_merges=(dature.MergeRule(dature.F[Config].tags, dature.FieldMergeStrategy.FIRST_WINS),),
    ),
    Config,
)

assert config.tags == ["web", "default"]
assert config.tags == ["web", "default"]
