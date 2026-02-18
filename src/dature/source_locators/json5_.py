from dataclasses import dataclass

from dature.source_locators.char_base import (
    CharPathFinder,
    KeyParseResult,
    PosLine,
    StackEntry,
    build_path,
    increment_parent_array,
)


class Json5PathFinder(CharPathFinder):
    def _skip_noise(self, content: str, pos: int, line: int, length: int) -> PosLine | None:
        ch = content[pos]
        if ch in " \t\r\n":
            if ch == "\n":
                line += 1
            return PosLine(pos=pos + 1, line=line)

        if ch == ",":
            return PosLine(pos=pos + 1, line=line)

        if ch != "/" or pos + 1 >= length:
            return None

        next_ch = content[pos + 1]
        if next_ch == "/":
            return PosLine(pos=_skip_line_comment(content, pos + 2, length), line=line)
        if next_ch == "*":
            block = _skip_block_comment(content, pos + 2, length, line)
            return PosLine(pos=block.pos, line=block.line)

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
        ch = content[pos]

        if ch in {'"', "'"}:
            return _handle_quoted(content, pos, line, length, stack, target_path)

        if _is_ident_start(ch):
            return _handle_identifier(content, pos, line, length, stack, target_path)

        return None

    def _find_value_end_line(self, content: str, pos: int, length: int, start_line: int) -> int:
        current_line = start_line

        pl = _skip_ws_and_comments(content, pos, length, current_line)
        pos = pl.pos
        current_line = pl.line
        if pos >= length or content[pos] != ":":
            return start_line
        pos += 1

        pl = _skip_ws_and_comments(content, pos, length, current_line)
        pos = pl.pos
        current_line = pl.line

        if pos >= length:
            return current_line

        ch = content[pos]

        if ch in {'"', "'"}:
            end = _skip_quoted_string(content, pos + 1, ch, current_line)
            return end.line

        if ch in "{[":
            return _scan_json5_container_end(content, pos, length, current_line)

        return current_line


@dataclass(frozen=True, slots=True)
class _PosLine:
    pos: int
    line: int


def _handle_quoted(
    content: str,
    pos: int,
    line: int,
    length: int,
    stack: list[StackEntry],
    target_path: list[str],
) -> KeyParseResult:
    quote = content[pos]
    string_start = pos + 1
    end = _skip_quoted_string(content, string_start, quote, line)
    string_value = content[string_start : end.pos - 1]

    colon = _skip_ws_and_comments(content, end.pos, length, end.line)

    if colon.pos >= length or content[colon.pos] != ":":
        increment_parent_array(stack)
        return KeyParseResult(pos=end.pos, line=end.line, last_key=None, found=False)

    if build_path(stack, string_value) == target_path:
        return KeyParseResult(pos=end.pos, line=line, last_key=None, found=True)

    return KeyParseResult(pos=colon.pos + 1, line=colon.line, last_key=string_value, found=False)


def _handle_identifier(
    content: str,
    pos: int,
    line: int,
    length: int,
    stack: list[StackEntry],
    target_path: list[str],
) -> KeyParseResult:
    ident_end = _skip_identifier(content, pos, length)
    ident = content[pos:ident_end]

    colon = _skip_ws_and_comments(content, ident_end, length, line)

    if colon.pos >= length or content[colon.pos] != ":":
        increment_parent_array(stack)
        return KeyParseResult(pos=ident_end, line=line, last_key=None, found=False)

    if build_path(stack, ident) == target_path:
        return KeyParseResult(pos=ident_end, line=line, last_key=None, found=True)

    return KeyParseResult(pos=colon.pos + 1, line=colon.line, last_key=ident, found=False)


def _skip_quoted_string(
    content: str,
    pos: int,
    quote: str,
    line: int,
) -> _PosLine:
    """Advance past a quoted string body. Returns position after the closing quote."""
    length = len(content)
    while pos < length:
        ch = content[pos]
        if ch == "\\":
            if pos + 1 < length and content[pos + 1] == "\n":
                line += 1
            pos += 2
            continue
        if ch == "\n":
            line += 1
            pos += 1
            continue
        if ch == quote:
            return _PosLine(pos=pos + 1, line=line)
        pos += 1
    return _PosLine(pos=pos, line=line)


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch in {"_", "$"}


def _is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "$"}


def _skip_identifier(content: str, pos: int, length: int) -> int:
    while pos < length and _is_ident_char(content[pos]):
        pos += 1
    return pos


def _skip_line_comment(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] != "\n":
        pos += 1
    return pos


def _skip_block_comment(
    content: str,
    pos: int,
    length: int,
    line: int,
) -> _PosLine:
    while pos < length:
        if content[pos] == "\n":
            line += 1
        elif content[pos] == "*" and pos + 1 < length and content[pos + 1] == "/":
            return _PosLine(pos=pos + 2, line=line)
        pos += 1
    return _PosLine(pos=pos, line=line)


def _skip_ws_and_comments(
    content: str,
    pos: int,
    length: int,
    line: int,
) -> _PosLine:
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
            block = _skip_block_comment(content, pos + 2, length, line)
            pos = block.pos
            line = block.line
            continue
        return _PosLine(pos=pos, line=line)
    return _PosLine(pos=pos, line=line)


def _scan_json5_container_end(
    content: str,
    pos: int,
    length: int,
    current_line: int,
) -> int:
    depth = 1
    pos += 1
    while pos < length and depth > 0:
        c = content[pos]
        if c == "\n":
            current_line += 1
        elif c in {'"', "'"}:
            end = _skip_quoted_string(content, pos + 1, c, current_line)
            pos = end.pos
            current_line = end.line
            continue
        elif c == "/" and pos + 1 < length:
            nc = content[pos + 1]
            if nc == "/":
                pos = _skip_line_comment(content, pos + 2, length)
                continue
            if nc == "*":
                block = _skip_block_comment(content, pos + 2, length, current_line)
                pos = block.pos
                current_line = block.line
                continue
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        pos += 1
    return current_line
