from .manager import EtcdConfigManager


def get_overwrites(env, dev_params, etcd_details):
    overwrites = {}
    if etcd_details is not None:
        mgr = EtcdConfigManager(dev_params, **etcd_details)
        overwrites = mgr.get_env_defaults(env)
    else:
        overwrites = EtcdConfigManager.get_dev_params(dev_params)
    return overwrites
