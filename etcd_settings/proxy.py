import os
import re
from importlib import import_module

from django.conf import settings as django_settings

from .manager import EtcdConfigManager
from .utils import (
    attrs_to_dir, copy_if_mutable, dict_rec_update, find_project_root,
)


class EtcdSettingsProxy(object):

    def __init__(self):
        self.env = getattr(django_settings, 'DJES_ENV', None)
        dev_params = getattr(django_settings, 'DJES_DEV_PARAMS', None)
        etcd_details = getattr(django_settings, 'DJES_ETCD_DETAILS', None)
        self._init_req_getter(
            getattr(django_settings, 'DJES_REQUEST_GETTER', None))
        self._locate_wsgi_file(
            getattr(django_settings, 'DJES_WSGI_FILE', None))
        if etcd_details is not None:
            self._etcd_mgr = EtcdConfigManager(dev_params, **etcd_details)
            self._config_sets = self._etcd_mgr.get_config_sets()
            self._env_defaults = self._etcd_mgr.get_env_defaults(self.env)
        else:
            self._etcd_mgr = None
            self._config_sets = dict()
            self._env_defaults = EtcdConfigManager.get_dev_params(dev_params)

    def _locate_wsgi_file(self, wsgi_file):
        if wsgi_file is None:
            self._wsgi_file = None
        elif wsgi_file.startswith(os.path.sep):
            self._wsgi_file = wsgi_file
        else:
            self._wsgi_file = os.path.join(
                find_project_root('manage.py'),
                wsgi_file)

    def _init_req_getter(self, s):
        if s is not None:
            r = re.compile('(?P<module>.*)\.(?P<f>[\w_]+)')
            m = re.match(r, s)
            mod_s = m.group('module')
            fun_s = m.group('f')
            mod = import_module(mod_s)
            self._req_getter = getattr(mod, fun_s)
        else:
            self._req_getter = None

    def _parse_req_config_sets(self):
        sets = []
        if self._req_getter is not None:
            request = self._req_getter()
            if request and getattr(request, "META", None):
                sets = request.META.get('HTTP_X_DYNAMIC_SETTING', '').split()
        return sets

    def start_monitors(self):
        if self._etcd_mgr is not None:
            self._etcd_mgr.monitor_env_defaults(
                env=self.env, conf=self._env_defaults,
                wsgi_file=self._wsgi_file)
            self._etcd_mgr.monitor_config_sets(conf=self._config_sets)

    def __getattr__(self, attr):
        try:
            dj_value = getattr(django_settings, attr)
            dj_value_exists = True
        except AttributeError:
            dj_value_exists = False
            dj_value = None
        try:
            value = self._env_defaults[attr]
            value_exists = True
        except KeyError:
            value_exists = dj_value_exists
            value = dj_value

        for override_set in self._parse_req_config_sets():
            config_set = self._config_sets.get(override_set, {})
            if attr in config_set:
                new_value = config_set[attr]
                value = copy_if_mutable(value)
                if isinstance(value, dict) and isinstance(new_value, dict):
                    dict_rec_update(value, new_value)
                else:
                    value = new_value
        if value or value_exists:
            return value
        else:
            raise AttributeError(attr)

    def as_dict(self):
        items = attrs_to_dir(django_settings)
        items.update(self._env_defaults)
        return items


proxy = EtcdSettingsProxy()
