import pytest

from dature.errors import CaretSpan
from dature.sources.presentation import find_key_in_line


class TestFindKeyInLine:
    @pytest.mark.parametrize(
        ("line", "key", "expected"),
        [
            ('  "db_host": "x"', "db_host", CaretSpan(start=3, end=10)),
            ('  "dbHost": "x"', "db_host", CaretSpan(start=3, end=9)),
            ("db-host: x", "dbHost", CaretSpan(start=0, end=7)),
            ("DB_HOST=x", "db_host", CaretSpan(start=0, end=7)),
            ("DBHost = 1", "db_host", CaretSpan(start=0, end=6)),
            ("APP_DB_HOST_TYPO=<REDACTED>", "db_host_typo", CaretSpan(start=4, end=16)),
            ("APP_DB__HOSTT=1", "hostt", CaretSpan(start=8, end=13)),
            ('{"hostname": "h", "host": 1}', "host", CaretSpan(start=19, end=23)),
            ('{"name": "host"}', "host", None),
            ('hostt = "<REDACTED>"', "hostt", CaretSpan(start=0, end=5)),
            ("hostt: <REDACTED>", "hostt", CaretSpan(start=0, end=5)),
            ("[app]", "app", None),
            ("", "host", None),
            ("   ", "host", None),
        ],
        ids=[
            "json-quoted-snake",
            "json-quoted-camel-to-snake",
            "ini-kebab-to-camel",
            "env-screaming-snake-to-snake",
            "toml-pascal-to-snake",
            "env-prefixed-typo",
            "env-prefixed-double-separator",
            "substring-guard",
            "value-guard",
            "ini-plain",
            "yaml-plain",
            "section-header",
            "empty-line",
            "blank-line",
        ],
    )
    def test_find_key_in_line(self, line: str, key: str, expected: "CaretSpan | None"):
        assert find_key_in_line(line, key) == expected
