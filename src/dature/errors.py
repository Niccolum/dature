from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FieldErrorInfo:
    field_path: list[str]
    message: str
    input_value: object | None


@dataclass(frozen=True)
class SourceLocation:
    source_type: str
    file_path: Path | None
    line_number: int | None
    line_content: str | None
    env_var_name: str | None


@dataclass(frozen=True)
class FieldError:
    error: FieldErrorInfo
    location: SourceLocation | None


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
            lines.append(f"       {loc.line_content}")
        return lines

    location_str = f"   └── FILE '{loc.file_path}'"
    if loc.line_number is not None:
        location_str += f", line {loc.line_number}"
    lines.append(location_str)
    if loc.line_content is not None:
        lines.append(f"       {loc.line_content}")

    return lines


class DatureConfigError(Exception):
    def __init__(self, errors: list[FieldError], dataclass_name: str) -> None:
        self.errors = errors
        self.dataclass_name = dataclass_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines: list[str] = []
        lines.append(f"{self.dataclass_name} loading errors ({len(self.errors)})")
        lines.append("")

        for field_error in self.errors:
            path_str = ".".join(field_error.error.field_path)
            if not path_str:
                path_str = "<root>"
            lines.append(f"  [{path_str}]  {field_error.error.message}")

            if field_error.location is not None:
                lines.extend(_format_location(field_error.location))

            lines.append("")

        return "\n".join(lines)


class MergeConflictError(DatureConfigError):
    def __init__(
        self,
        conflicts: list[tuple[FieldErrorInfo, list[SourceLocation]]],
        dataclass_name: str,
    ) -> None:
        self.conflicts = conflicts
        errors = [FieldError(error=info, location=locations[0] if locations else None) for info, locations in conflicts]
        super().__init__(errors, dataclass_name)

    def _format_message(self) -> str:
        lines: list[str] = []
        lines.append(f"{self.dataclass_name} merge conflicts ({len(self.conflicts)})")
        lines.append("")

        for info, locations in self.conflicts:
            path_str = ".".join(info.field_path)
            if not path_str:
                path_str = "<root>"
            lines.append(f"  [{path_str}]  {info.message}")

            for loc in locations:
                lines.extend(_format_location(loc))

            lines.append("")

        return "\n".join(lines)
