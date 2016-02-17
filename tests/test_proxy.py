import json
import os
import re
import sys

from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from etcd_settings.loader import get_overwrites
from etcd_settings.manager import EtcdClusterState, EtcdConfigManager
from etcd_settings.proxy import EtcdSettingsProxy
from mock import MagicMock

from .conftest import settings


@override_settings(
    DJES_ETCD_DETAILS=settings.ETCD_DETAILS,
    DJES_ENV=settings.ETCD_ENV,
    DJES_REQUEST_GETTER='etcd_settings.utils.threaded',
    E=0
)
class TestEtcdSettingsProxy(TestCase):

    def setUp(self):
        s = ''
        with open('tests/unicode.txt', 'rb+') as f:
            if sys.version_info.major == 3:
                s = f.read().decode()
            else:
                s = f.read()
        self.mgr = EtcdConfigManager(
            prefix=settings.ETCD_PREFIX, host=settings.ETCD_HOST,
            port=settings.ETCD_PORT,
            username=settings.ETCD_USERNAME, password=settings.ETCD_PASSWORD
        )

        self.env_config = {
            "A": 1, "B": "c", "D": {"e": "f"}, "E": 1,
            "C": {'c2': 1}, 'ENCODING': s
        }
        self.mgr.set_env_defaults('test', self.env_config)
        self.mgr.set_config_sets({
            'foo': {'A': 11},
            'bar': {'C': {'c3': 2}}})
        self.proxy = EtcdSettingsProxy()
        with open('manage.py', 'w') as f:
            f.write("testing artifact")

    def tearDown(self):
        try:
            os.remove('manage.py')
        except:
            pass

    def test_loader_etcd_index_in_manager(self):
        env = get_overwrites(settings.ETCD_ENV, None, settings.ETCD_DETAILS)
        self.assertIsNotNone(env)
        self.assertGreater(EtcdClusterState.etcd_index, 0)

    def test_username_password(self):
        self.assertEquals({'authorization': u'Basic dGVzdDp0ZXN0'},
                          self.mgr._client._get_headers())

    def test_proxy_starts_without_extensions(self):
        self.mgr._client.delete(self.mgr._base_config_set_path, recursive=True)
        p = EtcdSettingsProxy()
        self.assertIsNotNone(p)

    def test_proxy_starts_when_extensions_is_not_a_dir(self):
        self.mgr._client.delete(self.mgr._base_config_set_path, recursive=True)
        self.mgr._client.write(
            self.mgr._base_config_set_path,
            json.dumps('not_a_dict'))
        p = EtcdSettingsProxy()
        self.assertIsNotNone(p)

    def test_proxy_reads_initial_blob(self):
        self.assertEquals(1, self.proxy.A)
        self.assertEquals("c", self.proxy.B)

    def test_proxy_raises_attribute_errors_on_not_found(self):
        with self.assertRaises(AttributeError):
            self.proxy.KEY_THAT_IS_NOT_THERE

    def test_proxy_reads_django_settings(self):
        self.assertEquals('test', self.proxy.DJES_ENV)

    def test_proxy_gives_prio_to_env_over_django_settings(self):
        self.assertEquals(1, self.proxy.E)

    def test_proxy_can_be_viewed_as_dict(self):
        d = self.proxy.as_dict()
        for k, v in self.env_config.items():
            self.assertEqual(v, d[k])

    def test_proxy_uses_dynamic_settings(self):
        r = HttpRequest()
        r.META = {'HTTP_X_DYNAMIC_SETTING': 'foo'}
        self.proxy._req_getter = MagicMock(return_value=r)
        self.assertEqual(11, self.proxy.A)

    def test_proxy_dynamic_settings_handle_dict_overwrites(self):
        r = HttpRequest()
        r.META = {'HTTP_X_DYNAMIC_SETTING': 'bar'}
        self.proxy._req_getter = MagicMock(return_value=r)
        c = self.proxy.C
        self.assertEqual(1, c.get('c2'))
        self.assertEqual(2, c.get('c3'))

    def test_proxy_locates_uwsgi_file(self):
        self.proxy._locate_wsgi_file(None)
        self.assertEqual(None, self.proxy._wsgi_file)
        self.proxy._locate_wsgi_file(__file__)
        self.assertEqual(__file__, self.proxy._wsgi_file)
        self.proxy._locate_wsgi_file('etcd_settings/proxy.py')
        self.assertIsNotNone(
            re.match("^/(.*)/etcd_settings/proxy.py", self.proxy._wsgi_file))
        os.remove('manage.py')
        with self.assertRaises(IOError):
            self.proxy._locate_wsgi_file('file_that_cannot_exist.py')

    def test_loader_gets_overwrites(self):
        self.assertEqual(
            self.env_config,
            get_overwrites(settings.ETCD_ENV, None, settings.ETCD_DETAILS)
        )
