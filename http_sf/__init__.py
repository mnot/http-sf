#!/usr/bin/env python

"Structured HTTP Field Values"

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) Mark Nottingham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

__version__ = "1.1.0"

from typing import Tuple, List, Dict, Optional, Callable

from http_sf.dictionary import parse_dictionary, ser_dictionary
from http_sf.item import parse_item, ser_item
from http_sf.list import parse_list, ser_list
from http_sf.retrofit import retrofit
from http_sf.types import StructuredType, Token, DisplayString, OnDuplicateKeyType
from http_sf.util import discard_ows


from http_sf.state import ParserState
from http_sf.errors import StructuredFieldError


def parse(
    value: bytes,
    name: Optional[str] = None,
    tltype: Optional[str] = None,
    on_duplicate_key: Optional[OnDuplicateKeyType] = None,
) -> StructuredType:
    structure: StructuredType
    if name is not None:
        tltype = retrofit.get(name.lower(), tltype)
    state = ParserState(value)
    discard_ows(state)
    try:
        if tltype in ["dict", "dictionary"]:
            structure = parse_dictionary(state, on_duplicate_key)
        elif tltype == "list":
            structure = parse_list(state, on_duplicate_key)
        elif tltype == "item":
            structure = parse_item(state, on_duplicate_key)
        else:
            raise KeyError("unrecognised top-level type")
        discard_ows(state)
        if state.has_data():
            raise StructuredFieldError(
                "Trailing characters after value (missing comma?)",
                position=state.cursor,
                offending_char=state.data[state.cursor],
            )
        return structure
    except StructuredFieldError as why:
        if why.position is None:
            why.position = state.cursor
            try:
                why.offending_char = state.data[state.cursor]
            except IndexError:
                why.offending_char = None
        raise why


def ser(structure: StructuredType) -> str:
    if isinstance(structure, Dict):
        return ser_dictionary(structure)
    if isinstance(structure, List):
        return ser_list(structure)
    return ser_item(structure)
