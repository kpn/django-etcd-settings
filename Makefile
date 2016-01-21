# This Makefile requires the following commands to be available:
# * virtualenv-2.7
# * python2.7
# * docker
# * docker-compose

DEPS:=requirements.txt
DOCKER_COMPOSE:=$(shell which docker-compose)

PIP:="venv/bin/pip"
CMD_FROM_VENV:=". venv/bin/activate; which"
TOX=$(shell "$(CMD_FROM_VENV)" "tox")
PYTHON=$(shell "$(CMD_FROM_VENV)" "python")
TOX_PY_LIST="$(shell $(TOX) -l | grep ^py | xargs | sed -e 's/ /,/g')"

.PHONY: clean docsclean pyclean test lint isort docs docker setup.py

tox: clean venv
	$(TOX)

pyclean:
	@find . -name *.pyc -delete
	@rm -rf *.egg-info build
	@rm -rf coverage.xml .coverage

docsclean:
	@rm -fr docs/_build/
	@rm -fr docs/api/

clean: pyclean docsclean
	@rm -rf venv

venv:
	@virtualenv -p python2.7 venv
	@$(PIP) install -U "pip>=7.0" -q
	@$(PIP) install -r $(DEPS)

test: venv pyclean
	$(TOX) -e $(TOX_PY_LIST)

test/%: venv pyclean
	$(TOX) -e $(TOX_PY_LIST) -- $*

lint: venv
	@$(TOX) -e lint
	@$(TOX) -e isort-check

isort: venv
	@$(TOX) -e isort-fix

docs: venv docsclean
	@$(TOX) -e docs

docker:
	$(DOCKER_COMPOSE) run --rm app bash

docker/%:
	$(DOCKER_COMPOSE) run --rm app make $*

setup.py: venv
	$(PYTHON) setup_gen.py
	$(PYTHON) setup.py check --restructuredtext

publish: setup.py
	$(PYTHON) setup.py sdist upload

build: clean venv tox setup.py
