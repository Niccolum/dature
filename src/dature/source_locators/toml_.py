from dataclasses import dataclass

from dature.errors import LineRange
from dature.source_locators.line_base import LinePathFinder


class TomlPathFinder(LinePathFinder):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self._current_section: list[str] = []
        self._in_multiline: str | None = None

    def _process_line(self, line_num: int, line: str, target_path: list[str]) -> LineRange | None:
        target_key = target_path[-1]
        target_parents = target_path[:-1]

        if self._in_multiline is not None:
            if self._in_multiline in line:
                self._in_multiline = None
            return None

        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            return None

        if stripped.startswith("[") and "]" in stripped:
            section_name = stripped.strip("[] ")
            self._current_section = [p.strip() for p in section_name.split(".")]
            return None

        if "=" not in stripped:
            return None

        key, _, value = stripped.partition("=")
        key = key.strip().strip("\"'")
        value = value.strip()

        unclosed = _detect_unclosed_multiline(value)
        if unclosed is not None:
            if key != target_key or self._current_section != target_parents:
                self._in_multiline = unclosed
                return None
            # Found target with multiline string
            end_line = _find_multiline_string_end(self._lines, line_num, unclosed)
            return LineRange(start=line_num, end=end_line)

        if key != target_key or self._current_section != target_parents:
            return None

        # Check for inline table/array
        end_line = _find_inline_container_end(self._lines, line_num - 1, value)
        return LineRange(start=line_num, end=end_line)


def _detect_unclosed_multiline(value: str) -> str | None:
    for delimiter in ('"""', "'''"):
        if delimiter not in value:
            continue
        # odd number of delimiters means unclosed
        count = value.count(delimiter)
        if count % 2 == 1:
            return delimiter
    return None


def _find_multiline_string_end(lines: list[str], start_line_1based: int, delimiter: str) -> int:
    """Find the line (1-based) where the multiline string closes."""
    for j in range(start_line_1based, len(lines)):
        if delimiter in lines[j]:
            return j + 1  # 1-based
    return start_line_1based


@dataclass
class _ContainerState:
    depth: int
    in_string: str | None


def _process_container_char(ch: str, state: _ContainerState) -> None:
    if state.in_string is not None:
        if ch == "\\":
            return
        if ch == state.in_string:
            state.in_string = None
        return
    if ch in {'"', "'"}:
        state.in_string = ch
        return
    if ch in "{[":
        state.depth += 1
    elif ch in "}]":
        state.depth -= 1


def _find_inline_container_end(lines: list[str], line_index: int, value: str) -> int:
    state = _ContainerState(depth=0, in_string=None)

    for ch in value:
        _process_container_char(ch, state)

    if state.depth == 0:
        return line_index + 1  # 1-based

    for j in range(line_index + 1, len(lines)):
        for ch in lines[j]:
            _process_container_char(ch, state)
        if state.depth == 0:
            return j + 1  # 1-based

    return len(lines)
