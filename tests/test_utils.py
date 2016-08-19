import logging
import unittest

from etcd_settings import utils


class TestLoggingFilter(unittest.TestCase):

    def setUp(self):
        self.logger_filter = utils.IgnoreMaxEtcdRetries()

    def test_log_record_without_args(self):
        self.assertTrue(
            self.logger_filter.filter(
                logging.LogRecord(
                    'etcd.client',
                    logging.ERROR,
                    '/',
                    0,
                    'Read timed out',
                    tuple(),
                    None
                )
            )
        )

    def test_log_record_match(self):
        self.assertFalse(
            self.logger_filter.filter(
                logging.LogRecord(
                    'etcd.client',
                    logging.ERROR,
                    '/',
                    0,
                    'Error %s exception %s',
                    ('Read timed out', 'MaxRetryError'),
                    None
                )
            )
        )
