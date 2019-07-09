# -*- coding: utf-8 -*-
# Copyright (c) 2014 Rackspace
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Compatibility module for Python 2 and 3 support."""
import sys

try:
    from urllib.parse import quote as urlquote
except ImportError:  # Python 2.x
    from urllib import quote as urlquote

try:
    from urllib.parse import urlencode
except ImportError:  # Python 2.x
    from urllib import urlencode

__all__ = ("to_bytes", "to_str", "urlquote", "urlencode")

PY3 = (3, 0) <= sys.version_info < (4, 0)
PY2 = (2, 6) <= sys.version_info < (2, 8)


if PY3:
    unicode = str  # Python 3.x


def to_str(b, encoding="utf-8"):
    """Ensure that b is text in the specified encoding."""
    if hasattr(b, "decode") and not isinstance(b, unicode):
        b = b.decode(encoding)
    return b


def to_bytes(s, encoding="utf-8"):
    """Ensure that s is converted to bytes from the encoding."""
    if hasattr(s, "encode") and not isinstance(s, bytes):
        s = s.encode(encoding)
    return s


from PyQt5.QtCore import QObject
from collections import Iterator
class CompKeyListDictIterator(Iterator):
     def __init__(self, keys, _dict):
        super(CompKeyListDictIterator, self).__init__()
        self.__keys = keys
        self.__dict = _dict
        self.__i = 0

     def next(self):
        if not self.__i < len(self.__keys):
            raise StopIteration
        result = self.__dict[self.__keys[self.__i]]
        self.__i+=1
        return result

class CompNamedTuple(QObject):
    _keys = []
    __virtual = {}
    def __init__(self, *args, **kwargs):
        super(CompNamedTuple, self).__init__()
        all_args = len(args)+len(kwargs)
        needed_args = len(self._keys)
        if all_args != needed_args:
            raise TypeError("Expect "+str(needed_args)+" args but got"+str(all_args))
        
        x=0
        while x < len(args) and x < len(self._keys):
            self.__virtual[self._keys[x]] = args[x]
            x+=1
        
        for key in kwargs.keys():
            if not key in self._keys:
                raise TypeError("Can not find kwarg with name "+key)
            self.__virtual[key] = kwargs[key]

    def __getattr__(self, key):
        if key in ["_keys","__virtual"]:
            return super.__getattr__(self, key)
        if key in self._keys:
            return self.__virtual[key]
        return super.__getattr__(self, key)

    def __setattr__(self, key, value):
        if key in ["_keys","__virtual"]:
            super.__setattr__(self, key, value)
            return
        if key in self._keys:
            self.__virtual[key] = value
            return
        super.__setattr__(self, key, value)

    def __getitem__(self, key):
        if type(key) == int:
            if not key < len(self._keys):
                raise TypeError(str(key)+" is out of index max "+str((len(self._keys)-1)))
            return self.__virtual[self._keys[key]]
        elif type(key) == str:
            if not key in self._keys:
                raise TypeError(key+" is not in key list "+", ".join(self._keys))
            return self.__virtual[key]
        raise TypeError("Unsupported index type "+str(type(key)))

    def __setitem__(self, key, value):
        if type(key) == int:
            if not key < len(self._keys):
                raise TypeError(str(key)+" is out of index max "+str((len(self._keys)-1)))
            self.__virtual[self._keys[key]] = value
            return
        elif type(key) == str:
            if not key in self._keys:
                raise TypeError(key+" is not in key list "+", ".join(self._keys))
            self.__virtual[key] = value
            return
        raise TypeError("Unsupported index type "+str(type(key)))

    def __iter__(self):
        return CompKeyListDictIterator(self._keys, self.__virtual)

    def __repr__(self):
        val = self.__class__.__name__+"(\n"
        for key in self._keys:
            val += key+"="+self.__virtual[key]+"\n"
        return val+")"

    def __hash__(self):
        return hash((tuple(self._keys), tuple(self.__virtual)))