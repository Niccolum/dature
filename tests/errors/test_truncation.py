"""Unit and integration tests for dature.errors.truncation.raise_truncated."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from dature import JsonSource
from dature.config import ErrorDisplayConfig
from dature.errors import (
    CrossRefError,
    CrossRefExpandError,
    DatureConfigError,
    DatureErrorGroup,
    FieldGroupError,
    FieldGroupViolationError,
    FieldLoadError,
    MergeConflictError,
    MergeConflictFieldError,
    MissingEnvVarError,
    StrictModeError,
    UnknownKeyError,
)
from dature.errors.exceptions import EnvVarExpandError
from dature.errors.truncation import raise_truncated
from dature.instance import Dature
from dature.loading.field_pass import merge_root_and_field_errors


def _field_load_errors(n: int) -> list[FieldLoadError]:
    return [FieldLoadError(field_path=[f"field_{i}"], message="bad") for i in range(n)]


def _missing_env_var_errors(n: int) -> list[MissingEnvVarError]:
    return [MissingEnvVarError(var_name=f"VAR_{i}", position=0, source_text=f"${{VAR_{i}}}") for i in range(n)]


def _merge_conflict_field_errors(n: int) -> list[MergeConflictFieldError]:
    return [MergeConflictFieldError(field_path=[f"field_{i}"], message="conflict", locations=[]) for i in range(n)]


def _field_group_violation_errors(n: int) -> list[FieldGroupViolationError]:
    return [
        FieldGroupViolationError(
            group_fields=("a", "b"),
            changed_fields=("a",),
            unchanged_fields=("b",),
            changed_sources=("0",),
            unchanged_sources=("1",),
            source_index=i,
        )
        for i in range(n)
    ]


def _unknown_key_errors(n: int) -> list[UnknownKeyError]:
    return [UnknownKeyError(field_path=[f"typo_{i}"], source_repr="<src>") for i in range(n)]


def _cross_ref_errors(n: int) -> list[CrossRefError]:
    return [CrossRefError(ref=f"@tag.key_{i}", message="not found") for i in range(n)]


def _raise_and_capture[G: DatureErrorGroup](group: G, max_errors: int) -> G:
    with pytest.raises(type(group)) as exc_info:
        raise_truncated(group, ErrorDisplayConfig(max_errors=max_errors))
    return exc_info.value


class TestTruncateGroup:
    @pytest.mark.parametrize(
        ("factory", "leaves_factory", "expected_noun"),
        [
            pytest.param(
                lambda leaves: DatureConfigError("Config", leaves),
                _field_load_errors,
                "errors",
                id="DatureConfigError",
            ),
            pytest.param(
                lambda leaves: EnvVarExpandError("env errors", leaves),
                _missing_env_var_errors,
                "missing environment variables",
                id="EnvVarExpandError",
            ),
            pytest.param(
                lambda leaves: MergeConflictError("Config", leaves),
                _merge_conflict_field_errors,
                "merge conflicts",
                id="MergeConflictError",
            ),
            pytest.param(
                lambda leaves: FieldGroupError("Config", leaves),
                _field_group_violation_errors,
                "field group errors",
                id="FieldGroupError",
            ),
            pytest.param(
                lambda leaves: StrictModeError("Config", leaves),
                _unknown_key_errors,
                "unknown config keys",
                id="StrictModeError",
            ),
            pytest.param(
                lambda leaves: CrossRefExpandError("cross-ref errors", leaves),
                _cross_ref_errors,
                "cross-source reference errors",
                id="CrossRefExpandError",
            ),
        ],
    )
    def test_truncates_and_notes_domain_noun(self, factory, leaves_factory, expected_noun):
        leaves = leaves_factory(10)
        group = factory(leaves)

        truncated = _raise_and_capture(group, max_errors=3)

        assert len(truncated.exceptions) == 3
        assert truncated.__notes__ == [f"... and 7 more {expected_noun} (10 total)"]

    def test_returns_same_object_when_within_limit(self):
        group = DatureConfigError("Config", _field_load_errors(3))

        result = _raise_and_capture(group, max_errors=7)

        assert result is group

    def test_returns_same_object_when_exactly_at_limit(self):
        group = DatureConfigError("Config", _field_load_errors(7))

        result = _raise_and_capture(group, max_errors=7)

        assert result is group

    def test_preserves_existing_notes(self):
        group = DatureConfigError("Config", _field_load_errors(5))
        group.add_note("pre-existing note")

        truncated = _raise_and_capture(group, max_errors=2)

        assert truncated.__notes__ == [
            "pre-existing note",
            "... and 3 more errors (5 total)",
        ]

    def test_preserves_cause_chain(self):
        cause = ValueError("root cause")
        group = DatureConfigError("Config", _field_load_errors(5))
        group.__cause__ = cause

        truncated = _raise_and_capture(group, max_errors=2)

        assert truncated.__cause__ is cause

    def test_note_survives_subgroup_split(self):
        group = DatureConfigError("Config", _field_load_errors(5))

        truncated = _raise_and_capture(group, max_errors=2)
        subgroup = truncated.subgroup(FieldLoadError)

        assert subgroup is not None
        assert subgroup.__notes__ == truncated.__notes__

    def test_note_survives_except_star(self):
        group = DatureConfigError("Config", _field_load_errors(5))
        truncated = _raise_and_capture(group, max_errors=2)

        matched = None
        try:
            raise truncated
        except* FieldLoadError as eg:
            matched = eg

        assert matched is not None
        assert matched.__notes__ == truncated.__notes__

    def test_rebuild_via_merge_root_and_field_errors_keeps_true_total(self):
        """merge_root_and_field_errors rebuilds a fresh DatureConfigError from two lists of
        leaves, discarding whatever the original groups carried. Truncation must run after
        this rebuild (not before, on either input group) so the note's total reflects the
        combined leaf count, not a count computed before the merge."""
        root_errors = _field_load_errors(6)
        field_errors = [FieldLoadError(field_path=[f"other_{i}"], message="bad") for i in range(6)]

        combined = merge_root_and_field_errors("Config", root_errors, field_errors)
        truncated = _raise_and_capture(combined, max_errors=4)

        assert len(truncated.exceptions) == 4
        assert truncated.__notes__ == ["... and 8 more errors (12 total)"]


def _write_json(tmp_path: Path, content: str) -> Path:
    config_file = tmp_path / "config.json"
    config_file.write_text(content)
    return config_file


class TestTruncationIntegration:
    def test_validation_errors_truncated_at_load_boundary(self, tmp_path: Path):
        content = "{" + ", ".join(f'"field_{i}": "not-an-int"' for i in range(10)) + "}"
        config_file = _write_json(tmp_path, content)

        @dataclass
        class Config:
            field_0: int
            field_1: int
            field_2: int
            field_3: int
            field_4: int
            field_5: int
            field_6: int
            field_7: int
            field_8: int
            field_9: int

        conf = Dature(masking={"masking_mode": "none"}, error_display={"max_errors": 3})

        with pytest.raises(DatureConfigError) as exc_info:
            conf.load(JsonSource(file=config_file), schema=Config)

        assert len(exc_info.value.exceptions) == 3
        assert exc_info.value.__notes__ == ["... and 7 more errors (10 total)"]
        assert str(exc_info.value) == "Config loading errors (3)"

    def test_merge_conflicts_truncated_at_load_boundary(self, tmp_path: Path):
        fields = [f"field_{i}" for i in range(5)]
        a = tmp_path / "a.json"
        a.write_text("{" + ", ".join(f'"{f}": "a"' for f in fields) + "}")
        b = tmp_path / "b.json"
        b.write_text("{" + ", ".join(f'"{f}": "b"' for f in fields) + "}")

        @dataclass
        class Config:
            field_0: str
            field_1: str
            field_2: str
            field_3: str
            field_4: str

        conf = Dature(masking={"masking_mode": "none"}, error_display={"max_errors": 2})

        with pytest.raises(MergeConflictError) as exc_info:
            conf.load(JsonSource(file=a), JsonSource(file=b), schema=Config, strategy="raise_on_conflict")

        assert len(exc_info.value.exceptions) == 2
        assert exc_info.value.__notes__ == ["... and 3 more merge conflicts (5 total)"]
        assert str(exc_info.value).startswith("Config merge conflicts (2)")

    def test_no_truncation_below_limit_leaves_group_untouched(self, tmp_path: Path):
        content = '{"field_0": "not-an-int"}'
        config_file = _write_json(tmp_path, content)

        @dataclass
        class Config:
            field_0: int

        conf = Dature(masking={"masking_mode": "none"}, error_display={"max_errors": 7})

        with pytest.raises(DatureConfigError) as exc_info:
            conf.load(JsonSource(file=config_file), schema=Config)

        assert len(exc_info.value.exceptions) == 1
        assert getattr(exc_info.value, "__notes__", []) == []
