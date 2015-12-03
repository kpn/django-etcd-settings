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
TOX_PY_LIST="$(shell $(TOX) -l | grep ^py | xargs | sed -e 's/ /,/g')"

.PHONY: clean docsclean distclean test lint docs docker

build: venv clean
	$(TOX)

clean:
	@find . -name *.pyc -delete
	@rm -rf de_core.egg-info build

docsclean:
	@rm -fr docs/_build/

distclean: clean docsclean
	@rm -rf venv

venv:
	@virtualenv-2.7 -p python2.7 venv
	@$(PIP) install -U "pip>=7.0" -q
	@$(PIP) install -r $(DEPS)

test: venv clean
	$(TOX) -e $(TOX_PY_LIST)

test/%: venv clean
	$(TOX) -e $(TOX_PY_LIST) -- $*

lint: venv
	@$(TOX) -e lint
	@$(TOX) -e isort-check

isort: venv
	@$(TOX) -e isort-fix

docs: venv
	@$(TOX) -e docs

docker:
	$(DOCKER_COMPOSE) run --rm app bash

docker/%:
	$(DOCKER_COMPOSE) run --rm app make $*
