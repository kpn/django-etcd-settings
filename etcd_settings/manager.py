import re
import json
from os import utime
from importlib import import_module
from etcd import Client
from .utils import (threaded, CustomJSONEncoder, custom_json_decoder_hook,
                    attrs_to_dir)


class EtcdConfigManager():

    def __init__(self, dev_params=None, prefix='config', protocol='http',
                 host='localhost', port=2379):
        self._client = Client(
            host=host, port=port, protocol=protocol, allow_redirect=True)
        self._base_config_path = prefix
        self._dev_params = dev_params
        self._base_config_set_path = "{}/extensions"\
            .format(self._base_config_path)
        r = '^(?P<path>{}/(?:extensions/)?(?P<envorset>[\w\.]+))/(?P<key>.+)$'
        self._key_regex = re.compile(r.format(self._base_config_path))
        self._etcd_index = 0

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
        return json.loads(val, object_hook=custom_json_decoder_hook)

    def _process_response_set(self, rset, env_defaults=True):
        d = {}
        for leaf in rset.leaves:
            config_set, key = self._decode_config_key(leaf.key)
            value = self._decode_config_value(leaf.value)
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

    def get_env_defaults(self, env='test_exa'):
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

    @threaded
    def monitor_env_defaults(self, env='test_exa', conf={}, wsgi_file=None):
        for event in self._client.eternal_watch(
                self._env_defaults_path(env),
                index=self._etcd_index,
                recursive=True):
            self._etcd_index = event.etcd_index
            conf.update(self._process_response_set(event))
            conf.update(EtcdConfigManager.get_dev_params(self._dev_params))
            if wsgi_file:
                with open(wsgi_file, 'a'):
                    utime(wsgi_file, None)

    @threaded
    def monitor_config_sets(self, conf={}):
        for event in self._client.eternal_watch(
                self._base_config_set_path,
                index=self._etcd_index,
                recursive=True):
            self._etcd_index = event.etcd_index
            conf.update(self._process_response_set(event, env_defaults=False))

    def set_env_defaults(self, env='test_exa', conf={}):
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
                            self._encode_config_value(v),
                            append=True)
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
