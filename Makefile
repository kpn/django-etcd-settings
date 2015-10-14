PYTHON=`. venv/bin/activate; which python`
PIP=`. venv/bin/activate; which pip`
DEPS:=requirements.txt
VSN=`git describe --tags --always`

clean:
	@find . -name *.pyc -delete

distclean: clean
	rm -rf venv

venv: clean
	test -d venv || virtualenv-2.7 -p python2.7 venv
	$(PIP) install -U "pip>=7.0"
	$(PIP) install -r $(DEPS)

test: venv
	$(PYTHON) tests.py

upload: venv
ifdef UPLOAD_TARGET
	$(PYTHON) setup.py register -r $(UPLOAD_TARGET)
	$(PYTHON) setup.py sdist upload -r $(UPLOAD_TARGET)
else
	@$(error "Please set UPLOAD_TARGET to pypitest or pypi")
endif
