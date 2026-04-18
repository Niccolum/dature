"""Error message formatting helpers."""

import json
from typing import TYPE_CHECKING

from dature.config import config
from dature.types import JSONValue

if TYPE_CHECKING:
    from dature.errors.exceptions import SourceLocation


def format_path(field_path: list[str]) -> str:
    return ".".join(field_path) or "<root>"


def _truncate_line(line: str) -> str:
    max_length = config.error_display.max_line_length
    if len(line) > max_length:
        return line[: max_length - 3] + "..."
    return line


def _format_content_lines(content: list[str], *, prefix: str = "       ") -> list[str]:
    max_visible = config.error_display.max_visible_lines
    if len(content) > max_visible:
        visible = content[: max_visible - 1]
        lines = [f"{prefix}{_truncate_line(line)}" for line in visible]
        lines.append(f"{prefix}...")
        return lines
    return [f"{prefix}{_truncate_line(line)}" for line in content]


def _value_candidates(input_value: JSONValue) -> list[str]:
    if isinstance(input_value, (list, dict)):
        return [json.dumps(input_value, ensure_ascii=False)]
    if input_value == "":
        return ['""', "''"]
    text = str(input_value)
    lower = text.lower()
    return [text] if lower == text else [text, lower]


def _find_value_position(
    line: str,
    *,
    input_value: JSONValue,
    field_key: str | None,
) -> "tuple[int, int] | None":
    candidates = _value_candidates(input_value)
    if field_key is not None:
        key_marker = f'"{field_key}":'
        key_pos = line.find(key_marker)
        if key_pos != -1:
            search_from = key_pos + len(key_marker)
            for candidate in candidates:
                pos = line.find(candidate, search_from)
                if pos != -1:
                    return (pos, len(candidate))
    for candidate in candidates:
        pos = line.rfind(candidate)
        if pos != -1:
            return (pos, len(candidate))
    return None


def _compute_caret(
    loc: "SourceLocation",
    *,
    input_value: JSONValue,
    field_key: str | None,
) -> "tuple[int, int] | None":
    if loc.caret is not None:
        return loc.caret
    if loc.line_content is None or len(loc.line_content) != 1:
        return None
    line = loc.line_content[0]
    if input_value is not None:
        return _find_value_position(line, input_value=input_value, field_key=field_key)
    eq_pos = line.find("=")
    if eq_pos != -1:
        return (eq_pos + 1, len(line) - eq_pos - 1)
    return (0, len(line))


def _format_caret(caret: tuple[int, int]) -> str | None:
    pos, length = caret
    max_visible = config.error_display.max_line_length - 3
    if pos >= max_visible:
        return None
    return f"   │   {' ' * pos}{'^' * min(length, max_visible - pos)}"


def _format_fileline(loc: "SourceLocation", *, connector: str, suffix: str) -> str:
    line = f"   {connector} {loc.location_label} '{loc.file_path}'"
    if loc.line_range is not None:
        line += f", {loc.line_range!r}"
    return line + suffix


def format_location(
    loc: "SourceLocation",
    *,
    last: bool = True,
    input_value: JSONValue = None,
    field_key: str | None = None,
) -> list[str]:
    connector = "└──" if last else "├──"
    suffix = f" ({loc.annotation})" if loc.annotation is not None else ""

    if loc.env_var_name is not None and loc.file_path is None:
        main = f"   {connector} {loc.location_label} '{loc.env_var_name}'"
        if loc.env_var_value is not None:
            main += f" = '{loc.env_var_value}'"
        return [main + suffix]

    if loc.file_path is None:
        return []

    lines: list[str] = []
    if loc.line_content is not None:
        lines.extend(_format_content_lines(loc.line_content, prefix="   ├── "))
        caret = _compute_caret(loc, input_value=input_value, field_key=field_key)
        if caret is not None and (caret_line := _format_caret(caret)) is not None:
            lines.append(caret_line)

    lines.append(_format_fileline(loc, connector=connector, suffix=suffix))
    return lines
