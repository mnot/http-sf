
# Shhh!

## Structured HTTP Headers (handily)

This is a [Python 3](https://python.org/) library implementing parsing and serialisation of [Structured Headers for HTTP](https://httpwg.org/http-extensions/draft-ietf-httpbis-header-structure.html).

Shhh's initial purpose is to prove the algorithms in the specification; as a result, it is not at all optimised. It tracks the specification closely, but since it is not yet an RFC, may change at any time.

The top-level `parse` and `serialise` functions are the ones your code should call.

_Currently, this implements draft 17 of the specification._

## Command Line Use

You can validate and examine the data model of a field value by calling the library on the command line, using `-d`, `-l` and `i` to denote dictionaries, lists and items respectively; e.g.,

~~~ example
> python3 -m shhh -i "foo;bar=baz"
[
    {
        "__type": "token",
        "value": "foo"
    },
    {
        "bar": {
            "__type": "token",
            "value": "baz"
        }
    }
]
~~~

or:

~~~ example
> python3 -m shhh -i "foo;&bar=baz"
FAIL: Key does not begin with lcalpha or * at: &bar=baz
~~~
