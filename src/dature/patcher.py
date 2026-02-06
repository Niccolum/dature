from collections.abc import Callable
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

from dature.sources_loader.base import ILoader
from dature.validators.base import DataclassInstance


def _merge_fields(
    loaded_data: Any,  # noqa: ANN401
    field_list: tuple[Any, ...],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    explicit_fields = set(kwargs.keys())
    for i, _ in enumerate(args):
        if i < len(field_list):
            explicit_fields.add(field_list[i].name)

    complete_kwargs = dict(kwargs)
    for field in field_list:
        if field.name not in explicit_fields:
            complete_kwargs[field.name] = getattr(loaded_data, field.name)

    return complete_kwargs


def _ensure_retort(loader_instance: ILoader, cls: type) -> None:
    """Создаёт retort до замены __init__, чтобы adaptix видел оригинальную сигнатуру."""
    if cls not in loader_instance._retorts:  # noqa: SLF001
        loader_instance._retorts[cls] = loader_instance._create_retort()  # noqa: SLF001
    loader_instance._retorts[cls].get_loader(cls)  # noqa: SLF001


class _PatchContext:
    def __init__(
        self,
        loader_instance: ILoader,
        file_path: Path,
        cls: type[DataclassInstance],
    ) -> None:
        _ensure_retort(loader_instance, cls)
        validating_retort = loader_instance._create_validating_retort(cls)  # noqa: SLF001

        self.loader_instance = loader_instance
        self.file_path = file_path
        self.cls = cls
        self.field_list = fields(cls)  # type: ignore[arg-type]
        self.original_init = cls.__init__
        self.original_post_init = getattr(cls, "__post_init__", None)
        self.validation_loader = validating_retort.get_loader(cls)
        self.validating = False
        self.loading = False


def _make_new_init(ctx: _PatchContext) -> Callable[..., None]:
    def new_init(self: DataclassInstance, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        if ctx.loading:
            ctx.original_init(self, *args, **kwargs)
            return

        ctx.loading = True
        try:
            loaded_data: Any = ctx.loader_instance.load(ctx.file_path, ctx.cls)
        finally:
            ctx.loading = False

        complete_kwargs = _merge_fields(loaded_data, ctx.field_list, args, kwargs)
        ctx.original_init(self, *args, **complete_kwargs)

        if ctx.original_post_init is None:
            self.__post_init__()  # type: ignore[attr-defined]

    return new_init


def _make_new_post_init(ctx: _PatchContext) -> Callable[..., None]:
    def new_post_init(self: DataclassInstance) -> None:
        if ctx.loading:
            return

        if ctx.validating:
            return

        if ctx.original_post_init is not None:
            ctx.original_post_init(self)

        ctx.validating = True
        try:
            obj_dict = asdict(self)  # type: ignore[call-overload]
            ctx.validation_loader(obj_dict)
        finally:
            ctx.validating = False

    return new_post_init


def load_as_function(
    loader_instance: ILoader,
    file_path: Path,
    dataclass_: type[DataclassInstance],
) -> DataclassInstance:
    validating_retort = loader_instance._create_validating_retort(dataclass_)  # noqa: SLF001
    validation_loader = validating_retort.get_loader(dataclass_)
    result = loader_instance.load(file_path, dataclass_)
    result_dict = asdict(result)  # type: ignore[call-overload]
    validation_loader(result_dict)
    return result


def make_decorator(
    loader_instance: ILoader,
    file_path: Path,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]:
    def decorator(cls: type[DataclassInstance]) -> type[DataclassInstance]:
        if not is_dataclass(cls):
            msg = f"{cls.__name__} must be a dataclass"
            raise TypeError(msg)

        ctx = _PatchContext(loader_instance, file_path, cls)
        cls.__init__ = _make_new_init(ctx)
        cls.__post_init__ = _make_new_post_init(ctx)
        return cls

    return decorator
