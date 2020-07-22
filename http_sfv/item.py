from decimal import Decimal
from typing import Any, List, Union

from .boolean import parse_boolean, ser_boolean
from .byteseq import parse_byteseq, ser_byteseq, BYTE_DELIMIT
from .decimal import ser_decimal
from .integer import parse_number, ser_integer, NUMBER_START_CHARS
from .string import parse_string, ser_string, DQUOTE
from .token import parse_token, ser_token, Token, TOKEN_START_CHARS
from .util import StructuredFieldValue, remove_char, discard_ows, parse_key, ser_key
from .util_json import value_to_json, value_from_json


class Item(StructuredFieldValue):
    def __init__(self, value: Any = None) -> None:
        StructuredFieldValue.__init__(self)
        self.value = value
        self.params = Parameters()

    def parse_content(self, input_string: str) -> str:
        input_string, self.value = parse_bare_item(input_string)
        return self.params.parse(input_string)

    def __str__(self) -> str:
        output = ""
        output += ser_bare_item(self.value)
        output += str(self.params)
        return output

    def to_json(self) -> Any:
        value = value_to_json(self.value)
        return [value, self.params.to_json()]

    def from_json(self, json_data: Any) -> None:
        try:
            value, params = json_data
        except ValueError:
            raise ValueError(json_data)
        self.value = value_from_json(value)
        self.params.from_json(params)


class Parameters(dict):
    def parse(self, input_string: str) -> str:
        while input_string:
            if input_string[0] != ";":
                break
            input_string, _ = remove_char(input_string)
            input_string = discard_ows(input_string)
            input_string, param_name = parse_key(input_string)
            param_value = True
            if input_string and input_string[0] == "=":
                input_string, _ = remove_char(input_string)
                input_string, param_value = parse_bare_item(input_string)
            self[param_name] = param_value
        return input_string

    def __str__(self) -> str:
        output = ""
        for param_name in self:
            output += ";"
            output += ser_key(param_name)
            if self[param_name] is not True:
                output += "="
                output += ser_bare_item(self[param_name])
        return output

    def to_json(self) -> Any:
        return {k: value_to_json(v) for (k, v) in self.items()}

    def from_json(self, json_data: Any) -> None:
        for name, value in json_data.items():
            self[name] = value_from_json(value)


class InnerList(list):
    def __init__(self, values: list = None) -> None:
        list.__init__(self, [itemise(v) for v in values or []])
        self.params = Parameters()

    def parse(self, input_string: str) -> str:
        input_string, char = remove_char(input_string)
        if char != "(":
            raise ValueError(
                f"First character of inner list is not '(' at: {input_string[:10]}"
            )
        while input_string:
            input_string = discard_ows(input_string)
            if input_string and input_string[0] == ")":
                input_string = input_string[1:]
                return self.params.parse(input_string)
            item = Item()
            input_string = item.parse_content(input_string)
            self.append(item)
            if not (input_string and input_string[0] in set(" )")):
                raise ValueError(f"Inner list bad delimitation at: {input_string[:10]}")
        raise ValueError(f"End of inner list not found at: {input_string[:10]}")

    def __str__(self) -> str:
        output = "("
        count = len(self)
        for x in range(0, count):
            output += str(self[x])
            if x + 1 < count:
                output += " "
        output += ")"
        output += str(self.params)
        return output

    def to_json(self) -> Any:
        return [[i.to_json() for i in self], self.params.to_json()]

    def from_json(self, json_data: Any) -> None:
        try:
            values, params = json_data
        except ValueError:
            raise ValueError(json_data)
        for i in values:
            self.append(Item())
            self[-1].from_json(i)
        self.params.from_json(params)


def parse_bare_item(input_string: str) -> Any:
    if not input_string:
        raise ValueError("Empty item.", input_string)
    start_char = input_string[0]
    if start_char in TOKEN_START_CHARS:
        return parse_token(input_string)
    if start_char is DQUOTE:
        return parse_string(input_string)
    if start_char in NUMBER_START_CHARS:
        return parse_number(input_string)
    if start_char is BYTE_DELIMIT:
        return parse_byteseq(input_string)
    if start_char == "?":
        return parse_boolean(input_string)
    raise ValueError(
        f"Item starting with '{input_string[0]}' can't be identified at: {input_string[:10]}"
    )


def ser_bare_item(item: Any) -> str:
    item_type = type(item)
    if item_type is int:
        return ser_integer(item)
    if isinstance(item, (Decimal, float)):
        return ser_decimal(item)
    if isinstance(item, Token):
        return ser_token(item)
    if item_type is str:
        return ser_string(item)
    if item_type is bool:
        return ser_boolean(item)
    if item_type is bytes:
        return ser_byteseq(item)
    raise ValueError(f"Can't serialise; unrecognised item with type {item_type}")


def itemise(thing: Any) -> Union[InnerList, Item]:
    if isinstance(thing, (Item, InnerList)):
        return thing
    if isinstance(thing, list):
        return InnerList(thing)
    return Item(thing)
