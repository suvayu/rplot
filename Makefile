PYTHON	:= $(shell which python)

TESTS	:= $(wildcard test_*.py)

# targets
$(TESTS:%.py=%):%:	%.py
	 $(PYTHON) -m unittest $(OPTS) $@

-include local.mk
