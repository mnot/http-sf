# Project Rules

You are writing a Python library for parsing HTTP Structured Fields. Adherence to the RFC is paramount; avoid relying on sources like MDN unless the standard is ambiguous or out of date. Always refer to the most current version of each standard.


## Code Style

- Target all currently supported versions of Python.
- PEP8 style Python.
- 100 characters on a line, max.
- all imports need to be at the top of each file.
- All code should have type declarations.


## Tests

- All code additions and changes should have tests, using existing infrastructure where possible.
- Tests should reside in the same file as the code unless it is used in multiple files, in which case it should be separate.
- New test files in `test/` should be added as a target in the Makefile and invoked by `make test`.

## Workflow

For each code change, you MUST:

1. Typecheck by running `make typecheck`
2. Lint by running `make lint`
3. Test by running `make test`
4. Format by running `make tidy` (this can fix line length issues and trailing whitespace)

These MUST be run after each code change, and MUST all succeed before presenting something to the user.

You MUST use `.venv/bin/python` if you need to run Python and the task isn't covered by the make rules above. Don't run pytest; use make test. You can run `test/`test_foo` with `make test_foo`.

Note that `make` targets automatically use the virtual environment, so you don't need to activate it explicitly.

You will NOT make edits to large numbers of files without explaining your plan and giving the user an opportunity to intervene.
