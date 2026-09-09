"""Schema → tree of fields whose ``default_factory`` cannot be called with zero arguments.

Mirrors ``strict/known_keys.py``'s recursive dataclass walk: a field's own nested shape is
built once per schema and memoized. Unlike ``known_keys.py``, container elements
(``list[Db]``) are deliberately **not** descended into — a container's contents are data,
not a fixed schema path, and a ``default_factory`` fallback is never invoked for an element
of a list/dict (only for the *field itself* being absent).

Used by ``dature.loading.field_pass.enrich_missing_factory_field_errors`` and
``recover_factory_type_error`` to turn a missing-field error, or a bare ``TypeError`` raised
while adaptix invokes a missing field's ``default_factory`` (e.g. ``TgConfig.__init__() missing
3 required positional arguments: ...``), into a ``FieldLoadError`` that names the field path and
the required subfields.
"""

import inspect
import types
from collections.abc import Callable
from dataclasses import MISSING, dataclass, fields, is_dataclass
from typing import Annotated, Union, cast, get_args, get_origin, get_type_hints

from dature.protocols import DataclassInstance
from dature.type_aliases import TypeAnnotation

_POSITIONAL_OR_KEYWORD = (
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
)


@dataclass(frozen=True, slots=True)
class UnsafeFactoryField:
    """A field whose ``default_factory`` cannot be called with zero arguments."""

    name: str
    """Declared field name (not canonicalized) — used verbatim in the reported path."""
    factory_name: str
    """Display name of the factory, e.g. ``"TgConfig"``, for the error message."""
    required_params: tuple[str, ...]
    """Names of the factory's parameters that have no default."""


@dataclass(frozen=True, slots=True)
class FactoryNode:
    """One dataclass level of the schema, pruned to branches that contain an unsafe factory."""

    dc_type: type[DataclassInstance]
    """The dataclass this node was built from — used to look up aliases by owner type."""
    unsafe: tuple[UnsafeFactoryField, ...]
    """This level's own fields with an unsafe ``default_factory``."""
    children: "dict[str, FactoryNode]"
    """Declared field name (not canonicalized) → node for fields that are themselves a
    dataclass. Kept as the declared name so callers can canonicalize on demand for lookup
    while still reporting the schema's own spelling in field paths."""


def required_params_of(factory: Callable[..., object]) -> tuple[str, ...] | None:
    """Return the names *factory* requires to be called, or ``None`` if it needs none.

    Purely static reflection — *factory* is never invoked. ``inspect.signature`` failing
    (``ValueError`` for builtins such as ``dict``) is treated as safe: guessing would risk
    turning a working config into a hard error.
    """
    try:
        sig = inspect.signature(factory)
    except (TypeError, ValueError):
        return None

    try:
        sig.bind()
    except TypeError:
        pass
    else:
        return None

    required = tuple(
        name
        for name, param in sig.parameters.items()
        if param.default is inspect.Parameter.empty and param.kind in _POSITIONAL_OR_KEYWORD
    )
    return required or None


def _strip_annotated(field_type: TypeAnnotation) -> TypeAnnotation:
    while get_origin(field_type) is Annotated:
        field_type = get_args(field_type)[0]
    return field_type


def _nested_dataclass_type(field_type: TypeAnnotation) -> type[DataclassInstance] | None:
    """Return the single nested dataclass type behind *field_type*, if any.

    Handles a bare dataclass and a ``Union``/``X | None`` with exactly one dataclass member.
    Containers (``list``/``dict``/``tuple``) are deliberately not unwrapped — see module
    docstring.
    """
    stripped = _strip_annotated(field_type)
    if is_dataclass(stripped) and isinstance(stripped, type):
        return stripped

    if get_origin(stripped) is Union or isinstance(stripped, types.UnionType):
        candidates = [
            arg for arg in get_args(stripped) if arg is not type(None) and is_dataclass(arg) and isinstance(arg, type)
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None


_VISITING = object()
"""Sentinel marking a dataclass type currently on the recursion stack, in ``_build_factory_node``'s
*state* dict — distinguishes "still being built" from a finished node (which may legitimately be
``None``, meaning "no unsafe branch")."""


def _build_factory_node(
    dataclass_type: "type[DataclassInstance]",
    state: "dict[type[DataclassInstance], object]",
) -> "FactoryNode | None":
    """Build (or reuse) the pruned node for *dataclass_type*, or ``None`` if it has no unsafe branch.

    *state* doubles as memo and cycle guard: a cycle back to a type already on the current
    recursion path (marked ``_VISITING``) returns ``None`` rather than recursing unboundedly — a
    recursive schema's cycle edge is never itself reachable through an absent-key fallback.
    """
    if dataclass_type in state:
        cached = state[dataclass_type]
        return None if cached is _VISITING else cast("FactoryNode | None", cached)
    state[dataclass_type] = _VISITING

    try:
        hints = get_type_hints(dataclass_type, include_extras=True)
    except (NameError, TypeError, AttributeError):
        hints = {}

    unsafe: list[UnsafeFactoryField] = []
    children: dict[str, FactoryNode] = {}
    for f in fields(dataclass_type):
        if f.default_factory is not MISSING:
            required_params = required_params_of(f.default_factory)
            if required_params is not None:
                factory_name = (
                    getattr(f.default_factory, "__qualname__", None)
                    or getattr(f.default_factory, "__name__", None)
                    or type(f.default_factory).__name__
                )
                unsafe.append(
                    UnsafeFactoryField(name=f.name, factory_name=factory_name, required_params=required_params)
                )

        # Descend regardless of the field's own unsafe-ness: an unsafe field that IS
        # provided (so its own report above doesn't fire) can still have an unsafe
        # default_factory nested further inside it, reachable once the parent key is present.
        field_type = hints.get(f.name)
        if field_type is None:
            continue
        nested = _nested_dataclass_type(field_type)
        if nested is None:
            continue
        child = _build_factory_node(nested, state)
        if child is not None:
            children[f.name] = child

    node = FactoryNode(dc_type=dataclass_type, unsafe=tuple(unsafe), children=children) if unsafe or children else None
    state[dataclass_type] = node
    return node


def unsafe_factory_tree(dataclass_type: "type[DataclassInstance]") -> "FactoryNode | None":
    """Build the tree of *dataclass_type* fields whose ``default_factory`` needs arguments.

    Returns ``None`` when no field anywhere in the schema (recursively) has one — the
    overwhelmingly common case, so callers pay a single ``is None`` check. Callers
    (``RetortCache``) compute this once per schema and store the result, so no caching here.
    """
    return _build_factory_node(dataclass_type, {})


def iter_unsafe_fields(
    node: "FactoryNode | None",
    path: tuple[str, ...] = (),
) -> "list[tuple[tuple[str, ...], UnsafeFactoryField]]":
    """Flatten *node* into every ``(field_path, field)`` pair, regardless of key presence.

    Used by ``dature.loading.field_pass``'s ``enrich_missing_factory_field_errors`` to name the
    factory and its required parameters in an otherwise-plain "Missing required field" error.
    """
    if node is None:
        return []
    result: list[tuple[tuple[str, ...], UnsafeFactoryField]] = [((*path, f.name), f) for f in node.unsafe]
    for name, child in node.children.items():
        result.extend(iter_unsafe_fields(child, (*path, name)))
    return result
