PROJECT=http_sf
BLAB=test/blab
TESTS=test/tests/*.json
SER_TESTS=test/tests/serialisation-tests/*.json

.PHONY: test
test: $(TESTS) $(SER_TESTS) venv
	PYTHONPATH=.:$(VENV) $(VENV)/python test/test.py $(TESTS) $(SER_TESTS)
	PYTHONPATH=.:$(VENV) $(VENV)/python test/test_compat_full.py $(TESTS) $(SER_TESTS)
	@# Every other test/test_*.py is a self-contained script; new ones are picked up
	@# automatically. test_compat_full.py takes the JSON files and test_perf.py is
	@# the benchmark (see the perf target).
	@for t in test/test_*.py; do \
		case $$t in test/test_compat_full.py|test/test_perf.py) continue;; esac; \
		echo "== $$t"; \
		PYTHONPATH=.:$(VENV) $(VENV)/python $$t || exit 1; \
	done

$(TESTS) $(SER_TESTS):
	git submodule update --init --recursive

.PHONY: update-tests
update-tests:
	cd test/tests; git pull origin main || exit
	git add test/tests
	git commit -m "update tests"

.PHONY: perf
perf: venv
	PYTHONPATH=. $(VENV)/python test/test_perf.py

pyright: venv
	PYTHONPATH=$(VENV) $(VENV)/python -m pyright $(PROJECT)

$(BLAB).c:
	curl https://haltp.org/files/blab-0.2.c.gz | gzip -d > $@

$(BLAB): $(BLAB).c
	sha256sum -c test/download.sha256 && cc -O -o $@ $<

.PHONY: fuzz-%
fuzz-%: venv $(BLAB)
	while [ true ];\
	do\
		$(BLAB) -l test -e "sf.sf-$*" -f 200 | PYTHONPATH=$(VENV) $(VENV)/python -m $(PROJECT) --$* --stdin || exit 1;\
	done

.PHONY: clean
clean: clean_py
	rm -rf test/blab*

.PHONY: lint
lint: lint_py

.PHONY: typecheck
typecheck: typecheck_py

.PHONY: tidy
tidy: tidy_py



include Makefile.pyproject
