"""Run the full JSON test suite through the http_sf.compat object API.

Mirrors test/test.py but uses Dictionary/List/Item.parse() and str(...) from
http_sf.compat, converting between functional and object forms to compare
against the existing JSON test expectations.
"""

import sys
from pathlib import Path
from typing import Any, List, Tuple

from http_sf import from_json
from http_sf.compat import (
    Dictionary,
    Item,
    List as CompatList,
    Parameters,
    _from_functional,
    _to_functional,
)

FAIL = "\033[91m"
WARN = "\033[93m"
ENDC = "\033[0m"


def load_tests(files: Any = None) -> List[Tuple[Path, List[Any]]]:
    suites = []
    if not files:
        files = Path("test/tests").glob("*.json")
    for filename in files:
        with open(filename, encoding="utf-8") as fh:
            suite = from_json(fh.read())
        suites.append((filename, suite))
    return suites


def _compat_parse(field_value: bytes, header_type: str) -> Any:
    if header_type == "dictionary":
        obj: Any = Dictionary()
    elif header_type == "list":
        obj = CompatList()
    elif header_type == "item":
        obj = Item()
    else:
        raise ValueError(f"Unknown header_type: {header_type}")
    obj.parse(field_value)
    return obj


def _compat_to_functional(obj: Any, header_type: str) -> Any:
    if header_type == "dictionary":
        return {k: _to_functional(v) for k, v in obj.data.items()}
    if header_type == "list":
        return [_to_functional(v) for v in obj.data]
    # item
    return (obj.value, dict(obj.params))


def _build_compat(expected: Any, header_type: str) -> Any:
    if header_type == "dictionary":
        out = Dictionary()
        for key, val in expected.items():
            out.data[key] = _from_functional(val)
        return out
    if header_type == "list":
        out = CompatList()
        for val in expected:
            out.data.append(_from_functional(val))
        return out
    # item
    value, params = expected
    item = Item(value)
    item.params = Parameters(params)
    return item


def test_parse(test: dict) -> Tuple[bool, Any, Any]:
    parsed: Any = None
    parse_success = False
    parse_fail_reason = None
    try:
        field_value = b", ".join(v.encode("utf-8") for v in test["raw"])
        obj = _compat_parse(field_value, test["header_type"])
        parsed = _compat_to_functional(obj, test["header_type"])
        parse_success = True
    except ValueError as why:
        parse_fail_reason = why.args
        parsed = {}
    except Exception:
        sys.stderr.write(f"*** TEST ERROR in {test['name']}\n")
        raise
    if test.get("must_fail", False):
        test_success = not parse_success
    else:
        test_success = test["expected"] == parsed
    return test_success, parsed, parse_fail_reason


def test_serialise(test: dict) -> Tuple[bool, Any, Any, Any]:
    expected = test.get("canonical", test["raw"])
    output: Any = None
    ser_fail_reason = None
    try:
        obj = _build_compat(test["expected"], test["header_type"])
        output = str(obj)
    except ValueError as why:
        ser_fail_reason = why.args[0]
    except Exception:
        sys.stderr.write(f"*** TEST ERROR in {test['name']}\n")
        raise
    if output is None:
        test_success = expected == []
    else:
        test_success = expected == [output]
    return test_success, output, expected, ser_fail_reason


def run_suite(suite_name: str, suite: List[dict]) -> Tuple[int, int]:
    print(f"## {suite_name}")
    suite_tests = 0
    suite_passed = 0
    for test in suite:
        suite_tests += 1
        parse_ok, parsed, parse_reason = test_parse(test)
        if parse_ok:
            suite_passed += 1
        else:
            if test.get("can_fail", False):
                print(
                    f"{WARN}  * {test['name']}: PARSE FAIL (non-critical){ENDC}"
                )
                suite_passed += 1
            else:
                print(f"{FAIL}  * {test['name']}: PARSE FAIL{ENDC}")
            print(f"    -      raw: {test['raw']}")
            print(f"    - expected: {test.get('expected', 'FAIL')}")
            print(f"    -      got: {parsed}")
            if parse_reason:
                print(f"    -   reason: {parse_reason}")

        if not test.get("must_fail", False):
            suite_tests += 1
            ser_ok, serialised, ser_expected, ser_reason = test_serialise(test)
            if ser_ok:
                suite_passed += 1
            else:
                if test.get("can_fail", False):
                    print(
                        f"{WARN} * {test['name']}: SERIALISE FAIL (non-critical){ENDC}"
                    )
                    suite_passed += 1
                else:
                    print(f"{FAIL} * {test['name']}: SERIALISE FAIL{ENDC}")
                print(f"    - expected: {ser_expected}")
                print(f"    -      got: ['{serialised}']")
                if ser_reason:
                    print(f"    -   reason: {ser_reason}")

    print(f"-> {suite_passed} of {suite_tests} passed.")
    print()
    return suite_tests, suite_passed


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(
        description="Run tests through http_sf.compat."
    )
    argparser.add_argument(
        "files",
        metavar="filename",
        type=str,
        nargs="*",
        help="a JSON file containing tests",
    )
    args = argparser.parse_args()
    total_tests = 0
    total_passed = 0
    for filename, suite in load_tests(args.files):
        tests, passed = run_suite(filename, suite)
        total_tests += tests
        total_passed += passed
    print(f"TOTAL: {total_passed} of {total_tests} passed.")
    if total_passed < total_tests:
        sys.exit(1)
