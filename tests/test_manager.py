import datetime
import json
import logging
import os
import time

from django.test import TestCase
from etcd import EtcdKeyNotFound
from etcd_settings.manager import (
    EtcdClusterState, EtcdConfigInvalidValueError, EtcdConfigManager,
)

from .conftest import settings


class TestEtcdConfigManager(TestCase):
    longMessage = True

    def _dataset_with_empty_dir(self):
        key = os.path.join(self.mgr._env_defaults_path(self.env), 'dir/empty')
        self.mgr._client.write(key, None, dir=True)
        value = self.mgr._client.get(key)
        return key, value

    def _dataset_with_invalid_json(self):
        key = os.path.join(
            self.mgr._env_defaults_path(self.env), 'json/invalid')
        self.mgr._client.set(key, '{')
        value = self.mgr._client.get(key)
        return key, value

    def _dataset_for_defaults(self):
        dataset = {}
        k1 = os.path.join(self.mgr._env_defaults_path(self.env), 'foo/bar')
        dataset[k1] = '"baz"'
        k2 = os.path.join(self.mgr._env_defaults_path(self.env), 'foo/baz')
        dataset[k2] = '"bar"'
        k3 = os.path.join(self.mgr._env_defaults_path(self.env), 'foobarbaz')
        dataset[k3] = '"superbaz"'
        expected_env = {
            'FOO_BAR': 'baz',
            'FOO_BAZ': 'bar',
            'FOOBARBAZ': 'superbaz',
        }
        for k, v in dataset.items():
            self.mgr._client.set(k, v)
        return dataset.keys(), expected_env

    def _dataset_for_configsets(self):
        dataset = {}
        k1 = os.path.join(self.mgr._config_set_path('foo'), 'bar')
        dataset[k1] = '1'
        k2 = os.path.join(self.mgr._config_set_path('foo'), 'baz')
        dataset[k2] = '2'
        k3 = os.path.join(self.mgr._config_set_path('foo.bar'), 'baz')
        dataset[k3] = '1'
        k4 = os.path.join(self.mgr._config_set_path('foo.bar'), 'bazbaz')
        dataset[k4] = '2'
        k5 = os.path.join(self.mgr._config_set_path('foo.bar-zoo'), 'bar')
        dataset[k5] = '1'
        expected_sets = {
            'foo': {'BAR': 1, 'BAZ': 2},
            'foo.bar': {'BAZ': 1, 'BAZBAZ': 2},
            'foo.bar-zoo': {'BAR': 1},
        }
        for k, v in dataset.items():
            self.mgr._client.set(k, v)
        return dataset.keys(), expected_sets

    def setUp(self):

        self.env = 'unittest'
        EtcdClusterState.etcd_index = 0
        self.mgr = EtcdConfigManager(
            dev_params=None, prefix=settings.ETCD_PREFIX, protocol='http',
            host=settings.ETCD_HOST, port=settings.ETCD_PORT,
            username=settings.ETCD_USERNAME, password=settings.ETCD_PASSWORD,
            long_polling_timeout=0.1, long_polling_safety_delay=0.1
        )
        for l in self.mgr.logger.handlers:
            l.setLevel(logging.CRITICAL)

    def tearDown(self):
        def try_unless_not_found(f):
            try:
                f()
            except EtcdKeyNotFound:
                pass

        def clean_env():
            self.mgr._client.delete(
                self.mgr._env_defaults_path(self.env), recursive=True)

        def clean_extensions():
            self.mgr._client.delete(
                self.mgr._base_config_set_path, recursive=True)

        try_unless_not_found(clean_extensions)
        try_unless_not_found(clean_env)

    def test_init_logger(self):
        self.assertIsNotNone(self.mgr.logger)

    def test_encode_config_key(self):
        self.assertEqual(
            'foo/bar/baz',
            self.mgr._encode_config_key('FOO_BAR_BAZ'))

    def test_decode_env_config_key(self):
        key = 'FOO_BAR'
        s = '{}/{}/foo/bar'.format(self.mgr._base_config_path, self.env)
        self.assertEqual((self.env, key), self.mgr._decode_config_key(s))

    def test_decode_set_config_key(self):
        key = 'FOO_BAR'
        configset = 'unit.test'
        s = '{}/{}/foo/bar'.format(self.mgr._base_config_set_path, configset)
        self.assertEqual((configset, key), self.mgr._decode_config_key(s))

    def test_encode_config_value(self):
        self.assertEqual(
            '"abcde"',
            self.mgr._encode_config_value('abcde'))
        self.assertEqual(
            '112',
            self.mgr._encode_config_value(112))
        self.assertEqual(
            # Tuples are lost in encoding, should be avoided as config values
            '[1, "b"]',
            self.mgr._encode_config_value((1, 'b')))
        encoded_config = self.mgr._encode_config_value(dict(foo=1, bar='baz'))
        self.assertEqual(
            json.loads('{"foo": 1, "bar": "baz"}'),
            json.loads(encoded_config))

    def test_process_response_set_empty(self):
        key, value = self._dataset_with_empty_dir()
        self.assertEqual({}, self.mgr._process_response_set(value))

    def test_process_response_exception_handling(self):
        with self.assertRaises(EtcdConfigInvalidValueError) as excContext:
            key, value = self._dataset_with_invalid_json()
            self.mgr._process_response_set(value)

        exc = excContext.exception

        self.assertEqual(key, exc.key)
        self.assertEqual(value.value, exc.raw_value)
        self.assertIn(key, str(exc), "Expect key in message")
        self.assertIn(
            "Expecting", str(exc), msg="Expect detailed error message")
        self.assertIn(
            "line", str(exc), msg="Expect line number in error message")
        self.assertIn(
            "column", str(exc), msg="Expect column number in error message")
        self.assertIn(value.value, str(exc), msg="Expect invalid value")

    def test_decode_config_value(self):
        self.assertEqual(
            'abcde',
            self.mgr._decode_config_value('"abcde"'))
        self.assertEqual(
            112,
            self.mgr._decode_config_value('112'))
        self.assertEqual(
            dict(foo=1, bar='baz'),
            self.mgr._decode_config_value('{"foo": 1, "bar": "baz"}'))
        self.assertEqual(
            [1, 'b'],
            self.mgr._decode_config_value('[1, "b"]'))

    def test_custom_encoding_decoding_values(self):
        d = datetime.datetime(2015, 10, 9, 8, 7, 6)
        encoded_d = self.mgr._encode_config_value(d)
        decoded_d = self.mgr._decode_config_value(encoded_d)
        self.assertEqual(True, isinstance(decoded_d, datetime.datetime))
        self.assertEqual(d.isoformat(), decoded_d.isoformat())
        self.assertEqual(d, decoded_d)

    def test_get_env_defaults(self):
        keys, expected = self._dataset_for_defaults()
        self.assertEqual(expected, self.mgr.get_env_defaults(self.env))

    def test_get_config_sets(self):
        keys, expected_sets = self._dataset_for_configsets()
        self.assertEqual(expected_sets, self.mgr.get_config_sets())

    def test_monitor_env_defaults(self):
        keys, expected_env = self._dataset_for_defaults()
        d = {}
        old_etcd_index = EtcdClusterState.etcd_index
        t = self.mgr.monitor_env_defaults(env=self.env, conf=d, max_events=1)
        self.assertEqual(1, t.result)
        self.assertEqual(expected_env, d)
        self.assertGreater(EtcdClusterState.etcd_index, old_etcd_index)

    def test_monitor_config_sets(self):
        keys, expected_sets = self._dataset_for_configsets()
        d = {}
        old_etcd_index = EtcdClusterState.etcd_index
        t = self.mgr.monitor_config_sets(conf=d, max_events=1)
        self.assertEqual(1, t.result)
        self.assertEqual(expected_sets, d)
        self.assertGreater(EtcdClusterState.etcd_index, old_etcd_index)

    def test_monitors_delay_and_continue_on_exception(self):
        d = {}
        max_events = 2
        lambdas = [
            lambda: self.mgr.monitor_env_defaults(
                self.env, conf=d, max_events=max_events),
            lambda: self.mgr.monitor_config_sets(
                conf=d, max_events=max_events),
        ]
        try:
            self.mgr._base_config_path = 'Unknown'
            for l in lambdas:
                t0 = time.time()
                t = l()
                self.assertEqual(max_events, t.result)
                self.assertEqual(
                    True,
                    (time.time() - t0)
                    > (max_events * self.mgr.long_polling_safety_delay)
                )
                self.assertEqual(False, t.is_alive())
        finally:
            self.mgr._base_config_path = settings.ETCD_PREFIX

    def test_monitors_continue_on_etcd_exception(self):
        d = {}
        max_events = 2
        lambdas = [
            lambda: self.mgr.monitor_env_defaults(
                self.env, conf=d, max_events=max_events),
            lambda: self.mgr.monitor_config_sets(
                conf=d, max_events=max_events),
        ]
        try:
            old_etcd_index = EtcdClusterState.etcd_index
            self.mgr._etcd_index = 999990
            for l in lambdas:
                t0 = time.time()
                t = l()
                self.assertEqual(max_events, t.result)
                net_time = time.time() - t0
                self.assertGreater(
                    net_time,
                    (max_events * self.mgr.long_polling_timeout)
                )
                self.assertLess(
                    net_time,
                    (max_events *
                        (self.mgr.long_polling_safety_delay
                            + self.mgr.long_polling_timeout))
                )
                self.assertEqual(False, t.is_alive())
        finally:
            EtcdClusterState.etcd_index = old_etcd_index
