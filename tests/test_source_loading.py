"""Tests for source loading — skip broken sources, empty sources."""

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest

from dature import LoadMetadata, MergeMetadata, load
from dature.errors import DatureConfigError


class TestSkipBrokenSources:
    def test_skip_missing_file(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost", "port": 3000}')

        missing = str(tmp_path / "does_not_exist.json")

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(valid)),
                    LoadMetadata(file_=missing),
                ),
                skip_broken_sources=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 3000

    def test_skip_broken_json(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost", "port": 3000}')

        broken = tmp_path / "broken.json"
        broken.write_text("{invalid json")

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(valid)),
                    LoadMetadata(file_=str(broken)),
                ),
                skip_broken_sources=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 3000

    def test_all_sources_broken_raises(self, tmp_path: Path):
        broken_a = tmp_path / "a.json"
        broken_a.write_text("{bad")

        broken_b = tmp_path / "b.json"
        broken_b.write_text("{bad")

        @dataclass
        class Config:
            host: str

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=str(broken_a)),
                        LoadMetadata(file_=str(broken_b)),
                    ),
                    skip_broken_sources=True,
                ),
                Config,
            )

        assert str(exc_info.value) == dedent("""\
            Config loading errors (1)

              [<root>]  All 2 source(s) failed to load
            """)

    def test_broken_source_without_flag_raises(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost"}')

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        @dataclass
        class Config:
            host: str

        with pytest.raises(DatureConfigError):
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=str(valid)),
                        LoadMetadata(file_=str(broken)),
                    ),
                ),
                Config,
            )

    def test_skip_middle_source(self, tmp_path: Path):
        a = tmp_path / "a.json"
        a.write_text('{"host": "a-host", "port": 1000}')

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        c = tmp_path / "c.json"
        c.write_text('{"port": 2000}')

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(a)),
                    LoadMetadata(file_=str(broken)),
                    LoadMetadata(file_=str(c)),
                ),
                skip_broken_sources=True,
            ),
            Config,
        )

        assert result.host == "a-host"
        assert result.port == 2000

    def test_per_source_override_skip(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost", "port": 3000}')

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(valid)),
                    LoadMetadata(file_=str(broken), skip_if_broken=True),
                ),
                skip_broken_sources=False,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 3000

    def test_per_source_override_no_skip(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost", "port": 3000}')

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        @dataclass
        class Config:
            host: str
            port: int

        with pytest.raises(DatureConfigError):
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=str(valid)),
                        LoadMetadata(file_=str(broken), skip_if_broken=False),
                    ),
                    skip_broken_sources=True,
                ),
                Config,
            )

    def test_per_source_none_uses_global(self, tmp_path: Path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"host": "localhost", "port": 3000}')

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(valid)),
                    LoadMetadata(file_=str(broken), skip_if_broken=None),
                ),
                skip_broken_sources=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 3000

    def test_empty_sources_raises(self):
        @dataclass
        class Config:
            host: str

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(sources=()),
                Config,
            )

        assert str(exc_info.value) == dedent("""\
            Config loading errors (1)

              [<root>]  MergeMetadata.sources must not be empty
            """)

    def test_all_sources_broken_mixed_errors(self, tmp_path: Path):
        missing = str(tmp_path / "does_not_exist.json")

        broken = tmp_path / "broken.json"
        broken.write_text("{bad")

        @dataclass
        class Config:
            host: str

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=missing),
                        LoadMetadata(file_=str(broken)),
                    ),
                    skip_broken_sources=True,
                ),
                Config,
            )

        assert str(exc_info.value) == dedent("""\
            Config loading errors (1)

              [<root>]  All 2 source(s) failed to load
            """)
