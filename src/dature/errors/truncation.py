"""Cap a dature exception group's sub-exceptions at ``error_display.max_errors``."""

from typing import NoReturn, cast

from dature.config import ErrorDisplayConfig
from dature.errors.exceptions import DatureError, DatureErrorGroup


def _truncate_group[G: DatureErrorGroup](group: G, error_display: ErrorDisplayConfig) -> G:
    """Return *group* capped at ``error_display.max_errors`` sub-exceptions.

    Returns *group* itself, unchanged, when it already fits. Otherwise derives a new
    group from the first ``max_errors`` sub-exceptions and records the remainder as a
    note (``"... and N more <error_noun> (M total)"``) rather than dropping it silently.

    Dature never nests exception groups — every group is one level deep — so this does
    not recurse into sub-exceptions.

    Meant to run once, at the boundary where a load call is about to raise to the
    caller, not at each internal construction site: some groups are rebuilt from their
    leaves on the way there (``enrich_skipped_errors``, ``merge_root_and_field_errors``),
    which would otherwise turn "already truncated" into "true total lost".
    """
    total = len(group.exceptions)
    max_errors = error_display.max_errors
    if total <= max_errors:
        return group

    # Dature never nests groups, so every sub-exception is a leaf DatureError, never
    # itself an ExceptionGroup — the cast reflects that invariant to the type checker.
    shown = cast("list[DatureError]", list(group.exceptions)[:max_errors])
    remaining = total - len(shown)
    truncated = group.derive(shown)
    for note in getattr(group, "__notes__", []):
        truncated.add_note(note)
    truncated.add_note(f"... and {remaining} more {type(group).error_noun} ({total} total)")
    truncated.__cause__ = group.__cause__
    truncated.__traceback__ = group.__traceback__
    return truncated


def raise_truncated(group: DatureErrorGroup, error_display: ErrorDisplayConfig) -> NoReturn:
    """Raise *group*, capped at ``error_display.max_errors`` sub-exceptions, keeping its cause chain.

    A one-line replacement for the ``truncated = truncate_group(...); raise truncated
    from truncated.__cause__`` pattern each load-boundary call site would otherwise
    repeat. Raising here rather than in the caller adds one more dature-internal frame
    to the traceback, which is invisible: ``DatureErrorGroup.__traceback__`` (and
    ``DatureError.__traceback__``) already strip every dature-internal frame, and the
    boundary's own frame is stripped for the same reason regardless of where the final
    ``raise`` statement lives.
    """
    truncated = _truncate_group(group, error_display)
    raise truncated from truncated.__cause__
