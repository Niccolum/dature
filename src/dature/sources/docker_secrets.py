from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from dature.errors import SourceLocation
from dature.expansion.env_expand import expand_file_path
from dature.sources.base import FlatKeySource
from dature.types import JSONValue, NestedConflict

if TYPE_CHECKING:
    from dature.types import FilePath


@dataclass(kw_only=True, repr=False)
class DockerSecretsSource(FlatKeySource):
    dir_: "FilePath"
    format_name = "docker_secrets"
    location_label: ClassVar[str] = "SECRET FILE"

    def __post_init__(self) -> None:
        if isinstance(self.dir_, (str, Path)):
            self.dir_ = expand_file_path(str(self.dir_), mode="strict")

    def __repr__(self) -> str:
        return f"{self.format_name} '{self.dir_}'"

    def file_display(self) -> str | None:
        return str(self.dir_)

    def file_path_for_errors(self) -> Path | None:
        return Path(self.dir_)

    def resolve_location(
        self,
        *,
        field_path: list[str],
        file_content: str | None,  # noqa: ARG002
        nested_conflict: NestedConflict | None,
        input_value: JSONValue = None,
    ) -> list[SourceLocation]:
        if nested_conflict is not None:
            json_var = self._resolve_var_name(field_path[:1], self.prefix, self.split_symbols, None)
            if nested_conflict.used_var == json_var:
                secret_name = field_path[0]
            else:
                secret_name = self.split_symbols.join(field_path)
        else:
            secret_name = self.split_symbols.join(field_path)
        if self.prefix is not None:
            secret_name = self.prefix + secret_name
        secret_file = Path(self.dir_) / secret_name
        line_content: list[str] | None = None
        caret: tuple[int, int] | None = None
        with suppress(OSError):
            raw = secret_file.read_text().strip()
            if raw:
                line_content = [raw]
                if input_value is not None:
                    found = self._find_value_in_line(
                        raw,
                        input_value=input_value,
                        field_key=field_path[-1] if field_path else None,
                    )
                    if found is not None:
                        caret = found
                else:
                    caret = (0, len(raw))
        return [
            SourceLocation(
                location_label=self.location_label,
                file_path=secret_file,
                line_range=None,
                line_content=line_content,
                env_var_name=None,
                caret=caret,
            ),
        ]

    def _load(self) -> JSONValue:
        path = Path(self.dir_)

        result: dict[str, JSONValue] = {}
        for entry in sorted(path.iterdir()):
            if not entry.is_file():
                continue

            key = entry.name.lower()
            value = entry.read_text().strip()

            if self.prefix and not key.startswith(self.prefix.lower()):
                continue

            if self.prefix:
                key = key[len(self.prefix) :]

            result[key] = value

        return result
