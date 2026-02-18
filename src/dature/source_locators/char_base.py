import abc
from dataclasses import dataclass

from dature.errors import LineRange
from dature.source_locators.base import PathFinder


@dataclass
class StackEntry:
    key: str | None
    is_array: bool
    array_index: int


@dataclass(frozen=True, slots=True)
class PosLine:
    pos: int
    line: int


@dataclass(frozen=True, slots=True)
class KeyParseResult:
    pos: int
    line: int
    last_key: str | None
    found: bool


class CharPathFinder(PathFinder):
    def __init__(self, content: str) -> None:
        self._content = content

    def find_line_range(self, target_path: list[str]) -> LineRange | None:
        content = self._content
        length = len(content)
        pos = 0
        line = 1
        stack: list[StackEntry] = []
        last_key: str | None = None

        while pos < length:
            ch = content[pos]

            noise = self._skip_noise(content, pos, line, length)
            if noise is not None:
                pos = noise.pos
                line = noise.line
                continue

            if ch in "{[":
                increment_parent_array(stack)
                is_array = ch == "["
                stack.append(StackEntry(key=last_key, is_array=is_array, array_index=-1))
                pos += 1
                last_key = None
                continue

            if ch in "}]":
                if stack:
                    stack.pop()
                pos += 1
                last_key = None
                continue

            result = self._try_parse_key(content, pos, line, length, stack, target_path)
            if result is not None:
                if result.found:
                    end_line = self._find_value_end_line(content, result.pos, length, result.line)
                    return LineRange(start=result.line, end=end_line)
                pos = result.pos
                line = result.line
                last_key = result.last_key
                continue

            increment_parent_array(stack)
            pos = skip_scalar(content, pos, length)

        return None

    @abc.abstractmethod
    def _skip_noise(self, content: str, pos: int, line: int, length: int) -> PosLine | None: ...

    @abc.abstractmethod
    def _try_parse_key(
        self,
        content: str,
        pos: int,
        line: int,
        length: int,
        stack: list[StackEntry],
        target_path: list[str],
    ) -> KeyParseResult | None: ...

    @abc.abstractmethod
    def _find_value_end_line(self, content: str, pos: int, length: int, start_line: int) -> int: ...


def increment_parent_array(stack: list[StackEntry]) -> None:
    if stack and stack[-1].is_array:
        stack[-1].array_index += 1


def build_path(stack: list[StackEntry], current_key: str) -> list[str]:
    path: list[str] = []
    for entry in stack:
        if entry.key is not None:
            path.append(entry.key)
        if entry.is_array:
            path.append(str(entry.array_index))
    path.append(current_key)
    return path


def skip_scalar(content: str, pos: int, length: int) -> int:
    while pos < length and content[pos] not in " \t\r\n,}]":
        pos += 1
    return pos
