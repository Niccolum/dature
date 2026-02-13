from dataclasses import dataclass


class JsonPathFinder:
    def __init__(self, content: str) -> None:
        self._content = content

    def find_line(self, target_path: list[str]) -> int:
        content = self._content
        length = len(content)
        pos = 0
        line = 1
        stack: list[_StackEntry] = []
        last_key: str | None = None

        while pos < length:
            ch = content[pos]

            if ch in " \t\r\n":
                if ch == "\n":
                    line += 1
                pos += 1
                continue

            if ch == ",":
                pos += 1
                continue

            if ch in "{}[]":
                pos, last_key = _handle_bracket(ch, stack, last_key, pos)
                continue

            if ch != '"':
                # Scalar value (number, true, false, null)
                _increment_parent_array(stack)
                pos = _skip_until(content, pos, length)
                continue

            string_value, pos = _read_string(content, pos + 1)
            colon_pos = _skip_ws(content, pos, length)

            if colon_pos >= length or content[colon_pos] != ":":
                # String value, not a key
                _increment_parent_array(stack)
                last_key = None
                continue

            # Found the key
            if _build_path(stack, string_value) == target_path:
                return line

            last_key = string_value
            pos = colon_pos + 1

        return -1


@dataclass
class _StackEntry:
    key: str | None
    is_array: bool
    array_index: int


def _handle_bracket(
    ch: str,
    stack: list[_StackEntry],
    last_key: str | None,
    pos: int,
) -> tuple[int, None]:
    if ch == "{":
        _increment_parent_array(stack)
        stack.append(_StackEntry(key=last_key, is_array=False, array_index=-1))
    elif ch == "[":
        _increment_parent_array(stack)
        stack.append(_StackEntry(key=last_key, is_array=True, array_index=-1))
    elif stack:
        stack.pop()
    return pos + 1, None


def _increment_parent_array(stack: list[_StackEntry]) -> None:
    if stack and stack[-1].is_array:
        stack[-1].array_index += 1


def _read_string(content: str, pos: int) -> tuple[str, int]:
    start = pos
    while pos < len(content):
        ch = content[pos]
        if ch == "\\":
            pos += 2
            continue
        if ch == '"':
            return content[start:pos], pos + 1
        pos += 1
    return content[start:pos], pos


def _skip_ws(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] in " \t\r\n":
        pos += 1
    return pos


def _skip_until(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] not in " \t\r\n,}]":
        pos += 1
    return pos


def _build_path(stack: list[_StackEntry], current_key: str) -> list[str]:
    path: list[str] = []
    for entry in stack:
        if entry.key is not None:
            path.append(entry.key)
        if entry.is_array:
            path.append(str(entry.array_index))
    path.append(current_key)
    return path
