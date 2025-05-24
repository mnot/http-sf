import base64
from datetime import datetime
from decimal import Decimal
import json
from string import ascii_lowercase, ascii_uppercase, digits
from typing import Tuple, Any, Union

from .types import StructuredType, Token, DisplayString

SPACE = ord(b" ")
HTTP_OWS = set(b" \t")


def discard_ows(data: bytes) -> int:
    "Return the number of space characters at the beginning of data."
    i = 0
    ln = len(data)
    while True:
        if i == ln or data[i] != SPACE:
            return i
        i += 1


def discard_http_ows(data: bytes) -> int:
    "Return the number of space or HTAB characters at the beginning of data."
    i = 0
    ln = len(data)
    while True:
        if i == ln or data[i] not in HTTP_OWS:
            return i
        i += 1


KEY_START_CHARS = set((ascii_lowercase + "*").encode("ascii"))
KEY_CHARS = set((ascii_lowercase + digits + "_-*.").encode("ascii"))
UPPER_CHARS = set((ascii_uppercase).encode("ascii"))
COMPAT = False


def parse_key(data: bytes) -> Tuple[int, str]:
    if data == b"" or data[0] not in KEY_START_CHARS:
        if data == b"" or not (COMPAT and data[0] in UPPER_CHARS):
            raise ValueError("Key does not begin with lcalpha or *")
    bytes_consumed = 1
    while bytes_consumed < len(data):
        if data[bytes_consumed] not in KEY_CHARS:
            if not (COMPAT and data[bytes_consumed] in UPPER_CHARS):
                return bytes_consumed, data[:bytes_consumed].decode("ascii").lower()
        bytes_consumed += 1
    return bytes_consumed, data.decode("ascii").lower()


def ser_key(key: str) -> str:
    if len(key) == 0:
        raise ValueError("Zero length key")
    if not all(ord(char) in KEY_CHARS for char in key):
        raise ValueError("Key contains disallowed characters")
    if ord(key[0]) not in KEY_START_CHARS:
        raise ValueError("Key does not start with allowed character")
    return key


def to_json(structure: StructuredType, **args: Any) -> str:
    return json.dumps(structure, default=json_dump, **args)


def from_json(instr: str) -> StructuredType:
    raw_suite = json.loads(instr, parse_float=Decimal, object_hook=json_load)
    suite = []
    for test in raw_suite:
        if "expected" in test:
            test["expected"] = adjust_field_json(test["expected"], test["header_type"])
        suite.append(test)
    return suite


def json_dump(inobj: Any) -> Union[Any, dict]:
    if isinstance(inobj, Token):
        return {"__type": "token", "value": str(inobj)}
    if isinstance(inobj, bytes):
        return {"__type": "binary", "value": base64.b32encode(inobj).decode("ascii")}
    if isinstance(inobj, datetime):
        return {"__type": "date", "value": inobj.timestamp()}
    if isinstance(inobj, DisplayString):
        return {"__type": "displaystring", "value": str(inobj)}
    if isinstance(inobj, Decimal):
        return float(inobj)
    raise ValueError(f"Unknown object type - {inobj}")


def json_load(inobj: dict) -> Any:
    objtype = inobj.get("__type", None)
    if not objtype:
        return inobj
    if objtype == "token":
        return Token(inobj["value"])
    if objtype == "binary":
        return base64.b32decode(inobj["value"])
    if objtype == "date":
        return datetime.fromtimestamp(inobj["value"])
    if objtype == "displaystring":
        return DisplayString(inobj["value"])
    raise ValueError(f"Unknown object type - {inobj}")


def adjust_field_json(field: Any, header_type: str) -> Any:
    if header_type == "dictionary":
        return {k: adjust(v) for k, v in field}
    if header_type == "list":
        return [adjust(i) for i in field]
    if header_type == "item":
        return adjust(field)
    raise ValueError(f"Unknown header_type: {header_type}")


def adjust(thing: Any) -> Any:
    if isinstance(thing, list) and len(thing) == 2:
        thing = (thing[0], thing[1])
        if isinstance(thing[0], list):
            thing = ([adjust(i) for i in thing[0]], thing[1])
        if isinstance(thing[1], list):
            thing = (thing[0], dict([adjust((k, v)) for k, v in thing[1]]))
    return thing
