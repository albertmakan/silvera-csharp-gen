import warnings

from silvera.core import TypedList, TypeDef, TypedSet, TypedDict, Function

# silvera types
VOID = "void"
STRING = "str"
PASSWORD = "pwd"
FLOAT = "float"
DOUBLE = "double"
BOOL = "bool"
i16 = "i16"
i32 = "i32"
i64 = "i64"
INT = "int"
DATE = "date"
# Collections types
LIST = "list"
SET = "set"
DICT = "dict"

CSHARP = {
    "TYPES": {
        INT: "int",
        i16: "System.Int16",
        i32: "System.Int32",
        i64: "System.Int64",
        FLOAT: "float",
        DOUBLE: "double",
        STRING: "string",
        BOOL: "bool",
        VOID: "void",
        DATE: "System.DateTime",
        PASSWORD: "string"
    },

    "COLLECTIONS": {
        LIST: "System.Collections.Generic.IList",
        SET: "System.Collections.Generic.ISet",
        DICT: "System.Collections.Generic.IDictionary"
    },

    "DEF_RET_VAL": {
        INT: 0,
        i16: 0,
        i32: 0,
        i64: 0,
        FLOAT: 0.0,
        DOUBLE: 0.0,
        STRING: '""',
        PASSWORD: '""',
        BOOL: "false",
        VOID: "",
        DATE: "System.DateTime.Now",
        LIST: "null",
        SET: "null",
        DICT: "null"
    },

    "ASYNC_RET_TYPE": "System.Threading.Tasks.Task"
}


def convert_type(_type):
    """Converts complex silvera object to a c# type"""
    if isinstance(_type, TypeDef):
        return _type.name
    if isinstance(_type, TypedList):
        return f"{CSHARP['COLLECTIONS'][LIST]}<{convert_type(_type.type)}>"
    if isinstance(_type, TypedSet):
        return f"{CSHARP['COLLECTIONS'][SET]}<{convert_type(_type.type)}>"
    if isinstance(_type, TypedDict):
        return f"{CSHARP['COLLECTIONS'][DICT]}<{convert_type(_type.key_type)}, {convert_type(_type.value_type)}>"
    return CSHARP["TYPES"][_type]


def convert_ret_type(func: Function):
    if func.is_async():
        if func.ret_type == VOID:
            return CSHARP['ASYNC_RET_TYPE']
        return f"{CSHARP['ASYNC_RET_TYPE']}<{convert_type(func.ret_type)}>"
    return convert_type(func.ret_type)


def get_default_ret_val(_type):
    return CSHARP["DEF_RET_VAL"][_type]


def get_default_for_cb_pattern(func: Function):
    if func.cb_pattern in ("fallback_method", "fallback_static"):
        return get_default_ret_val(func.ret_type)
    elif func.cb_pattern == "fallback_stubbed":
        if isinstance(func.ret_type, TypeDef):
            return "new()"
        else:
            return get_default_ret_val(func.ret_type)
    elif func.cb_pattern == "fail_silent":
        warnings.warn("Circuit Breaker pattern 'fail_silent' returns "
                      "default value instead of empty response. Sorry :(. ")
        return get_default_ret_val(func.ret_type)
    elif func.cb_pattern == "fallback_cache":
        warnings.warn("Circuit Breaker pattern 'fallback_cache' returns "
                      "default value instead of cached value. Sorry :(. ")
        return get_default_ret_val(func.ret_type)
