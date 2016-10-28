PYTHON	:= $(shell which python3)

TESTS	:= $(wildcard test_*.py)
TESTS	:= $(TESTS:%.py=%)

# targets
.PHONY:	discover $(TESTS)

discover:
	$(PYTHON) -m unittest discover $(OPTS)

$(TESTS):%:	%.py
	$(PYTHON) -m unittest $(OPTS) $@
