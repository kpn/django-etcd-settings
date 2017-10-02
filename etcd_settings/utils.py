import copy
import os
from collections import Mapping


def dict_rec_update(d, u):
    """Nested update of a dict, handy for overriding settings"""
    # https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    for k, v in u.items():
        if isinstance(v, Mapping):
            r = dict_rec_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def find_project_root(root_indicator='manage.py', current=os.getcwd()):
    parent = os.path.dirname(current)
    if root_indicator in os.listdir(current):
        return current
    elif current == parent:
        # We are at '/' already!
        raise IOError('Not found: {}'.format(root_indicator))
    else:
        return find_project_root(root_indicator, parent)


def copy_if_mutable(value):
    """
    Copy function handling mutable values (only dicts and lists).
    """
    if type(value) in (dict, list):
        return copy.deepcopy(value)
    return value
