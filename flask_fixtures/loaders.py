"""
    flask_fixtures.loaders
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Classes for loading serialized fixtures data.

    :copyright: (c) 2015 Christopher Roach <ask.croach@gmail.com>.
    :license: MIT, see LICENSE for more details.
"""
from __future__ import absolute_import

import abc
import inspect
import os
import logging

from flask_fixtures import config
from flask_fixtures.config import JSON_PARSE_DATETIME
from .utils import print_info
import six

try:
    from dateutil.parser import parse as dtparse
except ImportError:
    print_info("""If you are using JSON for your fixtures, consider installing
        the dateutil library for more flexible parsing of dates and times.""")

    from datetime import datetime
    def dtparse(dtstring):
        """Returns a datetime object for the given string"""
        return datetime.strptime(dtstring, '%Y-%m-%d')

try:
    import simplejson as json
except ImportError:
    import json

try:
    import yaml
except ImportError:
    def load(self, filename):
        raise Exception("Could not load fixture '{0}'. Make sure you have PyYAML installed.".format(filename))
    yaml = type('FakeYaml', (object,), {
        'load': load
    })()


log = logging.getLogger(__name__)


class FixtureLoader(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def load(self):
        pass


class JSONLoader(FixtureLoader):

    extensions = ('.json', '.js')

    def load(self, filename):
        def _datetime_parser(dct):
            for key, value in list(dct.items()):
                try:
                    dct[key] = dtparse(value)
                except Exception:
                    pass
            return dct

        with open(filename) as fin:
            parse_datetime = config.settings.get(JSON_PARSE_DATETIME)
            if parse_datetime:
                return json.load(fin, object_hook=_datetime_parser)
            else:
                return json.load(fin)


class YAMLLoader(FixtureLoader):

    extensions = ('.yaml', '.yml')

    def load(self, filename):
        with open(filename) as fin:
            return yaml.load(fin)

_custom_loaders = []


def _is_loader(obj):
    return inspect.isclass(obj) and issubclass(obj, FixtureLoader)


def add(cls):
    """Add custom loader."""
    if not _is_loader(cls):
        raise ValueError("Unsupported loader class.")

    _custom_loaders.append(cls)


def remove(cls):
    """Remove custom loader."""
    if not _is_loader(cls):
        return

    _custom_loaders.remove(cls)


def _get_loaders_cls():
    loaders = []
    loaders.extend(_custom_loaders)
    for cls in FixtureLoader.__subclasses__():
        if cls not in _custom_loaders:
            loaders.append(cls)

    return loaders


def load(filename):
    name, extension = os.path.splitext(filename)
    for cls in _get_loaders_cls():
        # If a loader class has no extenions, log a warning so the developer
        # knows that it will never be used anyhwhere
        if not hasattr(cls, 'extensions'):
            log.warn("The loader '{0}' is missing extensions and will not be used.".format(cls.__name__))
            continue

        # Otherwise, check if the file's extension matches a loader extension
        for ext in cls.extensions:
            if extension == ext:
                return cls().load(filename)

    # None of the loaders matched, so raise an exception
    raise Exception("Could not load fixture '{0}'. Unsupported file format.".format(filename))


def extensions():
    return [ext for c in FixtureLoader.__subclasses__() for ext in c.extensions]
