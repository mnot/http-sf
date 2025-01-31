
# HTTP Structured Fields in Python

[![Test Status](https://github.com/mnot/http-sf/actions/workflows/test.yml/badge.svg)](https://github.com/mnot/http-sf/actions)

This is a [Python 3](https://python.org/) library implementing parsing and serialisation of [RFC 9651](https://www.rfc-editor.org/rfc/rfc9651.html).

## Python API

### Parsing

Textual HTTP headers can be parsed by calling `parse`; the return value is a data structure that represents the field value.

~~~ python
>>> from http_sf import parse, ser
>>> parse(b"foo; a=1, bar; b=2", tltype="dictionary")
{'foo': (True, {'a': 1}), 'bar': (True, {'b': 2})}
~~~

`parse()` takes a bytes-like object as the first argument. If you want to parse a string, please `.encode()` it first.

#### Indicating Top-Level Type

Because the library needs to know which kind of field it is, you need to hint this when calling `parse`. There are two ways to do this:

1. Using a `tltype` parameter, whose value should be one of 'dictionary', 'list', or 'item'.
2. Using a `name` parameter to indicate a field name that has a registered type, per [the retrofit draft](https://httpwg.org/http-extensions/draft-ietf-httpbis-retrofit.html).

Note that if you use `name`, a `KeyError` will be raised if the type associated with the name isn't known, unless you also pass a `tltype` as a fallback.

### Types

In the returned data, Dictionaries are represented as Python dictionaries; Lists are represented as Python lists, and Items are the bare type.

Bare types are represented using the following Python types:

* Integers: `int`
* Decimals: `float`
* Strings: `str`
* Tokens: `http_sf.Token` (a `UserString`)
* Byte Sequences: `bytes`
* Booleans: `bool`
* Dates: `datetime.datetime`
* Display Strings: `http_sf.DisplayString` (a `UserString`)

Inner Lists are represented as lists as well.

### Parameters

Structured Types that can have parameters (including Dictionary and List members as well as singular Items and Inner Lists) are represented as a tuple of `(value, parameters)` where parameters is a dictionary.

So, a single item that's a Token with one parameter whose value is an integer will be represented like this:

~~~ python
>>> parse(b"foo; a=1", tltype="item")
(Token("foo"), {'a': 1})
~~~

Note that even if there aren't parameters, a tuple will still be returned, as in some items on this List:

~~~ python
>>> parse(b"a, b; q=5, c", tltype="list")
[(Token("a"), {}), (Token("b"), {'q': 5}), (Token("c"), {})]
~~~

### Serialisation

To serialise that data structure back to a textual Structured Field, use `ser`:

~~~ python
>>> field = parse(b"a, b; q=5, c", tltype="list")
>>> ser(field)
'a, b;q=5, c'
~~~

When using `ser`, if an Item or Inner List doesn't have parameters, they can be omitted; for example:

~~~ python
>>> structure = [5, 6, (7, {"with": "param"})]
>>> ser(structure)
'5, 6, 7;with="param"'
~~~

Note that `ser` produces a string, not a bytes-like object.


## Command Line Use

You can validate and examine the data model of a field value by calling the library on the command line, using `-d`, `-l` and `-i` to denote dictionaries, lists or items respectively; e.g.,

~~~ bash
> python3 -m http_sf -i "foo;bar=baz"
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

~~~ bash
> python3 -m http_sf -i "foo;&bar=baz"
FAIL: Key does not begin with lcalpha or * at: &bar=baz
~~~

Alternatively, you can pass the field name with the `-n` option, provided that it is a compatible retrofit field:

~~~ bash
> python3 -m http_sf -n "Cache-Control" "max-age=40, must-revalidate"
{
    "max-age": [
        40,
        {}
    ],
    "must-revalidate": [
        true,
        {}
    ]
}
~~~

Note that if successful, the output is in the JSON format used by the [test suite](https://github.com/httpwg/structured-header-tests/).

