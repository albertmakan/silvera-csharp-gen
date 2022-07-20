from silvera.core import TypedList, TypeDef, TypedSet, TypedDict

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
    }
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
