
from typing import Tuple

def parse_boolean(input_string: str) -> Tuple[str, bool]:
    if not input_string or input_string[0] != "?":
        raise ValueError("First character of Boolean is not '?'", input_string)
    input_string = input_string[1:]
    if input_string and input_string[0] == "T":
        input_string = input_string[1:]
        return input_string, True
    if input_string and input_string[0] == "F":
        input_string = input_string[1:]
        return input_string, False
    raise ValueError("No Boolean value found.", input_string)

def ser_boolean(inval: bool) -> str:
    if type(inval) is not bool:
        raise ValueError("Input is not Boolean.")
    output = ""
    output += "?"
    if inval:
        output += "T"
    if not inval:
        output += "F"
    return output
