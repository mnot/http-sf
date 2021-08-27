from decimal import Decimal
from typing import Tuple, Union

from .decimal import FRAC_DIGITS, PRECISION
from .dictionary import Dictionary
from .item import Parameters, InnerList, Item
from .list import List
from .token import Token
from .types import BareItemType
from .util import StructuredFieldValue


"""
Each structure has a one-byte header, whose bits are:

|ttttxxxx|

- The first four `t` bits indicate the type of the structure. Each type has a specific payload
- The last four `x` bits are available for the structure's use
Each structure is self-delimiting.
"""

# FIXME: value content validation

HEADER_BITS = 4
HEADER_MASK = 0b00001111


def parse_binary(data: bytes) -> Tuple[int, StructuredFieldValue]:
    try:
        return _top_level_parsers[data[0] >> HEADER_BITS](data)  # type: ignore
    except KeyError:
        return parse_item(data)


def ser_binary(structure: StructuredFieldValue) -> bytearray:
    structure_type = structure.__class__
    try:
        return _top_level_serialisers[structure_type][1](structure)  # type: ignore
    except KeyError:
        return _serialisers[structure_type][1](structure)  # type: ignore


def parse_item_or_inner_list(data: bytes) -> Tuple[int, Union[InnerList, Item]]:
    try:
        return _item_or_inner_list_parsers[data[0] >> HEADER_BITS](data)  # type: ignore
    except KeyError:
        raise


def ser_item_or_inner_list(structure: Union[InnerList, Item]) -> bytearray:
    pass


def parse_bare_item(data: bytes) -> Tuple[int, BareItemType]:
    try:
        return _bare_item_parsers[data[0] >> HEADER_BITS](data)  # type: ignore
    except KeyError:
        raise


def ser_bare_item(item: BareItemType) -> bytearray:
    pass


def parse_item(data: bytes) -> Tuple[int, Item]:
    item = Item()
    bytes_consumed, item.value = parse_bare_item(data)
    # FIXME: flag for params
    offset, item.params = parse_parameters(data[bytes_consumed:])
    return bytes_consumed + offset, item


def ser_item(item: Item) -> bytearray:
    structure_type = item.__class__
    return _serialisers[structure_type][1](item)  # type: ignore


def parse_integer(data: bytes) -> Tuple[int, int]:
    """
    Payload: Integer i
    """
    return _decode_integer(HEADER_BITS, data)


def ser_integer(value: int) -> bytearray:
    data = _encode_integer(HEADER_BITS + 1, value)
    data = add_type(data, INTEGER)
    ## TODO: add sign
    return data


def parse_decimal(data: bytes) -> Tuple[int, Decimal]:
    """
    Payload: Integer i, Integer f - indicating the integer and fractional components in use
    """
    bytes_consumed, integer_component = _decode_integer(HEADER_BITS, data)
    offset, fractional_component = _decode_integer(0, data[bytes_consumed:])
    return bytes_consumed + offset, Decimal()  # FIXME


def ser_decimal(value: Decimal) -> bytearray:
    input_decimal = round(value, FRAC_DIGITS)
    abs_decimal = value.copy_abs()
    integer_component_s = str(int(abs_decimal))
    fractional_component = abs_decimal.quantize(PRECISION).normalize() % 1
    data = _encode_integer(integer_component, HEADER_BITS)
    data = add_type(data, DECIMAL)
    data += _encode_integer(fractional_component, 0)
    return data


def parse_boolean(data: bytes) -> Tuple[int, bool]:
    """
    Payload: Integer l, b000 remaining bits, b indicating the Boolean value
    """
    return 1, (data[0] & 0b00010000) > 0


def ser_boolean(value: bool) -> bytearray:
    pass


def parse_byteseq(data: bytes) -> Tuple[int, bytes]:
    """
    Payload: Integer l, l bytes of content
    """
    bytes_consumed, length = _decode_integer(HEADER_BITS, data)
    end = bytes_consumed + length
    return end, data[bytes_consumed:end]


def ser_byteseq(value: bytes) -> bytearray:
    pass


def parse_string(data: bytes) -> Tuple[int, str]:
    """
    Payload: Integer l, l bytes of content
    """
    bytes_consumed, length = _decode_integer(HEADER_BITS, data)
    end = bytes_consumed + length
    return end, data[bytes_consumed:end].decode("ascii")


def ser_string(value: str) -> bytearray:
    pass


def parse_token(data: bytes) -> Tuple[int, Token]:
    """
    Payload: Integer l, l bytes of content
    """
    bytes_consumed, length = _decode_integer(HEADER_BITS, data)
    end = bytes_consumed + length
    return end, Token(data[bytes_consumed:end].decode("ascii"))


def ser_token(value: Token) -> bytearray:
    pass


def parse_list(data: bytes) -> Tuple[int, List]:
    """
    Payload: Integer l, l items or inner lists following
    """
    output = List()
    bytes_consumed, members = _decode_integer(HEADER_BITS, data)
    for i in range(members):
        offset, member = parse_item_or_inner_list(data[bytes_consumed:])
        bytes_consumed += offset
        output.append(member)
    return bytes_consumed, output


def ser_list(value: List) -> bytearray:
    pass


def parse_dictionary(data: bytes) -> Tuple[int, Dictionary]:
    """
    Payload: Integer num, num x (Integer keyLen, structure) pairs
    """
    output = Dictionary()
    bytes_consumed, members = _decode_integer(HEADER_BITS, data)
    for i in range(members):
        offset, keyLength = _decode_integer(0, data[bytes_consumed:])
        bytes_consumed += offset
        key_end = bytes_consumed + offset
        name = data[bytes_consumed:key_end].decode("ascii")
        bytes_consumed = key_end
        offset, value = parse_item_or_inner_list(data[bytes_consumed:])
        bytes_consumed += offset
        output[name] = value
    # FIXME: Parameters
    return bytes_consumed, output


def ser_dictionary(value: Dictionary) -> bytearray:
    pass


def parse_inner_list(data: bytes) -> Tuple[int, InnerList]:
    """
    Payload: Integer l, l items following
    """
    output = InnerList()
    bytes_consumed, members = _decode_integer(HEADER_BITS, data)
    for i in range(members):
        offset, member = parse_item(data[bytes_consumed:])
        bytes_consumed += offset
        output.append(member)
    # FIXME: parameters
    return bytes_consumed, output


def ser_inner_list(value: InnerList) -> bytearray:
    pass


def parse_parameters(data: bytes) -> Tuple[int, Parameters]:
    """
    Payload: Integer num, item, num x (Integer keyLen, structure) pairs
    """
    output = Parameters()
    bytes_consumed, members = _decode_integer(HEADER_BITS, data)
    for i in range(members):
        offset, keyLength = _decode_integer(0, data[bytes_consumed:])
        bytes_consumed += offset
        key_end = bytes_consumed + offset
        name = data[bytes_consumed:key_end].decode("ascii")
        bytes_consumed = key_end
        offset, value = parse_bare_item(data[bytes_consumed:])
        bytes_consumed += offset
        output[name] = value
    return bytes_consumed, output


def ser_parameters(value: Parameters) -> bytearray:
    pass


def add_type(data: bytearray, sf_type: int) -> bytearray:
    data[0] = (sf_type << HEADER_BITS) | data[0]
    return data


DICTIONARY = 1
LIST = 2
INNER_LIST = 3
INTEGER = 4
DECIMAL = 5
BOOLEAN = 6
BYTESEQ = 7
STRING = 8
TOKEN = 9


_top_level_parsers = {DICTIONARY: parse_dictionary, LIST: parse_list}
_item_or_inner_list_parsers = {
    INNER_LIST: parse_inner_list,
    INTEGER: parse_integer,
    DECIMAL: parse_decimal,
    BOOLEAN: parse_boolean,
    BYTESEQ: parse_byteseq,
    STRING: parse_string,
    TOKEN: parse_token,
}
_bare_item_parsers = {
    INTEGER: parse_integer,
    DECIMAL: parse_decimal,
    BOOLEAN: parse_boolean,
    BYTESEQ: parse_byteseq,
    STRING: parse_string,
    TOKEN: parse_token,
}

_top_level_serialisers = {
    Dictionary: (DICTIONARY, ser_dictionary),
    List: (LIST, ser_list)
}
_serialisers = {
    InnerList: (INNER_LIST, ser_inner_list),
    int: (INTEGER, ser_integer),
    Decimal: (DECIMAL, ser_decimal),
    bool: (BOOLEAN, ser_boolean),
    bytes: (BYTESEQ, ser_byteseq),
    str: (STRING, ser_string),
    Token: (TOKEN, ser_token),
}


#### From hyper hpack

# Precompute 2^i for 1-8 for use in prefix calcs.
# Zero index is not used but there to save a subtraction
# as prefix numbers are not zero indexed.
_PREFIX_BIT_MAX_NUMBERS = [(2 ** i) - 1 for i in range(9)]


def _decode_integer(prefix_bits: int, data: bytes) -> Tuple[int, int]:
    """
    This decodes an integer according to the wacky integer encoding rules
    defined in the HPACK spec. Returns a tuple of the decoded integer and the
    number of bytes that were consumed from ``data`` in order to get that
    integer.
    """
    if prefix_bits < 1 or prefix_bits > 8:
        raise ValueError("Prefix bits must be between 1 and 8, got %s" % prefix_bits)

    max_number = _PREFIX_BIT_MAX_NUMBERS[prefix_bits]
    index = 1
    shift = 0
    mask = 0xFF >> (8 - prefix_bits)

    try:
        number = data[0] & mask
        if number == max_number:
            while True:
                next_byte = data[index]
                index += 1

                if next_byte >= 128:
                    number += (next_byte - 128) << shift
                else:
                    number += next_byte << shift
                    break
                shift += 7

    except IndexError:
        raise ValueError("Unable to decode HPACK integer representation from %r" % data)

    return index, number


def _encode_integer(integer: int, prefix_bits: int) -> bytearray:
    """
    This encodes an integer according to the wacky integer encoding rules
    defined in the HPACK spec.
    """

    if integer < 0:
        raise ValueError("Can only encode positive integers, got %s" % integer)

    if prefix_bits < 1 or prefix_bits > 8:
        raise ValueError("Prefix bits must be between 1 and 8, got %s" % prefix_bits)

    max_number = _PREFIX_BIT_MAX_NUMBERS[prefix_bits]

    if integer < max_number:
        return bytearray([integer])  # Seriously?
    else:
        elements = [max_number]
        integer -= max_number

        while integer >= 128:
            elements.append((integer & 127) + 128)
            integer >>= 7

        elements.append(integer)

        return bytearray(elements)
