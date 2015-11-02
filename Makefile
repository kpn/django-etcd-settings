PYTHON=`. venv/bin/activate; which python`
PIP=`. venv/bin/activate; which pip`
DEPS:=requirements.txt
VSN=`git describe --tags --always`

.PHONY: clean distclean test shell upload deps

clean:
	@find . -name *.pyc -delete

distclean: clean
	rm -rf venv

venv:
	virtualenv-2.7 -p python2.7 venv
	$(PIP) install -U "pip>=7.0"
	$(PIP) install -r $(DEPS)

deps: venv
	$(PIP) install -r $(DEPS) -U

test: venv
	$(PYTHON) tests.py

shell: venv
	$(CURDIR)/venv/bin/bpython

upload: venv
ifdef UPLOAD_TARGET
	$(PYTHON) setup.py register -r $(UPLOAD_TARGET)
	$(PYTHON) setup.py sdist upload -r $(UPLOAD_TARGET)
else
	@$(error "Please set UPLOAD_TARGET to pypitest or pypi")
endif
