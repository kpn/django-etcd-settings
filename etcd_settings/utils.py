import sys
import json
import datetime
from dateutil.parser import parse as parse_date
from collections import Mapping
from threading import Thread


def attrs_to_dir(mod):
    data = {}
    for attr in dir(mod):
        if attr == attr.upper():
            data[attr] = getattr(mod, attr)
    return data


def dict_rec_update(d, u):
    """Nested update of a dict, handy for overriding settings"""
    # https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    for k, v in u.iteritems():
        if isinstance(v, Mapping):
            r = dict_rec_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class Task(Thread):
    """
    The Threaded object returned by the @threaded decorator below
    """

    def __init__(self, method, *args, **kwargs):
        super(Task, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._result = None
        self.__exc_info = None

    def run(self):
        try:
            self._result = self.method(*self.args, **self.kwargs)
        except:
            self.__exc_info = sys.exc_info()

    @property
    def result(self):
        self.join()
        if self.__exc_info is not None:
            raise self.__exc_info[0], self.__exc_info[1], self.__exc_info[2]
        else:
            return self._result


def threaded(method):

    def get_thread(*args, **kwargs):
        t = Task(method, *args, **kwargs)
        t.start()
        return t

    return get_thread


class CustomJSONEncoder(json.JSONEncoder):

    custom_type_key = '_custom_type'
    custom_type_value_key = 'value'
    DECODERS = {'datetime': parse_date}

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {self.custom_type_key: 'datetime',
                    self.custom_type_value_key: obj.isoformat()}
        else:
            return super(CustomJSONEncoder, self).default(obj)


def custom_json_decoder_hook(obj):

    ct = obj.get(CustomJSONEncoder.custom_type_key, None)
    if ct is not None:
        value = obj.get(CustomJSONEncoder.custom_type_value_key)
        return CustomJSONEncoder.DECODERS[ct](value)
    else:
        return obj
