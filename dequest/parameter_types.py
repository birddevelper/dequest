import warnings
from typing import Any, Generic, Protocol, TypeVar

T = TypeVar("T")


class ParameterParser(Protocol):
    @staticmethod
    def parse(params: Any) -> tuple[type | None, str | None]: ...


class DictParser:
    @staticmethod
    def parse(params: dict) -> tuple[type | None, str | None]:
        return params.get("base_type"), params.get("alias")


class TupleParser:
    @staticmethod
    def parse(params: tuple) -> tuple[type | None, str | None]:
        length = len(params)
        if length == 1:
            return (None, params[0]) if isinstance(params[0], str) else (params[0], None)
        if length == 2:  # noqa: PLR2004
            return params
        raise TypeError("Expected at most 2 parameters: base_type and optional alias")


class DefaultParser:
    @staticmethod
    def parse(params: Any) -> tuple[type | None, str | None]:
        return (None, params) if isinstance(params, str) else (params, None)


class ParameterParserFactory:
    _parsers = {
        dict: DictParser(),
        tuple: TupleParser(),
    }

    @classmethod
    def get_parser_by_type(cls, params_type: Any) -> ParameterParser:
        return cls._parsers.get(params_type, DefaultParser())


def _make_parameter(cls: type, params: Any) -> type:
    base_type, alias = ParameterParserFactory.get_parser_by_type(type(params)).parse(
        params,
    )
    new_name = f"{cls.__name__}_{base_type.__name__}" if base_type is not None else cls.__name__
    return type(new_name, (cls,), {"__base_type__": base_type, "__alias__": alias})


class _ParameterUnset:
    def __repr__(self) -> str:
        return "ParameterUnset"


PARAMETER_UNSET = _ParameterUnset()


class ParameterDefinition:
    __base_type__ = None
    __alias__ = None

    def __init__(self, default: Any = PARAMETER_UNSET, alias: str | None = None):
        self.default = default
        self.alias = alias

    @classmethod
    def __class_getitem__(cls, params: Any):
        warnings.warn(
            (
                f"`{cls.__name__}[...]` subscription style is deprecated and will be removed "
                f"in a future release. Use a standard annotation with a parameter marker "
                f'default instead, for example: `param: str = {cls.__name__}(alias="...")`.'
            ),
            FutureWarning,
            stacklevel=2,
        )
        return _make_parameter(cls, params)


class PathParameter(ParameterDefinition, Generic[T]):
    pass


class QueryParameter(ParameterDefinition, Generic[T]):
    pass


class FormParameter(ParameterDefinition, Generic[T]):
    pass


class FileParameter(ParameterDefinition):
    pass


class JsonBody(ParameterDefinition):
    pass
