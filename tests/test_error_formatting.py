from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest
from adaptix import Retort
from adaptix.load_error import AggregateLoadError, LoadError

from dature import LoadMetadata, load
from dature.error_formatter import ErrorContext, extract_field_errors, resolve_source_location
from dature.errors import DatureConfigError, FieldError, FieldErrorInfo, SourceLocation


class TestExtractFieldErrors:
    def test_type_error(self):
        @dataclass
        class Config:
            timeout: int

        r = Retort(strict_coercion=False)
        try:
            r.load({"timeout": "abc"}, Config)
        except (AggregateLoadError, LoadError) as exc:
            errors = extract_field_errors(exc)
            assert len(errors) == 1
            assert errors[0].field_path == ["timeout"]
            assert errors[0].message == "Bad string format"

    def test_missing_field(self):
        @dataclass
        class Config:
            timeout: int
            name: str

        r = Retort(strict_coercion=False)
        try:
            r.load({"timeout": 123}, Config)
        except (AggregateLoadError, LoadError) as exc:
            errors = extract_field_errors(exc)
            assert len(errors) == 1
            assert errors[0].field_path == ["name"]
            assert errors[0].message == "Missing required field"

    def test_nested_errors(self):
        @dataclass
        class DB:
            host: str
            port: int

        @dataclass
        class Config:
            timeout: int
            db: DB

        r = Retort(strict_coercion=False)
        try:
            r.load({"timeout": "abc", "db": {"host": "ok", "port": "xyz"}}, Config)
        except (AggregateLoadError, LoadError) as exc:
            errors = extract_field_errors(exc)
            assert len(errors) == 2
            paths = [e.field_path for e in errors]
            assert ["timeout"] in paths
            assert ["db", "port"] in paths

    def test_multiple_missing_fields(self):
        @dataclass
        class Config:
            a: int
            b: str
            c: float

        r = Retort(strict_coercion=False)
        try:
            r.load({}, Config)
        except (AggregateLoadError, LoadError) as exc:
            errors = extract_field_errors(exc)
            assert len(errors) == 3
            paths = sorted([e.field_path[0] for e in errors])
            assert paths == ["a", "b", "c"]


class TestResolveSourceLocation:
    def test_env_source(self):
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="env",
            file_path=None,
            prefix="APP_",
            split_symbols="__",
        )
        loc = resolve_source_location(["database", "port"], ctx, file_content=None)
        assert loc.source_type == "env"
        assert loc.env_var_name == "APP_DATABASE__PORT"
        assert loc.file_path is None

    def test_env_source_no_prefix(self):
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="env",
            file_path=None,
            prefix=None,
            split_symbols="__",
        )
        loc = resolve_source_location(["timeout"], ctx, file_content=None)
        assert loc.env_var_name == "TIMEOUT"

    def test_env_source_custom_split_symbols(self):
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="env",
            file_path=None,
            prefix="APP_",
            split_symbols="_",
        )
        loc = resolve_source_location(["database", "port"], ctx, file_content=None)
        assert loc.env_var_name == "APP_DATABASE_PORT"

    def test_json_source_with_line(self):
        content = '{\n  "timeout": "30",\n  "name": "test"\n}'
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="json",
            file_path=Path("config.json"),
            prefix=None,
            split_symbols="__",
        )
        loc = resolve_source_location(["timeout"], ctx, file_content=content)
        assert loc.source_type == "json"
        assert loc.line_number == 2
        assert loc.line_content == '"timeout": "30",'

    def test_toml_source_with_line(self):
        content = 'timeout = "30"\nname = "test"'
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="toml",
            file_path=Path("config.toml"),
            prefix=None,
            split_symbols="__",
        )
        loc = resolve_source_location(["timeout"], ctx, file_content=content)
        assert loc.source_type == "toml"
        assert loc.line_number == 1
        assert loc.line_content == 'timeout = "30"'

    def test_envfile_source(self):
        content = "# comment\nAPP_TIMEOUT=30\nAPP_NAME=test"
        ctx = ErrorContext(
            dataclass_name="Config",
            loader_type="envfile",
            file_path=Path(".env"),
            prefix="APP_",
            split_symbols="__",
        )
        loc = resolve_source_location(["timeout"], ctx, file_content=content)
        assert loc.source_type == "envfile"
        assert loc.env_var_name == "APP_TIMEOUT"
        assert loc.line_number == 2
        assert loc.line_content == "APP_TIMEOUT=30"


class TestDatureConfigErrorFormat:
    def test_single_error_message(self):
        errors = [
            FieldError(
                error=FieldErrorInfo(
                    field_path=["timeout"],
                    message="Expected int, got str",
                    input_value="30",
                ),
                location=SourceLocation(
                    source_type="toml",
                    file_path=Path("config.toml"),
                    line_number=2,
                    line_content='timeout = "30"',
                    env_var_name=None,
                ),
            ),
        ]
        exc = DatureConfigError(errors, "Config")
        assert str(exc) == dedent("""\
            Config loading errors (1)

              [timeout]  Expected int, got str
               └── FILE 'config.toml', line 2
                   timeout = "30"
            """)

    def test_multiple_errors_message(self):
        errors = [
            FieldError(
                error=FieldErrorInfo(
                    field_path=["timeout"],
                    message="Bad string format",
                    input_value="abc",
                ),
                location=SourceLocation(
                    source_type="json",
                    file_path=Path("config.json"),
                    line_number=2,
                    line_content='"timeout": "abc"',
                    env_var_name=None,
                ),
            ),
            FieldError(
                error=FieldErrorInfo(
                    field_path=["db", "port"],
                    message="Missing required field",
                    input_value=None,
                ),
                location=SourceLocation(
                    source_type="json",
                    file_path=Path("config.json"),
                    line_number=None,
                    line_content=None,
                    env_var_name=None,
                ),
            ),
        ]
        exc = DatureConfigError(errors, "Config")
        assert str(exc) == dedent("""\
            Config loading errors (2)

              [timeout]  Bad string format
               └── FILE 'config.json', line 2
                   "timeout": "abc"

              [db.port]  Missing required field
               └── FILE 'config.json'
            """)

    def test_env_error_message(self):
        errors = [
            FieldError(
                error=FieldErrorInfo(
                    field_path=["database", "port"],
                    message="Bad string format",
                    input_value="abc",
                ),
                location=SourceLocation(
                    source_type="env",
                    file_path=None,
                    line_number=None,
                    line_content=None,
                    env_var_name="APP_DATABASE__PORT",
                ),
            ),
        ]
        exc = DatureConfigError(errors, "Config")
        assert str(exc) == dedent("""\
            Config loading errors (1)

              [database.port]  Bad string format
               └── ENV 'APP_DATABASE__PORT'
            """)


class TestLoadIntegrationErrors:
    def test_json_type_error_decorator(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"timeout": "abc", "name": "test"}')

        metadata = LoadMetadata(file_=str(json_file))

        @load(metadata)
        @dataclass
        class Config:
            timeout: int
            name: str

        with pytest.raises(DatureConfigError) as exc_info:
            Config()

        err = exc_info.value
        assert len(err.errors) == 1
        assert err.errors[0].error.field_path == ["timeout"]
        assert str(json_file) in str(err)

    def test_json_missing_field_function(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        @dataclass
        class Config:
            name: str
            port: int

        metadata = LoadMetadata(file_=str(json_file))

        with pytest.raises(DatureConfigError) as exc_info:
            load(metadata, Config)

        err = exc_info.value
        assert len(err.errors) == 1
        assert err.errors[0].error.field_path == ["port"]
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [port]  Missing required field
               └── FILE '{json_file}'
            """)

    def test_multiple_errors_at_once(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"timeout": "abc"}')

        @dataclass
        class Config:
            timeout: int
            name: str

        metadata = LoadMetadata(file_=str(json_file))

        with pytest.raises(DatureConfigError) as exc_info:
            load(metadata, Config)

        err = exc_info.value
        assert len(err.errors) == 2
        paths = [e.error.field_path for e in err.errors]
        assert ["timeout"] in paths
        assert ["name"] in paths
        assert "Config loading errors (2)" in str(err)

    def test_nested_dataclass_error(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{\n  "db": {\n    "host": "localhost",\n    "port": "abc"\n  }\n}')

        @dataclass
        class DB:
            host: str
            port: int

        @dataclass
        class Config:
            db: DB

        metadata = LoadMetadata(file_=str(json_file))

        with pytest.raises(DatureConfigError) as exc_info:
            load(metadata, Config)

        err = exc_info.value
        assert len(err.errors) == 1
        assert err.errors[0].error.field_path == ["db", "port"]
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [db.port]  Bad string format
               └── FILE '{json_file}', line 4
                   "port": "abc"
            """)

    def test_env_type_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_TIMEOUT", "abc")
        monkeypatch.setenv("APP_NAME", "test")

        metadata = LoadMetadata(prefix="APP_")

        @load(metadata)
        @dataclass
        class Config:
            timeout: int
            name: str

        with pytest.raises(DatureConfigError) as exc_info:
            Config()

        err = exc_info.value
        assert len(err.errors) == 1
        assert str(err) == dedent("""\
            Config loading errors (1)

              [timeout]  Bad string format
               └── ENV 'APP_TIMEOUT'
            """)

    def test_toml_with_line_number(self, tmp_path: Path):
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('name = "test"\ntimeout = "abc"\n')

        @dataclass
        class Config:
            name: str
            timeout: int

        metadata = LoadMetadata(file_=str(toml_file))

        with pytest.raises(DatureConfigError) as exc_info:
            load(metadata, Config)

        err = exc_info.value
        assert len(err.errors) == 1
        assert err.errors[0].location is not None
        assert err.errors[0].location.line_number == 2
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [timeout]  Bad string format
               └── FILE '{toml_file}', line 2
                   timeout = "abc"
            """)

    def test_json_with_line_number(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{\n  "name": "test",\n  "timeout": "abc"\n}')

        @dataclass
        class Config:
            name: str
            timeout: int

        metadata = LoadMetadata(file_=str(json_file))

        with pytest.raises(DatureConfigError) as exc_info:
            load(metadata, Config)

        err = exc_info.value
        assert err.errors[0].location is not None
        assert err.errors[0].location.line_number == 3
        assert str(err) == dedent(f"""\
            Config loading errors (1)

              [timeout]  Bad string format
               └── FILE '{json_file}', line 3
                   "timeout": "abc"
            """)
