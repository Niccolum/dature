def canonical_name(name: str) -> str:
    """Lowercase *name* and strip ``-``/``_`` so it compares equal across ``NameStyle`` variants.

    Dots are preserved as path separators, so this doubles as a path canonicalizer.
    """
    return name.lower().replace("-", "").replace("_", "")


def segment_offsets(name: str) -> list[int]:
    """Return the offsets where a new name segment starts within *name*.

    A segment starts at index 0, right after a run of ``-``/``_`` (so ``__`` collapses
    to a single boundary), or at an uppercase letter that follows a lowercase letter or
    digit (a camelCase hump). Used to find where a bare field name begins inside a
    prefixed identifier, e.g. ``APP_DB_HOST_TYPO`` contains ``db_host_typo`` starting at
    offset 4.
    """
    offsets = [0]
    for i in range(1, len(name)):
        prev, current = name[i - 1], name[i]
        separator_boundary = current not in "-_" and prev in "-_"
        camel_hump = current.isupper() and (prev.islower() or prev.isdigit())
        if separator_boundary or camel_hump:
            offsets.append(i)
    return offsets
