from django.apps import AppConfig
from etcd_settings.proxy import proxy


class EtcdMonitor(AppConfig):

    name = 'etcd_settings'
    verbose_name = 'EtcdMonitor starting the threads for long polling'

    def ready(self):
        proxy.start_monitors()
