from dature.errors import LineRange
from dature.source_locators.line_base import LinePathFinder


class YamlPathFinder(LinePathFinder):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self._stack: list[dict[str, str | int]] = []

    def _process_line(self, line_num: int, line: str, target_path: list[str]) -> LineRange | None:
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("#", "-")):
            return None

        indent = len(line) - len(stripped)
        key_part, sep, value_part = stripped.partition(":")
        if not sep:
            return None

        key = key_part.strip().strip("\"'")

        while self._stack and int(self._stack[-1]["indent"]) >= indent:
            self._stack.pop()

        self._stack.append({"key": key, "indent": indent})
        if [item["key"] for item in self._stack] != target_path:
            return None

        value = value_part.strip()
        # Inline value (not empty and not block scalar indicator)
        if value and value not in ("|", ">", "|-", ">-", "|+", ">+"):
            return LineRange(start=line_num, end=line_num)

        # Block value or nested mapping: scan forward
        end_line = line_num
        for j in range(line_num, len(self._lines)):
            next_line = self._lines[j]
            next_stripped = next_line.lstrip()
            if not next_stripped or next_stripped.startswith("#"):
                continue
            next_indent = len(next_line) - len(next_stripped)
            if next_indent <= indent:
                break
            end_line = j + 1  # 1-based
        return LineRange(start=line_num, end=end_line)
