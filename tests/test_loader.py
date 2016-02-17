from django.test import TestCase
from etcd_settings.loader import get_overwrites


class TestLoader(TestCase):

    def test_get_overwrites_without_etcd(self):
        overwrites = get_overwrites(
            'unittest', 'tests.loader_dev_params', None)
        self.assertEqual('bar', overwrites['FOO'])
