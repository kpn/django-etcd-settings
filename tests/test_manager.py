import datetime
import json
import logging
import time

from django.test import TestCase
from etcd import EtcdException, EtcdResult
from etcd_settings.manager import (
    EtcdConfigInvalidValueError, EtcdConfigManager,
)
from mock import MagicMock


class EtcdResultGenerator():

    @staticmethod
    def key(name, value):
        d = dict(
            key=name,
            value=value,
            expiration=None,
            ttl=None,
            modifiedIndex=5,
            createdIndex=1,
            newKey=False,
            dir=False,
        )
        return d

    @staticmethod
    def result_set(dirname, keys):
        dir_keys = keys
        for k in dir_keys:
            key_name = k['key']
            k['key'] = '{}{}'.format(dirname, key_name)
        d = dict(node=dict(
            key=dirname,
            expiration=None,
            ttl=None,
            modifiedIndex=6,
            createdIndex=2,
            newKey=False,
            dir=True,
            nodes=dir_keys
        ))
        res = EtcdResult(**d)
        res.etcd_index = 99
        return res


class TestEtcdConfigManager(TestCase):
    longMessage = True

    def _dataset_for_with_empty_dir(self, env):
        expected = {
        }
        keys = [EtcdResultGenerator.key('/foo/bar', None)]
        rset = EtcdResultGenerator.result_set(
            self.mgr._env_defaults_path(env),
            keys)
        return expected, rset

    def _dataset_for_with_invalid_json(self, env):
        keys = [EtcdResultGenerator.key('/foo/bar', '{')]
        rset = EtcdResultGenerator.result_set(
            self.mgr._env_defaults_path(env),
            keys)
        return rset

    def _dataset_for_defaults(self, env):
        expected = {
            'FOO_BAR': 'baz',
            'FOO_BAZ': 'bar',
            'FOOBARBAZ': 'superbaz',
        }
        keys = [EtcdResultGenerator.key('/foo/bar', '"baz"'),
                EtcdResultGenerator.key('/foo/baz', '"bar"'),
                EtcdResultGenerator.key('/foobarbaz', '"superbaz"')]
        rset = EtcdResultGenerator.result_set(
            self.mgr._env_defaults_path(env),
            keys)
        return expected, rset

    def _dataset_for_configsets(self):
        expected = {
            'foo': {'BAR': 1, 'BAZ': 2},
            'foo.bar': {'BAZ': 1, 'BAZBAZ': 2},
            'foo.bar-zoo': {'BAR': 1},
        }
        keys = [EtcdResultGenerator.key('/foo/bar', '1'),
                EtcdResultGenerator.key('/foo/baz', '2'),
                EtcdResultGenerator.key('/foo.bar/baz', '1'),
                EtcdResultGenerator.key('/foo.bar/bazbaz', '2'),
                EtcdResultGenerator.key('/foo.bar-zoo/bar', '1')]
        rset = EtcdResultGenerator.result_set(
            self.mgr._base_config_set_path,
            keys)
        return expected, rset

    def setUp(self):
        self.mgr = EtcdConfigManager(
            dev_params=None, prefix='prefix',
            protocol='foo', host='foo', port=0,
            long_polling_timeout=50,
            long_polling_safety_delay=0.1)
        for l in self.mgr.logger.handlers:
            l.setLevel(logging.CRITICAL)

    def test_init_logger(self):
        self.assertIsNotNone(self.mgr.logger)

    def test_encode_config_key(self):
        self.assertEqual(
            'foo/bar/baz',
            self.mgr._encode_config_key('FOO_BAR_BAZ'))

    def test_decode_env_config_key(self):
        key = 'FOO_BAR'
        env = 'test'
        s = '{}/{}/foo/bar'.format(self.mgr._base_config_path, env)
        self.assertEqual((env, key), self.mgr._decode_config_key(s))

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
        env = 'test'
        expected_rs, input_rs = self._dataset_for_with_empty_dir(env)

        self.assertEqual(expected_rs, self.mgr._process_response_set(input_rs))

    def test_process_response_exception_handling(self):
        env = 'test'
        with self.assertRaises(EtcdConfigInvalidValueError) as excContext:
            input_rs = self._dataset_for_with_invalid_json(env)
            self.mgr._process_response_set(input_rs)

        exc = excContext.exception

        self.assertEqual('prefix/test/foo/bar', exc.key)
        self.assertEqual('{', exc.raw_value)
        self.assertIn("foo/bar", str(exc), "Expect key in message")
        self.assertIn(
            "Expecting", str(exc), msg="Expect detailed error message")
        self.assertIn(
            "line", str(exc), msg="Expect line number in error message")
        self.assertIn(
            "column", str(exc), msg="Expect column number in error message")
        self.assertIn("'{'", str(exc), msg="Expect invalid value")

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
        env = 'test'
        expected, rset = self._dataset_for_defaults(env)
        env_path = self.mgr._env_defaults_path(env)
        self.mgr._client.read = MagicMock(return_value=rset)
        self.assertEqual(expected, self.mgr.get_env_defaults('test'))
        self.mgr._client.read.assert_called_with(env_path, recursive=True)

    def test_get_config_sets(self):
        expected, rset = self._dataset_for_configsets()
        self.mgr._client.read = MagicMock(return_value=rset)
        self.assertEqual(expected, self.mgr.get_config_sets())
        self.mgr._client.read.assert_called_with(
            self.mgr._base_config_set_path,
            recursive=True)

    def test_monitor_env_defaults(self):
        env = 'test'
        expected, rset = self._dataset_for_defaults(env)
        d = {}
        self.mgr._client.watch = MagicMock(return_value=rset)
        old_etcd_index = self.mgr._etcd_index
        t = self.mgr.monitor_env_defaults(env=env, conf=d, max_events=1)
        self.assertEqual(1, t.result)
        self.assertEqual(expected, d)
        self.assertEqual(99, self.mgr._etcd_index)
        self.mgr._client.watch.assert_called_with(
            self.mgr._env_defaults_path(env),
            index=old_etcd_index,
            recursive=True,
            timeout=50)

    def test_monitor_config_sets(self):
        expected, rset = self._dataset_for_configsets()
        d = {}
        self.mgr._client.watch = MagicMock(return_value=rset)
        old_etcd_index = self.mgr._etcd_index
        t = self.mgr.monitor_config_sets(conf=d, max_events=1)
        self.assertEqual(1, t.result)
        self.assertEqual(expected, d)
        self.assertEqual(99, self.mgr._etcd_index)
        self.mgr._client.watch.assert_called_with(
            self.mgr._base_config_set_path,
            index=old_etcd_index,
            recursive=True,
            timeout=50)

    def test_monitors_delay_and_continue_on_exception(self):
        env = 'test'
        d = {}
        max_events = 2
        lambdas = [
            lambda: self.mgr.monitor_env_defaults(
                env, conf=d, max_events=max_events),
            lambda: self.mgr.monitor_config_sets(
                conf=d, max_events=max_events),
        ]
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

    def test_monitors_continue_on_etcd_exception(self):
        env = 'test'
        d = {}
        max_events = 2
        self.mgr._client.watch = MagicMock(
            side_effect=EtcdException('timed out'))
        lambdas = [
            lambda: self.mgr.monitor_env_defaults(
                env, conf=d, max_events=max_events),
            lambda: self.mgr.monitor_config_sets(
                conf=d, max_events=max_events),
        ]
        for l in lambdas:
            t0 = time.time()
            t = l()
            self.assertEqual(max_events, t.result)
            self.assertEqual(
                True,
                (time.time() - t0)
                < (max_events * self.mgr.long_polling_safety_delay)
            )
            self.assertEqual(False, t.is_alive())
