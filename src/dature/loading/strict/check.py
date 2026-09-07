"""Orchestration and reporting for strict-mode unknown-key detection."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, is_dataclass

from dature.errors.exceptions import StrictModeError, UnknownKeyError
from dature.errors.location import ErrorContext, SourceContext, resolve_source_location
from dature.loading.strict.known_keys import alias_keys_by_type, known_key_tree
from dature.loading.strict.scan import find_unknown_keys
from dature.protocols import DataclassInstance
from dature.type_aliases import JSONValue, StrictMode

logger = logging.getLogger("dature")


@dataclass(frozen=True, slots=True)
class StrictSourceEntry:
    """One successfully-loaded source's contribution, as seen by the strict check."""

    raw: JSONValue
    error_ctx: ErrorContext
    file_content: str | None

    @classmethod
    def from_source_context(cls, raw: JSONValue, ctx: SourceContext) -> "StrictSourceEntry":
        """Build an entry from a merge pass's ``SourceContext``.

        Not a plain alias — ``SourceContext.loaded_data`` is the source's data *before*
        prefix stripping, while strict mode needs *raw*, the post-prefix dict actually
        compared against the schema's known-key tree.
        """
        return cls(raw=raw, error_ctx=ctx.error_ctx, file_content=ctx.file_content)


def run_strict_check(
    *,
    schema: "type[DataclassInstance]",
    entries: Sequence[StrictSourceEntry],
) -> None:
    """Report keys in *entries* that map to no field in *schema*, per source ``strict`` mode.

    Runs after a successful load — a real coercion/validation failure always surfaces
    before any "unknown key" report. Each entry's own ``error_ctx.source.strict`` decides
    its handling: ``"off"``/``None`` skips the source entirely, ``"warn"`` logs each unknown
    key, ``"error"`` collects them for a single :class:`StrictModeError` (one per *schema*,
    covering every ``"error"``-mode entry). ``"warn"`` output is capped at
    ``error_display.max_errors`` entries here, since a log line is never revisited. The
    ``"error"`` group is raised whole — capping it happens once, at the load boundary
    (``Loader.load()`` / decorator revalidation), where ``raise_truncated`` runs regardless
    of which kind of group is raised.
    """
    if not is_dataclass(schema):
        return

    tree = known_key_tree(schema)
    warn_errors: list[UnknownKeyError] = []
    raise_errors: list[UnknownKeyError] = []

    for entry in entries:
        source = entry.error_ctx.source
        mode: StrictMode = source.strict if source.strict is not None else "off"
        if mode == "off":
            continue

        alias_by_type = alias_keys_by_type(source.field_mapping)
        for field_path in find_unknown_keys(entry.raw, tree, alias_by_type):
            locations = resolve_source_location(
                field_path,
                entry.error_ctx,
                entry.file_content,
                caret_key=field_path[-1],
            )
            error = UnknownKeyError(
                field_path=field_path,
                source_repr=repr(source),
                locations=locations,
                error_display=entry.error_ctx.error_display,
            )
            (warn_errors if mode == "warn" else raise_errors).append(error)

    if warn_errors:
        max_errors = warn_errors[0].error_display.max_errors
        shown, remaining = warn_errors[:max_errors], len(warn_errors) - max_errors
        for error in shown:
            logger.warning("[%s] %s", schema.__name__, str(error))
        if remaining > 0:
            logger.warning(
                "[%s] ... and %d more %s (%d total)",
                schema.__name__,
                remaining,
                StrictModeError.error_noun,
                len(warn_errors),
            )

    if raise_errors:
        raise StrictModeError(schema.__name__, raise_errors)
