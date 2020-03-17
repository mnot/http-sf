from string import ascii_letters, digits
from typing import Tuple

from .util import remove_char

TOKEN_START_CHARS = set(ascii_letters + "*")
TOKEN_CHARS = set(ascii_letters + digits + ":/!#$%&'*+-.^_`|~")


class Token(str):
    pass


def parse_token(input_string: str) -> Tuple[str, str]:
    if not input_string or input_string[0] not in TOKEN_START_CHARS:
        raise ValueError(
            f"Token didn't start with legal character at: {input_string[:10]}"
        )
    output_string = []  # type: list
    while input_string:
        input_string, char = remove_char(input_string)
        if not char in TOKEN_CHARS:
            input_string = "".join([char, input_string])
            return input_string, Token("".join(output_string))
        output_string.append(char)
    return input_string, Token("".join(output_string))


def ser_token(token: str) -> str:
    if token and token[0] not in TOKEN_START_CHARS:
        raise ValueError("Token didn't start with legal character.")
    if not all(char in TOKEN_CHARS for char in token):
        raise ValueError("Token contains disallowed characters.")
    output = ""
    output += token
    return output
