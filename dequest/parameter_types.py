from typing import Any, Generic, Optional, Protocol, TypeVar

T = TypeVar("T")


class ParameterParser(Protocol):
    @staticmethod
    def parse(params: Any) -> tuple[Optional[type], Optional[str]]: ...


class DictParser:
    @staticmethod
    def parse(params: dict) -> tuple[Optional[type], Optional[str]]:
        return params.get("base_type"), params.get("alias")


class TupleParser:
    @staticmethod
    def parse(params: tuple) -> tuple[Optional[type], Optional[str]]:
        length = len(params)
        if length == 1:
            return (None, params[0]) if isinstance(params[0], str) else (params[0], None)
        if length == 2:  # noqa: PLR2004
            return params
        raise TypeError("Expected at most 2 parameters: base_type and optional alias")


class DefaultParser:
    @staticmethod
    def parse(params: Any) -> tuple[Optional[type], Optional[str]]:
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
    base_type, alias = ParameterParserFactory.get_parser_by_type(type(params)).parse(params)
    new_name = f"{cls.__name__}_{base_type.__name__}" if base_type is not None else cls.__name__
    return type(new_name, (cls,), {"__base_type__": base_type, "__alias__": alias})


class PathParameter(Generic[T]):
    @classmethod
    def __class_getitem__(cls, params: Any):
        return _make_parameter(cls, params)


class QueryParameter(Generic[T]):
    @classmethod
    def __class_getitem__(cls, params: Any):
        return _make_parameter(cls, params)


class FormParameter(Generic[T]):
    @classmethod
    def __class_getitem__(cls, params: Any):
        return _make_parameter(cls, params)


class JsonBody:
    @classmethod
    def __class_getitem__(cls, params: Any):
        return _make_parameter(cls, params)
