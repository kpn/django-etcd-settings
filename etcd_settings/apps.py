from django.apps import AppConfig
from etcd_settings.proxy import proxy


class EtcdMonitor(AppConfig):

    def ready(self):
        proxy.start_monitors()
