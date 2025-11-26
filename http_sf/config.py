"Configuration for http_sf."

from typing import Callable, Union

# Callback for duplicate keys. If set, it will be called with the duplicate key name.
on_duplicate_key: Union[Callable[[str], None], None] = None  # pylint: disable=invalid-name
