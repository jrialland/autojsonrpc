"""
This module contains utilities for converting Python types to JSON and back.
"""

import datetime
import decimal
import json
from typing import Any, Callable
import types
import typing
from dataclasses import is_dataclass

# ------------------------------------------------------------------------------
"""Type mappings for converting specific types to JSON and back.
"""
type_mappings = {
    # datetimes are converted to iso8601 strings
    "datetime.datetime": {
        "python_type": datetime.datetime,
        "js_type": "string",
        "to_dict": lambda x: x.isoformat(),
        "from_dict": lambda x: datetime.datetime.fromisoformat(x),
    },
    # timedeltas are converted to seconds
    "datetime.timedelta": {
        "python_type": datetime.timedelta,
        "ts_type": "number",
        "to_dict": lambda x: x.total_seconds(),
        "from_dict": lambda x: datetime.timedelta(seconds=x),
    },
    # decimals are converted to numbers
    "decimal.Decimal": {
        "python_type": decimal.Decimal,
        "ts_type": "number",
        "to_dict": lambda x: float(x),
        "from_dict": lambda x: decimal.Decimal(x),
    },
}


# ------------------------------------------------------------------------------
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts dataclasses to dictionaries and uses specific mappings for other types."""

    def default(self, obj):

        # if the value is None, return None
        if obj is None:
            return None

        # if the object has a to_dict method, use it
        if hasattr(obj, "to_dict"):
            return {self.default(k): self.default(v) for k, v in obj.to_dict().items()}

        # if the value is a dataclass, convert it to a dictionary
        if is_dataclass(obj.__class__):
            return {
                field: self.default(getattr(obj, field))
                for field in obj.__dataclass_fields__
            }

        # if there is a specific mapping for the type, use it
        for mapping in type_mappings.values():
            if isinstance(obj, mapping["python_type"]):
                return self.default(mapping["to_dict"](obj))

        # if the object is a list/tuple/set, convert its elements
        if isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set):
            return [self.default(value) for value in obj]

        # if the object is a dictionary, convert its values
        if isinstance(obj, dict):
            return {self.default(k): self.default(v) for k, v in obj.items()}

        # return any other object as is
        return obj


# ------------------------------------------------------------------------------
def to_dict(obj: Any) -> dict:
    """Convert an object to a dictionary."""
    return CustomJSONEncoder().default(obj)


# ------------------------------------------------------------------------------
def to_json(obj):
    """Convert an object to a JSON string."""
    return json.dumps(to_dict(obj))


# ------------------------------------------------------------------------------
def convert_arg(arg: Any, python_type: type) -> Any:
    """Read an argument from a JSON-RPC request and convert it to the specified type."""

    # if the expected type is not specified, return the argument as is
    if python_type is None or python_type == Any:
        return arg

    # for typed lists, convert each element to the specified type
    if typing.get_origin(python_type) in (list, tuple, set):
        component_type = typing.get_args(python_type)[0]
        return [convert_arg(value, component_type) for value in arg]

    # same for dictionaries
    if typing.get_origin(python_type) == dict:
        key_type, value_type = typing.get_args(python_type)
        return {
            convert_arg(k, key_type): convert_arg(v, value_type) for k, v in arg.items()
        }

    # if the type is a dataclass, convert the argument to a dataclass
    if is_dataclass(python_type):
        values = {}
        for field_name, field_type in python_type.__dataclass_fields__.items():
            values[field_name] = convert_arg(arg.get(field_name), field_type.type)
        return python_type(**values)

    # if there is a specific mapping for the type, use it
    for mapping in type_mappings.values():
        if python_type == mapping["python_type"]:
            from_dict: Callable = mapping.get("from_dict")  # type: ignore
            return from_dict(arg)

    # by default, return the argument as is
    return arg


# ------------------------------------------------------------------------------
def get_ts_type(python_type: type, is_return_type: bool) -> str:
    """for a given python type, return the corresponding typescript type."""

    if type(python_type) == typing._GenericAlias:
        origin = typing.get_origin(python_type)
        if origin in (list, set, tuple):
            return get_ts_type(typing.get_args(python_type)[0], is_return_type) + "[]"
        elif origin == dict:
            return (
                "{[key: "
                + get_ts_type(typing.get_args(python_type)[0], is_return_type)
                + "]: "
                + get_ts_type(typing.get_args(python_type)[1], is_return_type)
                + "}"
            )

    elif type(python_type) == types.GenericAlias:
        origin = python_type.__origin__
        if origin in (list, set, tuple):
            return get_ts_type(python_type.__args__[0], is_return_type) + "[]"
        elif origin == dict:
            return (
                "{[key: "
                + get_ts_type(python_type.__args__[0], is_return_type)
                + "]: "
                + get_ts_type(python_type.__args__[1], is_return_type)
                + "}"
            )

    elif typing.get_origin(python_type) == typing.Union:
        return " | ".join(
            get_ts_type(arg, is_return_type) for arg in typing.get_args(python_type)
        )

    if python_type is None:
        return "void" if is_return_type else "any"
    elif python_type in (int, float):
        return "number"
    elif python_type == str:
        return "string"
    elif python_type == bool:
        return "boolean"
    elif python_type in (list, tuple, set):
        return "any[]"
    elif python_type == dict:
        return "{[key: any]: any}"
    elif is_dataclass(python_type):
        return python_type.__name__
    else:
        # if this is a known mapping, return the corresponding typescript type
        for mapping in type_mappings.values():
            if python_type == mapping["python_type"]:
                return str(mapping.get("ts_type", "any"))

    # by default, when we cannot determine the type, return 'any'
    return "any"


# ------------------------------------------------------------------------------
def get_python_name(python_type: type, is_return_type: bool):
    """for a given python type, return the corresponding python type name."""
    if python_type is None:
        return "None" if is_return_type else "Any"
    if "__name__" in dir(python_type):
        return python_type.__name__
    else:
        mapping = {
            int: "int",
            float: "float",
            str: "str",
            bool: "bool",
            list: "list",
            tuple: "tuple",
            set: "set",
            dict: "dict",
        }
        if python_type in mapping:
            return mapping[python_type]
        return 'None' if is_return_type else 'Any'

def get_php_name(python_type, is_return_type: bool):
    """for a given python type, return the corresponding php type name."""
    pyname = get_python_name(python_type, is_return_type)
    if pyname in ('list', 'tuple', 'set', 'dict'):
        return 'array'
    if pyname == 'str':
        return 'string'
    if pyname == 'None':
        return 'mixed' if is_return_type else 'null'
