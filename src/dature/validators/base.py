from typing import Annotated, get_args, get_origin

from adaptix import P, validator
from adaptix.provider import Provider

from dature.protocols import ValidatorProtocol


def extract_validators_from_type(field_type: object) -> list[ValidatorProtocol]:
    validators: list[ValidatorProtocol] = []

    if get_origin(field_type) is not Annotated:
        return validators

    args = get_args(field_type)

    validators.extend(arg for arg in args[1:] if hasattr(arg, "__dataclass_fields__"))

    return validators


def create_validator_providers(
    dataclass_: type,
    field_name: str,
    validators: list[ValidatorProtocol],
) -> list[Provider]:
    providers = []

    for v in validators:
        func = v.get_validator_func()
        error = v.get_error_message()
        provider = validator(
            P[dataclass_][field_name],
            func,
            error,
        )
        providers.append(provider)

    return providers


def create_root_validator_providers(
    dataclass_: type,
    root_validators: tuple[ValidatorProtocol, ...],
) -> list[Provider]:
    providers = []

    for root_validator in root_validators:
        provider = validator(
            P[dataclass_],
            root_validator.get_validator_func(),
            root_validator.get_error_message(),
        )
        providers.append(provider)

    return providers
