"""Compare a source's raw data against a known-key tree, reporting unknown key paths."""

from dature.loading.strict.known_keys import ElementsNode, Node, ObjectNode
from dature.naming import canonical_name
from dature.protocols import DataclassInstance
from dature.type_aliases import JSONValue


def find_unknown_keys(
    raw: JSONValue,
    node: Node,
    alias_by_type: "dict[type[DataclassInstance], frozenset[str]]",
    path: tuple[str, ...] = (),
) -> list[list[str]]:
    """Return the dotted-path segments of every key in *raw* not covered by *node*.

    A shape mismatch (e.g. a dict expected but a scalar found) is silently ignored —
    that is a coercion error, which the loader itself already reports; strict mode
    only speaks to keys, not types.
    """
    if isinstance(node, ObjectNode):
        return _scan_object(raw, node, alias_by_type, path)
    return _scan_elements(raw, node, alias_by_type, path)


def _scan_object(
    raw: JSONValue,
    node: ObjectNode,
    alias_by_type: "dict[type[DataclassInstance], frozenset[str]]",
    path: tuple[str, ...],
) -> list[list[str]]:
    result: list[list[str]] = []
    if not isinstance(raw, dict):
        return result

    allowed = node.keys | alias_by_type.get(node.dc_type, frozenset())
    for key, value in raw.items():
        canon = canonical_name(key)
        current_path = (*path, key)
        if canon not in allowed:
            result.append(list(current_path))
            continue
        child = node.children.get(canon)
        if child is not None:
            result.extend(find_unknown_keys(value, child, alias_by_type, current_path))
    return result


def _scan_elements(
    raw: JSONValue,
    node: ElementsNode,
    alias_by_type: "dict[type[DataclassInstance], frozenset[str]]",
    path: tuple[str, ...],
) -> list[list[str]]:
    # Keys/indices are arbitrary data here — only the element shape is known.
    result: list[list[str]] = []
    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            result.extend(find_unknown_keys(item, node.element, alias_by_type, (*path, str(idx))))
    elif isinstance(raw, dict):
        for key, value in raw.items():
            result.extend(find_unknown_keys(value, node.element, alias_by_type, (*path, key)))
    return result
