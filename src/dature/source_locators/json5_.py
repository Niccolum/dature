from dataclasses import dataclass


@dataclass
class _StackEntry:
    key: str | None
    is_array: bool
    array_index: int


@dataclass
class _ParseState:
    pos: int
    line: int
    last_key: str | None


class Json5PathFinder:
    def __init__(self, content: str) -> None:
        self._content = content

    def find_line(self, target_path: list[str]) -> int:
        content = self._content
        length = len(content)
        state = _ParseState(pos=0, line=1, last_key=None)
        stack: list[_StackEntry] = []

        while state.pos < length:
            ch = content[state.pos]

            if _try_skip_noise(ch, content, state, length):
                continue

            if ch in "{}[]":
                state.pos, state.last_key = _handle_bracket(ch, stack, state.last_key, state.pos)
                continue

            if ch in {'"', "'"}:
                result = _handle_quoted(content, state, length, stack, target_path)
                if result != -1:
                    return result
                continue

            if _is_ident_start(ch):
                result = _handle_identifier(content, state, length, stack, target_path)
                if result != -1:
                    return result
                continue

            _increment_parent_array(stack)
            state.pos = _skip_scalar(content, state.pos, length)

        return -1


def _try_skip_noise(ch: str, content: str, state: _ParseState, length: int) -> bool:
    if ch in " \t\r\n":
        if ch == "\n":
            state.line += 1
        state.pos += 1
        return True

    if ch == ",":
        state.pos += 1
        return True

    if ch != "/" or state.pos + 1 >= length:
        return False

    next_ch = content[state.pos + 1]
    if next_ch == "/":
        state.pos = _skip_line_comment(content, state.pos + 2, length)
        return True
    if next_ch == "*":
        state.pos, state.line = _skip_block_comment(content, state.pos + 2, length, state.line)
        return True

    return False


def _handle_quoted(
    content: str,
    state: _ParseState,
    length: int,
    stack: list[_StackEntry],
    target_path: list[str],
) -> int:
    quote = content[state.pos]
    string_value, state.pos, state.line = _read_quoted_string(
        content,
        state.pos + 1,
        quote,
        state.line,
    )
    colon_pos, colon_line = _skip_ws_and_comments(content, state.pos, length, state.line)

    if colon_pos >= length or content[colon_pos] != ":":
        _increment_parent_array(stack)
        state.last_key = None
        return -1

    if _build_path(stack, string_value) == target_path:
        return state.line

    state.last_key = string_value
    state.pos = colon_pos + 1
    state.line = colon_line
    return -1


def _handle_identifier(
    content: str,
    state: _ParseState,
    length: int,
    stack: list[_StackEntry],
    target_path: list[str],
) -> int:
    ident, state.pos = _read_identifier(content, state.pos, length)
    colon_pos, colon_line = _skip_ws_and_comments(content, state.pos, length, state.line)

    if colon_pos < length and content[colon_pos] == ":":
        if _build_path(stack, ident) == target_path:
            return state.line

        state.last_key = ident
        state.pos = colon_pos + 1
        state.line = colon_line
        return -1

    _increment_parent_array(stack)
    return -1


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


def _build_path(stack: list[_StackEntry], current_key: str) -> list[str]:
    path: list[str] = []
    for entry in stack:
        if entry.key is not None:
            path.append(entry.key)
        if entry.is_array:
            path.append(str(entry.array_index))
    path.append(current_key)
    return path


def _read_quoted_string(
    content: str,
    pos: int,
    quote: str,
    line: int,
) -> tuple[str, int, int]:
    start = pos
    while pos < len(content):
        ch = content[pos]
        if ch == "\\":
            if pos + 1 < len(content) and content[pos + 1] == "\n":
                line += 1
            pos += 2
            continue
        if ch == "\n":
            line += 1
            pos += 1
            continue
        if ch == quote:
            return content[start:pos], pos + 1, line
        pos += 1
    return content[start:pos], pos, line


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch in {"_", "$"}


def _is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "$"}


def _read_identifier(content: str, pos: int, length: int) -> tuple[str, int]:
    start = pos
    while pos < length and _is_ident_char(content[pos]):
        pos += 1
    return content[start:pos], pos


def _skip_line_comment(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] != "\n":
        pos += 1
    return pos


def _skip_block_comment(
    content: str,
    pos: int,
    length: int,
    line: int,
) -> tuple[int, int]:
    while pos < length:
        if content[pos] == "\n":
            line += 1
        elif content[pos] == "*" and pos + 1 < length and content[pos + 1] == "/":
            return pos + 2, line
        pos += 1
    return pos, line


def _skip_ws_and_comments(
    content: str,
    pos: int,
    length: int,
    line: int,
) -> tuple[int, int]:
    while pos < length:
        ch = content[pos]
        if ch in " \t\r":
            pos += 1
            continue
        if ch == "\n":
            line += 1
            pos += 1
            continue
        if ch == "/" and pos + 1 < length and content[pos + 1] == "/":
            pos = _skip_line_comment(content, pos + 2, length)
            continue
        if ch == "/" and pos + 1 < length and content[pos + 1] == "*":
            pos, line = _skip_block_comment(content, pos + 2, length, line)
            continue
        return pos, line
    return pos, line


def _skip_scalar(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] not in " \t\r\n,}]":
        pos += 1
    return pos
