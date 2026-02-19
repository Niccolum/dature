from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True, slots=True)
class LineRange:
    start: int
    end: int

    def __repr__(self) -> str:
        if self.start == self.end:
            return f"line {self.start}"
        return f"line {self.start}-{self.end}"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    source_type: str
    file_path: Path | None
    line_range: LineRange | None
    line_content: list[str] | None
    env_var_name: str | None


def _truncate_line(line: str, max_length: int = 80) -> str:
    if len(line) > max_length:
        return line[: max_length - 3] + "..."
    return line


def _format_location(loc: SourceLocation) -> list[str]:
    lines: list[str] = []

    if loc.source_type == "env":
        if loc.env_var_name is not None:
            lines.append(f"   └── ENV '{loc.env_var_name}'")
        return lines

    if loc.source_type == "envfile":
        location_str = f"   └── ENV FILE '{loc.file_path}'"
        if loc.env_var_name is not None:
            location_str += f", var '{loc.env_var_name}'"
        lines.append(location_str)
        if loc.line_content is not None:
            lines.extend(f"       {_truncate_line(content_line)}" for content_line in loc.line_content)
        return lines

    location_str = f"   └── FILE '{loc.file_path}'"
    if loc.line_range is not None:
        location_str += f", {loc.line_range!r}"
    lines.append(location_str)
    if loc.line_content is not None:
        lines.extend(f"       {_truncate_line(content_line)}" for content_line in loc.line_content)

    return lines


class DatureError(Exception):
    """Базовая ошибка dature."""


class FieldLoadError(DatureError):
    def __init__(
        self,
        *,
        field_path: list[str],
        message: str,
        input_value: str | float | bool | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        self.field_path = field_path
        self.message = message
        self.input_value = input_value
        self.location = location
        super().__init__(self._format())

    def _format(self) -> str:
        path_str = ".".join(self.field_path)
        if not path_str:
            path_str = "<root>"
        lines = [f"  [{path_str}]  {self.message}"]
        if self.location is not None:
            lines.extend(_format_location(self.location))
        return "\n".join(lines)


class MergeConflictFieldError(DatureError):
    def __init__(
        self,
        *,
        field_path: list[str],
        message: str,
        locations: list[SourceLocation],
    ) -> None:
        self.field_path = field_path
        self.message = message
        self.locations = locations
        super().__init__(self._format())

    def _format(self) -> str:
        path_str = ".".join(self.field_path)
        if not path_str:
            path_str = "<root>"
        lines = [f"  [{path_str}]  {self.message}"]
        for loc in self.locations:
            lines.extend(_format_location(loc))
        return "\n".join(lines)


class SourceLoadError(DatureError):
    def __init__(
        self,
        *,
        message: str,
        location: SourceLocation | None = None,
    ) -> None:
        self.message = message
        self.location = location
        super().__init__(message)


class DatureConfigError(ExceptionGroup[DatureError]):
    dataclass_name: str

    def __new__(
        cls,
        dataclass_name: str,
        errors: Sequence[DatureError],
    ) -> Self:
        obj = super().__new__(
            cls,
            f"{dataclass_name} loading errors ({len(errors)})",
            errors,
        )
        obj.dataclass_name = dataclass_name
        return obj

    def __init__(
        self,
        dataclass_name: str,
        errors: Sequence[DatureError],
    ) -> None:
        pass

    def derive(self, excs: Sequence[DatureError], /) -> Self:  # type: ignore[override]
        return self.__class__(self.dataclass_name, list(excs))

    def __str__(self) -> str:
        lines: list[str] = []
        lines.append(f"{self.dataclass_name} loading errors ({len(self.exceptions)})")
        lines.append("")

        for exc in self.exceptions:
            if isinstance(exc, FieldLoadError):
                path_str = ".".join(exc.field_path)
                if not path_str:
                    path_str = "<root>"
                lines.append(f"  [{path_str}]  {exc.message}")
                if exc.location is not None:
                    lines.extend(_format_location(exc.location))
                lines.append("")
            elif isinstance(exc, SourceLoadError):
                lines.append(f"  [<root>]  {exc.message}")
                if exc.location is not None:
                    lines.extend(_format_location(exc.location))
                lines.append("")
            else:
                lines.append(f"  {exc}")
                lines.append("")

        return "\n".join(lines)


class MergeConflictError(DatureConfigError):
    def __new__(
        cls,
        dataclass_name: str,
        errors: Sequence[MergeConflictFieldError],
    ) -> Self:
        return super().__new__(cls, dataclass_name, errors)

    def __str__(self) -> str:
        lines: list[str] = []
        lines.append(f"{self.dataclass_name} merge conflicts ({len(self.exceptions)})")
        lines.append("")

        for exc in self.exceptions:
            if isinstance(exc, MergeConflictFieldError):
                path_str = ".".join(exc.field_path)
                if not path_str:
                    path_str = "<root>"
                lines.append(f"  [{path_str}]  {exc.message}")
                for loc in exc.locations:
                    lines.extend(_format_location(loc))
                lines.append("")
            else:
                lines.append(f"  {exc}")
                lines.append("")

        return "\n".join(lines)
