from dature.source_locators.char_base import (
    CharPathFinder,
    KeyParseResult,
    PosLine,
    StackEntry,
    build_path,
    increment_parent_array,
)


class JsonPathFinder(CharPathFinder):
    def _skip_noise(self, content: str, pos: int, line: int, length: int) -> PosLine | None:
        if pos >= length:
            return None
        ch = content[pos]
        if ch in " \t\r\n":
            if ch == "\n":
                line += 1
            return PosLine(pos=pos + 1, line=line)
        if ch == ",":
            return PosLine(pos=pos + 1, line=line)
        return None

    def _try_parse_key(
        self,
        content: str,
        pos: int,
        line: int,
        length: int,
        stack: list[StackEntry],
        target_path: list[str],
    ) -> KeyParseResult | None:
        if content[pos] != '"':
            return None

        string_start = pos + 1
        end_pos = _skip_string(content, string_start)
        string_value = content[string_start : end_pos - 1]

        colon_pos = _skip_ws(content, end_pos, length)

        if colon_pos >= length or content[colon_pos] != ":":
            increment_parent_array(stack)
            return KeyParseResult(pos=end_pos, line=line, last_key=None, found=False)

        if build_path(stack, string_value) == target_path:
            return KeyParseResult(pos=end_pos, line=line, last_key=None, found=True)

        return KeyParseResult(pos=colon_pos + 1, line=line, last_key=string_value, found=False)

    def _find_value_end_line(self, content: str, pos: int, length: int, start_line: int) -> int:
        pos, current_line = _skip_to_value_start(content, pos, length, start_line)
        if pos >= length:
            return current_line

        ch = content[pos]

        if ch == '"':
            return current_line

        if ch in "{[":
            return _scan_container_end(content, pos, length, current_line)

        return current_line


def _skip_string(content: str, pos: int) -> int:
    """Advance past a JSON string body. Returns position after the closing quote."""
    length = len(content)
    while pos < length:
        ch = content[pos]
        if ch == "\\":
            pos += 2
            continue
        if ch == '"':
            return pos + 1
        pos += 1
    return pos


def _skip_ws(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] in " \t\r\n":
        pos += 1
    return pos


def _skip_to_value_start(
    content: str,
    pos: int,
    length: int,
    current_line: int,
) -> tuple[int, int]:
    while pos < length and content[pos] != ":":
        if content[pos] == "\n":
            current_line += 1
        pos += 1
    if pos >= length:
        return pos, current_line
    pos += 1

    while pos < length and content[pos] in " \t\r\n":
        if content[pos] == "\n":
            current_line += 1
        pos += 1

    return pos, current_line


def _scan_container_end(content: str, pos: int, length: int, current_line: int) -> int:
    depth = 1
    pos += 1
    while pos < length and depth > 0:
        c = content[pos]
        if c == "\n":
            current_line += 1
        elif c == '"':
            pos = _skip_string(content, pos + 1)
            continue
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        pos += 1
    return current_line
