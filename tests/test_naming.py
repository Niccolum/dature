import pytest

from dature.naming import canonical_name, segment_offsets


class TestCanonicalName:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("secret-key", "secretkey"),
            ("secret_key", "secretkey"),
            ("secretKey", "secretkey"),
            ("SecretKey", "secretkey"),
            ("SECRET_KEY", "secretkey"),
            ("SECRET-KEY", "secretkey"),
            ("db.secret-key", "db.secretkey"),
            ("", ""),
            ("host", "host"),
        ],
        ids=[
            "kebab",
            "snake",
            "lower-camel",
            "upper-camel",
            "upper-snake",
            "upper-kebab",
            "dotted-path",
            "empty",
            "unchanged",
        ],
    )
    def test_canonical_name(self, name: str, expected: str):
        assert canonical_name(name) == expected


class TestSegmentOffsets:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("APP_DB_HOST_TYPO", [0, 4, 7, 12]),
            ("APP_DB__HOSTT", [0, 4, 8]),
            ("dbHostTypo", [0, 2, 6]),
            ("db-host", [0, 3]),
            ("host", [0]),
            ("", [0]),
        ],
        ids=[
            "screaming-snake-prefixed",
            "double-separator-collapses",
            "camel-case",
            "kebab-case",
            "no-boundary",
            "empty",
        ],
    )
    def test_segment_offsets(self, name: str, expected: list[int]):
        assert segment_offsets(name) == expected
