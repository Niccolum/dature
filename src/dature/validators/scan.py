from dataclasses import fields
from typing import cast, get_type_hints

from adaptix.provider import Provider

from dature.protocols import DataclassInstance
from dature.type_utils import find_nested_dataclasses
from dature.validators.base import create_validator_providers, extract_and_check_validators


def scan_validators[T](schema: type[T], *, _seen: "set[type] | None" = None) -> tuple[list[Provider], frozenset[type]]:
    """Walk *schema* once, returning both validator providers and validator target types.

    ``get_validator_providers`` and ``validator_target_dataclass_types`` need the exact same
    walk (``get_type_hints``, ``extract_and_check_validators``, ``find_nested_dataclasses``);
    ``RetortCache`` needs both results, so it calls this combined walk directly instead of
    walking the schema tree twice through the two single-purpose functions below. ``_seen``
    guards against unbounded recursion on self-referential/mutually-recursive dataclasses (e.g.
    ``child: "Node | None"``) — such a schema has no validators past the cycle, so revisiting it
    would only repeat work forever, never find anything new.
    """
    seen = _seen if _seen is not None else set()
    if schema in seen:
        return [], frozenset()
    seen.add(schema)

    providers: list[Provider] = []
    targets: set[type] = set()
    type_hints = get_type_hints(schema, include_extras=True)

    for field in fields(cast("type[DataclassInstance]", schema)):
        if field.name not in type_hints:
            continue

        field_type = type_hints[field.name]
        validators_list = extract_and_check_validators(field_type, field_path=[field.name])
        nested = find_nested_dataclasses(field_type)

        if validators_list:
            providers.extend(create_validator_providers(schema, field.name, validators_list))
            targets.update(nested)

        for nested_dataclass in nested:
            nested_providers, nested_targets = scan_validators(nested_dataclass, _seen=seen)
            providers.extend(nested_providers)
            targets.update(nested_targets)

    return providers, frozenset(targets)


def get_validator_providers[T](schema: type[T]) -> list[Provider]:
    """Return adaptix ``Provider`` instances for every ``Annotated`` field validator in *schema*.

    Recurses into nested dataclasses so validators on nested fields are also registered.
    """
    providers, _ = scan_validators(schema)
    return providers


def validator_target_dataclass_types[T](schema: type[T]) -> frozenset[type]:
    """Return every nested dataclass type a field validator is directly attached to, in *schema*.

    A field annotated ``Annotated[NestedDC, V.check(...)]`` or ``Annotated[list[NestedDC],
    V.each(...)]`` needs ``NestedDC`` loaded as a real instance, not a plain dict, so its
    validator can run. Used by ``RetortCache`` to compute which types ``ModelToDictProvider``
    must NOT convert to dicts during the field pass.
    """
    _, targets = scan_validators(schema)
    return targets
