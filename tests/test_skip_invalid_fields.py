"""Tests for skip_if_invalid / skip_invalid_fields feature."""

import logging
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest
from adaptix import Retort

from dature import F, LoadMetadata, MergeMetadata, MergeStrategy, load
from dature.errors import DatureConfigError
from dature.skip_field_provider import (
    ModelToDictProvider,
    SkipFieldProvider,
    filter_invalid_fields,
)


class TestMergeSkipInvalidFields:
    def test_fallback_to_other_source(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1)),
                    LoadMetadata(file_=str(source2)),
                ),
                skip_invalid_fields=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080

    def test_all_sources_invalid_with_default(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": "def"}')

        @dataclass
        class Config:
            host: str
            port: int = 9090

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1)),
                    LoadMetadata(file_=str(source2)),
                ),
                skip_invalid_fields=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 9090

    def test_all_sources_invalid_no_default_raises(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": "def"}')

        @dataclass
        class Config:
            host: str
            port: int

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=str(source1)),
                        LoadMetadata(file_=str(source2)),
                    ),
                    skip_invalid_fields=True,
                ),
                Config,
            )

        err = exc_info.value
        assert len(err.exceptions) == 1
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [port]  Missing required field (invalid in: json '{source1}', json '{source2}')
               └── FILE '{source2}', line 1
                   {{"port": "def"}}
            """)

    def test_nested_dataclass(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"db": {"host": "s1-host", "port": "abc"}}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"db": {"host": "s2-host", "port": 5432}}')

        @dataclass
        class Database:
            host: str
            port: int

        @dataclass
        class Config:
            db: Database

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1)),
                    LoadMetadata(file_=str(source2)),
                ),
                skip_invalid_fields=True,
            ),
            Config,
        )

        assert result.db.host == "s2-host"
        assert result.db.port == 5432

    def test_per_source_override(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1), skip_if_invalid=True),
                    LoadMetadata(file_=str(source2)),
                ),
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080

    def test_global_flag(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1)),
                    LoadMetadata(file_=str(source2)),
                ),
                skip_invalid_fields=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080

    def test_backward_compat_no_skip(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        @dataclass
        class Config:
            host: str
            port: int

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(
                    sources=(LoadMetadata(file_=str(source1)),),
                ),
                Config,
            )

        err = exc_info.value
        assert len(err.exceptions) == 1
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [port]  Bad string format
               └── FILE '{source1}', line 1
                   {{"host": "localhost", "port": "abc"}}
            """)

    def test_raise_on_conflict_with_skip(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"host": "localhost", "port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(file_=str(source1)),
                    LoadMetadata(file_=str(source2)),
                ),
                strategy=MergeStrategy.RAISE_ON_CONFLICT,
                skip_invalid_fields=True,
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080

    def test_skip_specific_fields_only(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc", "timeout": "bad"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int
            timeout: int = 30

        result = load(
            MergeMetadata(
                sources=(
                    LoadMetadata(
                        file_=str(source1),
                        skip_if_invalid=(F[Config].port, F[Config].timeout),
                    ),
                    LoadMetadata(file_=str(source2)),
                ),
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080
        assert result.timeout == 30

    def test_skip_specific_fields_non_listed_field_raises(self, tmp_path: Path):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": 123, "port": "abc"}')

        @dataclass
        class Config:
            host: str
            port: int

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(
                            file_=str(source1),
                            skip_if_invalid=(F[Config].port,),
                        ),
                    ),
                ),
                Config,
            )

        err = exc_info.value
        assert len(err.exceptions) == 1
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [port]  Missing required field (invalid in: json '{source1}')
               └── FILE '{source1}', line 1
                   {{"host": 123, "port": "abc"}}
            """)

    def test_log_warnings(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        source1 = tmp_path / "s1.json"
        source1.write_text('{"host": "localhost", "port": "abc"}')

        source2 = tmp_path / "s2.json"
        source2.write_text('{"port": 8080}')

        @dataclass
        class Config:
            host: str
            port: int

        with caplog.at_level(logging.WARNING, logger="dature"):
            load(
                MergeMetadata(
                    sources=(
                        LoadMetadata(file_=str(source1)),
                        LoadMetadata(file_=str(source2)),
                    ),
                    skip_invalid_fields=True,
                ),
                Config,
            )

        warning_messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages == [
            "[Config] Source 0: Skipped invalid field 'port'",
            "[Config] Source 1: Skipped invalid field 'host'",
        ]


class TestSingleSourceSkipInvalidFields:
    def test_skip_with_default(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"host": "localhost", "port": "abc"}')

        @dataclass
        class Config:
            host: str
            port: int = 8080

        result = load(
            LoadMetadata(file_=str(json_file), skip_if_invalid=True),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 8080

    def test_skip_without_default_raises(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"host": "localhost", "port": "abc"}')

        @dataclass
        class Config:
            host: str
            port: int

        with pytest.raises(DatureConfigError) as exc_info:
            load(
                LoadMetadata(file_=str(json_file), skip_if_invalid=True),
                Config,
            )

        err = exc_info.value
        assert len(err.exceptions) == 1
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [port]  Missing required field (invalid in: json '{json_file}')
               └── FILE '{json_file}', line 1
                   {{"host": "localhost", "port": "abc"}}
            """)

    def test_single_source_decorator_skip(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"host": "localhost", "port": "abc"}')

        @load(LoadMetadata(file_=str(json_file), skip_if_invalid=True))
        @dataclass
        class Config:
            host: str
            port: int = 8080

        cfg = Config()
        assert cfg.host == "localhost"
        assert cfg.port == 8080

    def test_single_source_specific_fields(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"host": "localhost", "port": "abc", "timeout": 60}')

        @dataclass
        class Config:
            host: str
            port: int = 9090
            timeout: int = 30

        result = load(
            LoadMetadata(
                file_=str(json_file),
                skip_if_invalid=(F[Config].port,),
            ),
            Config,
        )

        assert result.host == "localhost"
        assert result.port == 9090
        assert result.timeout == 60

    def test_single_source_log_warnings(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"host": "localhost", "port": "abc"}')

        @dataclass
        class Config:
            host: str
            port: int = 8080

        with caplog.at_level(logging.WARNING, logger="dature"):
            load(
                LoadMetadata(file_=str(json_file), skip_if_invalid=True),
                Config,
            )

        warning_messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_messages == ["[Config] Skipped invalid field 'port'"]


class TestFilterInvalidFields:
    def test_all_fields_valid(self):
        @dataclass
        class Config:
            host: str
            port: int

        probe = Retort(
            strict_coercion=False,
            recipe=[SkipFieldProvider(), ModelToDictProvider()],
        )
        raw = {"host": "localhost", "port": 8080}
        result = filter_invalid_fields(raw, probe, Config, None)

        assert result.cleaned_dict == {"host": "localhost", "port": 8080}
        assert result.skipped_paths == []

    def test_one_field_invalid(self):
        @dataclass
        class Config:
            host: str
            port: int

        probe = Retort(
            strict_coercion=False,
            recipe=[SkipFieldProvider(), ModelToDictProvider()],
        )
        raw = {"host": "localhost", "port": "abc"}
        result = filter_invalid_fields(raw, probe, Config, None)

        assert result.cleaned_dict == {"host": "localhost"}
        assert result.skipped_paths == ["port"]

    def test_nested_field_invalid(self):
        @dataclass
        class Database:
            host: str
            port: int

        @dataclass
        class Config:
            db: Database

        probe = Retort(
            strict_coercion=False,
            recipe=[SkipFieldProvider(), ModelToDictProvider()],
        )
        raw = {"db": {"host": "localhost", "port": "abc"}}
        result = filter_invalid_fields(raw, probe, Config, None)

        assert result.cleaned_dict == {"db": {"host": "localhost"}}
        assert result.skipped_paths == ["db.port"]

    def test_allowed_fields_restricts_skip(self):
        @dataclass
        class Config:
            host: str
            port: int
            timeout: int

        probe = Retort(
            strict_coercion=False,
            recipe=[SkipFieldProvider(), ModelToDictProvider()],
        )
        raw = {"host": "localhost", "port": "abc", "timeout": "bad"}
        result = filter_invalid_fields(raw, probe, Config, {"port"})

        assert result.cleaned_dict == {"host": "localhost", "timeout": "bad"}
        assert result.skipped_paths == ["port"]

    def test_non_dict_input(self):
        @dataclass
        class Config:
            host: str

        probe = Retort(
            strict_coercion=False,
            recipe=[SkipFieldProvider(), ModelToDictProvider()],
        )
        result = filter_invalid_fields("not a dict", probe, Config, None)

        assert result.cleaned_dict == "not a dict"
        assert result.skipped_paths == []
