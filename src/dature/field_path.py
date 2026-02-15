from dataclasses import dataclass, fields, is_dataclass
from typing import TypeVar, get_type_hints, overload

T = TypeVar("T")


def _resolve_field_type(owner: type, parts: tuple[str, ...]) -> type | None:
    """Walk the field chain and return the type of the last field, or None if not a dataclass."""
    current = owner
    for part in parts:
        if not is_dataclass(current):
            return None
        hints = get_type_hints(current)
        if part not in hints:
            return None
        current = hints[part]
    if not is_dataclass(current):
        return None
    return current


def _validate_field(owner: type, parts: tuple[str, ...], name: str) -> None:
    if not parts:
        target = owner
    else:
        resolved = _resolve_field_type(owner, parts)
        if resolved is None:
            return
        target = resolved

    field_names = {f.name for f in fields(target)}
    if name not in field_names:
        msg = f"'{target.__name__}' has no field '{name}'"
        raise AttributeError(msg)


@dataclass(frozen=True, slots=True)
class FieldPath:
    owner: type | str
    parts: tuple[str, ...] = ()

    def __getattr__(self, name: str) -> "FieldPath":
        if isinstance(self.owner, type):
            _validate_field(self.owner, self.parts, name)
        return FieldPath(owner=self.owner, parts=(*self.parts, name))

    def as_path(self) -> str:
        if not self.parts:
            msg = "FieldPath must contain at least one field name"
            raise ValueError(msg)
        return ".".join(self.parts)


class _FieldPathFactory:
    @overload
    def __getitem__(self, owner: type[T]) -> T: ...

    @overload
    def __getitem__(self, owner: str) -> FieldPath: ...

    def __getitem__(self, owner: type | str) -> object:
        if isinstance(owner, type) and not is_dataclass(owner):
            msg = f"'{owner.__name__}' is not a dataclass"
            raise TypeError(msg)
        return FieldPath(owner=owner)


F = _FieldPathFactory()
