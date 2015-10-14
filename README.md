# django-etcd-settings

## Goal

This application allows the extending the Django settings as configured in the
`settings.py` file with:

* Environment dependent values
* Values in different config sets, identified by name, which can be selected on
  a 'per request' basis using specific HTTP headers

## Installation

For now, just install it by pointing to this repository. You can either:

1. Clone this repository and run `make test` to check the library out and
   contribute to it

2. Have your Django application depend on this by using something like this in
   your `requirements.txt` file:
   `git+ssh://git@stash.kpnnl.local:7999/de/django-etcd-settings.git@master#egg=etcd_settings`


## Compatibility

This application has been tested for Python 2.7 and Django 1.7

## Configuration

This Django application uses the following configuration keys:

* `ETCD_DETAILS`: a dict with 'host', 'port' and 'protocol'. If this setting
    is None, this app will start with no errors and etcd_settings.settings
    will resolve to django.config.settings
    i.e. `ETCD_DETAILS = dict(host='localhost', port=4000, protocol='http')`

* `ETCD_CONFIG_PREFIX`: A string to be used as base path for all
    configuration managed by this app.
    i.e. '/config/api' will result in '/config/api/<ENV>' and
    '/config/api/extensions/' to be used for environment defaults and
    config_sets respectively

* `ENV`: A string with the name of the environment in which the code is
    running. This will be used for accessing the env_defaults in
    ETCD in a directory with that name
    i.e. 'test', 'staging', 'prod'...

* `REQUEST_GETTER_MODULE`: path to a module implemented a function
    'get_current_request()' which accesses the HTTP request object being
    handled. Ensuring access to this value can be implemented with, for
    instance, a middleware.
    This settings is only used to allow config overwrites on runtime based
    on predifined config_sets. In case you don't want to use this
    functionality, just set this settings to None
    i.e. 'middleware.thread_local'

Then, add `etcd_settings` to the list of `INSTALLED_APPS` before any other that
requires dynamic settings.

From your code, just do `from etcd_settings import settings` instead of `from
django.config import settings`.

## TODO

* Extending the unit tests in order to cover `etcd_settings.proxy`

* Moving this repository to [Github](http://www.github.com) and updating `url`
  and `download_url` in `setup.py` file with the new repo location

* Uploading this package to [PyPi](https://pypi.python.org). A user needs to be
  configured in `.pypirc`. After that, run:
  ```
  UPLOAD_TARGET=<upload_target> make upload
  ```
  ... where upload_target is one of `pypitest` or `pypi`
