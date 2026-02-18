import abc

from dature.errors import LineRange
from dature.source_locators.base import PathFinder


class LinePathFinder(PathFinder):
    def __init__(self, content: str) -> None:
        self._lines = content.splitlines()

    def find_line_range(self, target_path: list[str]) -> LineRange | None:
        for i, line in enumerate(self._lines, 1):
            result = self._process_line(i, line, target_path)
            if result is not None:
                return result
        return None

    @abc.abstractmethod
    def _process_line(self, line_num: int, line: str, target_path: list[str]) -> LineRange | None: ...
