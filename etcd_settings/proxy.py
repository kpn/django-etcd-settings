from importlib import import_module
from django.conf import settings as django_settings
from .mgr import EtcdConfigManager
from .utils import dict_rec_update


class EtcdSettingsProxy(object):
    """
    Config Dependencies:
    * ETCD_DETAILS: a dict with 'host', 'port' and 'protocol'. If this setting
        is None, this app will start with no errors and etcd_settings.settings
        will resolve to django.config.settings
    * ENV: A string with the name of the environment in which the code is
        running. This will be used for accessing the env_defaults in
        a directory with that name. i.e. 'test', 'staging', 'prod'...
    * REQUEST_GETTER_MODULE: path to a module implemented a function
        'get_current_request()' which accesses the HTTP request object being
        handled. Ensuring access to this value can be implemented with, for
        instance, a middleware.  i.e. 'middleware.thread_local'
        This settings is only used to allow config overwrites on runtime based
        on predifined config_sets. In case you don't want to use this
        functionality, just set this settings to None
    * ETCD_CONFIG_PREFIX: A string to be used as base path for all
        configuration managed by this app.
        i.e. '/config/api' will result in '/config/api/<ENV>' and
        '/config/api/extensions/' to be used for environment defaults and
        config_sets respectively
    """

    def __init__(self):
        self._env = django_settings.ENV
        self._etcd_details = django_settings.ETCD_DETAILS
        self._prefix = django_settings.ETCD_CONFIG_PREFIX
        if self._etcd_details is not None:
            self._etcd_mgr = EtcdConfigManager(
                self._prefix, **self._etcd_details)
            self._config_sets = self._etcd_mgr.get_config_sets()
            self._env_defaults = self._etcd_mgr.get_env_defaults(self._env)
        else:
            self._etcd_mgr = None
            self._config_sets = dict()
            self._env_defaults = dict()

    def _parse_req_config_sets(self):
        sets = []
        if getattr(django_settings, 'REQUEST_GETTER_MODULE', None) is not None:
            req_getter = import_module(
                django_settings.REQUEST_GETTER_MODULE).get_current_request
            request = req_getter()
            if request and getattr(request, "META", None):
                sets = request.META.get('HTTP_X_DYNAMIC_SETTING', '').split()
        return sets

    def start_monitors(self):
        if self._etcd_mgr is not None:
            self._env_defaults = self.monitor_env_defaults(self.env)
            self._config_sets = self.monitor_config_sets()

    def __getattr__(self, attr):
        try:
            dj_value = getattr(django_settings, attr)
            dj_value_exists = True
        except AttributeError:
            dj_value_exists = False
            dj_value = None
        try:
            value = getattr(self._env_defaults, attr)
            value_exists = True
        except AttributeError:
            value_exists = dj_value_exists
            value = dj_value

        for override_set in self._parse_req_config_sets():
            new_value = self._config_sets.get(override_set, {}).get(attr)
            if new_value:
                if isinstance(value, dict) and isinstance(new_value, dict):
                    dict_rec_update(value, new_value)
                else:
                    value = new_value
        if value or value_exists:
            return value
        else:
            raise AttributeError(attr)

    def as_dict(self):
        """Return a dict with all settings, overridden if need be"""

        env_defaults = self._env_defaults
        items = {}
        for key in dir(django_settings):
            if key.isupper():
                items[key] = getattr(self, key)
        env_defaults.update(items)
        return env_defaults


proxy = EtcdSettingsProxy()
