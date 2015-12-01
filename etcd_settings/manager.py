import json
import logging
import re
import time
from importlib import import_module
from os import utime
from etcd import (Client, EtcdException)
from .utils import (
    threaded, CustomJSONEncoder,
    custom_json_decoder_hook, attrs_to_dir, byteify
)


class EtcdConfigInvalidValueError(Exception):
    def __init__(self, key, raw_value, value_error):
        self.key = key
        self.raw_value = raw_value
        self.value_error = value_error
        super(EtcdConfigInvalidValueError, self).__init__(
            "Invalid value for key '{}'. Raising '{}', because of value: '{}'"
            .format(key, value_error, raw_value))


class EtcdConfigManager():

    def __init__(
            self, dev_params=None, prefix='config', protocol='http',
            host='localhost', port=2379, long_polling_timeout=50,
            long_polling_safety_delay=5):
        self._client = Client(
            host=host, port=port, protocol=protocol, allow_redirect=True)
        self._base_config_path = prefix
        self._dev_params = dev_params
        self._base_config_set_path = "{}/extensions"\
            .format(self._base_config_path)
        r = ('^(?P<path>{}/(?:extensions/)?'
             '(?P<envorset>[\w\-\.]+))/(?P<key>.+)$')
        self._key_regex = re.compile(r.format(self._base_config_path))
        self._etcd_index = 0
        self.long_polling_timeout = long_polling_timeout
        self.long_polling_safety_delay = long_polling_safety_delay
        self._init_logger()

    def _init_logger(self):
        self.logger = logging.getLogger('etcd_config_manager')
        logger_console_handler = logging.StreamHandler()
        logger_console_handler.setLevel(logging.ERROR)
        self.logger.addHandler(logger_console_handler)

    def _env_defaults_path(self, env='test'):
        return "{}/{}".format(self._base_config_path, env)

    def _config_set_path(self, set_name):
        return "{}/{}".format(self._base_config_set_path, set_name)

    def _encode_config_key(self, k):
        return k.lower().replace('_', '/')

    def _decode_config_key(self, k):
        [env_or_set, key_path] = re.sub(
            self._key_regex, '\g<envorset>|\g<key>', k).split('|')
        return env_or_set, key_path.upper().replace('/', '_')

    def _encode_config_value(self, val):
        return json.dumps(val, cls=CustomJSONEncoder)

    def _decode_config_value(self, val):
        decoded = json.loads(val, object_hook=custom_json_decoder_hook)
        return byteify(decoded)

    def _process_response_set(self, rset, env_defaults=True):
        d = {}
        for leaf in rset.leaves:
            config_set, key = self._decode_config_key(leaf.key)
            if leaf.value is not None:
                try:
                    value = self._decode_config_value(leaf.value)
                except ValueError as e:
                    raise EtcdConfigInvalidValueError(
                        leaf.key, leaf.value, e)

                if env_defaults:
                    d[key] = value
                else:
                    if config_set not in d:
                        d[config_set] = {}
                    d[config_set][key] = value
        return d

    @staticmethod
    def get_dev_params(mod):
        params = {}
        if mod:
            params = attrs_to_dir(import_module(mod))
        return params

    def get_env_defaults(self, env):
        res = self._client.read(
            self._env_defaults_path(env),
            recursive=True)
        conf = self._process_response_set(res)
        conf.update(EtcdConfigManager.get_dev_params(self._dev_params))
        return conf

    def get_config_sets(self):
        res = self._client.read(
            self._base_config_set_path,
            recursive=True)
        conf = self._process_response_set(res, env_defaults=False)
        return conf

    @threaded(daemon=True)
    def monitor_env_defaults(
            self, env, conf={}, wsgi_file=None, max_events=None):
        for event in self._watch(
                self._env_defaults_path(env), conf, wsgi_file, max_events):
            self._etcd_index = event.etcd_index
            conf.update(self._process_response_set(event))
            conf.update(EtcdConfigManager.get_dev_params(self._dev_params))
            if wsgi_file:
                with open(wsgi_file, 'a'):
                    utime(wsgi_file, None)

    @threaded(daemon=True)
    def monitor_config_sets(self, conf={}, max_events=None):
        for event in self._watch(
                self._base_config_set_path, conf=conf, max_events=max_events):
            self._etcd_index = event.etcd_index
            conf.update(self._process_response_set(event, env_defaults=False))

    def _watch(self, path, conf={}, wsgi_file=None, max_events=None):
        i = 0
        while (max_events is None) or (i < max_events):
            try:
                i += 1
                res = self._client.watch(
                    path,
                    index=self._etcd_index,
                    recursive=True,
                    timeout=self.long_polling_timeout)
                yield res
            except Exception as e:
                if isinstance(e, EtcdException) and ('timed out' in e.message):
                    continue
                self.logger.error("Long Polling Error: {}".format(e))
                time.sleep(self.long_polling_safety_delay)

    def set_env_defaults(self, env, conf={}):
        path = self._env_defaults_path(env)
        errors = {}
        for k, v in conf.iteritems():
            if k.isupper():
                try:
                    encoded_key = self._encode_config_key(k)
                    self._client.write(
                        "{}/{}".format(path, encoded_key),
                        self._encode_config_value(v))
                except Exception as e:
                    errors[k] = e.message
        return errors

    def set_config_sets(self, config_sets={}):
        errors = {}
        for set_name, config_set in config_sets.iteritems():
            path = self._config_set_path(set_name)
            for k, v in config_set.iteritems():
                if k.isupper():
                    try:
                        self._client.write(
                            "{}/{}".format(path, self._encode_config_key(k)),
                            self._encode_config_value(v))
                    except Exception as e:
                        errors[k] = e.message
        return errors

    def format_set_errors(self, errors={}, env_defaults=True):
        output = []
        if errors:
            config_type = 'env defaults'
            if not env_defaults:
                config_type = 'dynamic config set'
            output.append('Failed to load {} keys as {}:'.format(
                len(errors), config_type))
            for k, e in sorted(errors.iteritems()):
                output.append("    {} : {}".format(k, e))
        return '\n'.join(output)
