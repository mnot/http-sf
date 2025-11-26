"Configuration for http_sf."

from typing import Callable, Union

# Callback for duplicate keys. If set, it will be called with the duplicate key name and
# the context in which it occurred (either "dictionary" or "parameter").
on_duplicate_key: Union[Callable[[str, str], None], None] = None  # pylint: disable=invalid-name
