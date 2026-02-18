from dature.errors import LineRange
from dature.source_locators.line_base import LinePathFinder


class TablePathFinder(LinePathFinder):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self._current_section: list[str] = []

    def _process_line(self, line_num: int, line: str, target_path: list[str]) -> LineRange | None:
        target_key = target_path[-1]
        target_parents = target_path[:-1]

        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            return None

        if line[0] in (" ", "\t"):
            return None

        if stripped.startswith("[") and "]" in stripped:
            section_name = stripped.strip("[] ")
            self._current_section = section_name.split(".")
            return None

        sep = "=" if "=" in stripped else ":"
        if sep not in stripped:
            return None

        key = stripped.partition(sep)[0].strip().strip("\"'")
        if key != target_key or self._current_section != target_parents:
            return None

        # Found the key; check for continuation lines
        end_line = line_num
        for j in range(line_num, len(self._lines)):
            next_line = self._lines[j]
            if not next_line or next_line[0] not in (" ", "\t"):
                break
            end_line = j + 1  # 1-based

        return LineRange(start=line_num, end=end_line)
