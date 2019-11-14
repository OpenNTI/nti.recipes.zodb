# -*- coding: utf-8 -*-
"""
Building blocks to model a configuration.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from contextlib import contextmanager
from collections import namedtuple
from copy import copy

class ValueWriter(object):

    def __init__(self):
        self._lines = []
        self.current_indent = ''

    def getvalue(self):
        return '\n'.join(self._lines)

    @contextmanager
    def indented(self, by='    '):
        prev_indent = self.current_indent
        self.current_indent = prev_indent + by
        yield self
        self.current_indent = prev_indent


    def begin_line(self, *substrs):
        self._lines.append(self.current_indent + ''.join(substrs))

    def append(self, *substrs):
        self._lines[-1] += ''.join(substrs)

class _Contained(object):
    __parent__ = None
    __name__ = None

class _Values(_Contained):
    "A dict-like mapping if string keys to string values."

    def __init__(self, values):
        self.values = self._translate(dict(values))
        self.keys = self.values.keys
        self.items = self.values.items


    def _translate(self, kwargs):
        cls = type(self)
        values = {}
        for c in reversed(cls.mro()):
            local_values = {
                k: v
                for k, v in vars(c).items()
                if not k.startswith('_') and not callable(v)
            }
            values.update(local_values)
        values.update(kwargs)

        # Transform kwargs that had _ back into -
        keys = list(values)
        for k in keys:
            v = values[k]
            cls_value = getattr(cls, k, None)
            if getattr(cls_value, 'hyphenated', None) \
               or getattr(values[k], 'hyphenated', None):
                values.pop(k)
                k = k.replace('_', '-')
            elif getattr(cls_value, 'new_name', None):
                values.pop(k)
                k = cls_value.new_name
            if isinstance(v, _Contained):
                v = copy(v)
            else:
                v = _Const(v)
            v.__parent__ = self
            v.__name__ = k
            values[k] = v
        return values

    def with_settings(self, **kwargs):
        new_inst = copy(self)
        new_inst.values = copy(self.values)
        new_inst.values.update(kwargs)
        return new_inst

    def ref(self):
        return Ref(self.__parent__.__name__, self.__name__)

    def __getitem__(self, key):
        return self.values[key]

    def __delitem__(self, key):
        del self.values[key]

    def format_value(self, value):
        if hasattr(value, 'format_for_part'):
            value = value.format_for_part(self)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'
        elif isinstance(value, int):
            value = str(value)
        return value

    def _write_indented_value(self, io, lines):
        with io.indented():
            if hasattr(lines, 'write_to'):
                lines.write_to(io)
                return

            for line in lines:
                if hasattr(line, 'write_to'):
                    line.write_to(io)
                else:
                    line = self.format_value(line)
                    io.begin_line(line)

    _key_value_sep = ' = '
    _skip_empty_values = False

    def _write_one(self, io, k, v):
        v = self.format_value(v)
        if not v and self._skip_empty_values:
            return
        io.begin_line(k, self._key_value_sep)

        if v:
            if isinstance(v, str):
                assert '\n' not in v
                io.append(v)
            else:
                # A list of lines.
                self._write_indented_value(io, v)

    def _write_header(self, io):
        "Does nothing"

    _write_trailer = _write_header

    def _values_to_write(self):
        return sorted(self.values.items())

    def _write_values(self, io):
        for k, v in self._values_to_write():
            self._write_one(io, k, v)

    def write_to(self, io):
        self._write_header(io)
        self._write_values(io)
        self._write_trailer(io)

    def __str__(self):
        io = ValueWriter()
        self.write_to(io)
        return io.getvalue()

class _NamedValues(_Values):

    class uses_name(object):
        def __init__(self, template):
            self.template = template

        def format_for_part(self, part):
            template = part.format_value(self.template)
            return template % (part.name,)

    def __init__(self, name, values):
        # extends is a tuple of named parts we extend.
        self.name = self.__name__ = name
        _Values.__init__(self, values)

    def named(self, name):
        new_inst = self.with_settings()
        new_inst.name = name
        return new_inst

class Part(_NamedValues):
    """
    A buildout configuration part (or section).

    :param extends: A tuple of strings or other parts.
        Remember that in buildout, *later* elements in the
        list take priority over earlier ones, not vice versa.
        (The opposite of Python's class MRO.)
    """

    def __init__(self, _name, extends=(), **kwargs):
        super(Part, self).__init__(_name, kwargs)
        self.extends = extends

    def __getitem__(self, key):
        try:
            return super(Part, self).__getitem__(key)
        except KeyError:
            for extension in reversed(self.extends):
                try:
                    v = extension[key]
                except (TypeError, KeyError):
                    pass
                else:
                    if hasattr(v, '__parent__'):
                        v = copy(v)
                        v.__parent__ = self
                    return v
            # On Python 2, if we raised an exception in the
            # loop, it will overwrite the KeyError we
            # originally caught, and we could wind up with a TypeError,
            # which is not what we want.
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _write_header(self, io):
        io.begin_line('[', self.name, ']')
        if self.extends:
            io.begin_line('<=')
            extends = [getattr(e, 'name', e) for e in self.extends]
            self._write_indented_value(io, extends)
        if 'recipe' in self.values:
            self._write_one(io, 'recipe', self.values['recipe'])

    def _values_to_write(self):
        for k, v in super(Part, self)._values_to_write():
            if k != 'recipe':
                yield k, v

# ZConfig.schemaless is a module that contains a parser for existing
# configurations. It creates Section objects from that module. These
# extend dict and know how to write themselves through ``__str__(self,
# prefix='')``.  They handle imports but not defines.

class ZConfigSnippet(_Values):
    _skip_empty_values = True
    _key_value_sep = ' '
    _body_indention = '  '

    def __init__(self, **kwargs):
        self.trailer = kwargs.pop("APPEND", None)
        _Values.__init__(self, kwargs)

    def _write_trailer(self, io):
        __traceback_info__ = self.trailer
        if self.trailer:
            with io.indented(self._body_indention):
                # It's always another snippet or a simple value.
                if hasattr(self.trailer, 'write_to'):
                    self.trailer.write_to(io)
                else:
                    io.begin_line(self.format_value(self.trailer))


class ZConfigSection(_NamedValues, ZConfigSnippet):

    def __init__(self, _section_key, _section_name, *sections, **kwargs):
        ZConfigSnippet.__init__(self, **kwargs)
        _NamedValues.__init__(self, _section_key, kwargs)
        self.values.pop('APPEND', None)
        self.name = _section_key
        self.zconfig_name = _section_name
        self.sections = sections

    def _write_values(self, io):
        with io.indented(self._body_indention):
            super(ZConfigSection, self)._write_values(io)

    def _write_header(self, io):
        io.begin_line('<', self.format_value(self.name))
        if self.zconfig_name:
            io.append(' ', self.format_value(self.zconfig_name))
        io.append('>')

        with io.indented('    '):
            for section in self.sections:
                section.write_to(io)

    def _write_trailer(self, io):
        ZConfigSnippet._write_trailer(self, io)
        io.begin_line("</",
                      self.format_value(self.name),
                      '>')


class Ref(_Contained, namedtuple('_SubstititionRef', ('part', 'setting'))):

    def __new__(cls, part, setting=None):
        if setting is None:
            setting = part
            part = ''
        return super(Ref, cls).__new__(cls, part, setting)

    def __str__(self):
        return '${%s:%s}' % self

    def format_for_part(self, _):
        return str(self)

    def __copy__(self):
        return self

    def __add__(self, other):
        """
        Add concatenates the values on the same line.
        """
        return _CompoundValue(self, other)

    def __div__(self, other):
        """
        Like pathlib, / can be used to join a ref with another
        ref or string to compute a path value.
        """
        return _CompoundValue(self, '/', other)

    def __rdiv__(self, other):
        return _CompoundValue(other, '/', self)

    __truediv__ = __div__ # Py2
    __rtruediv__ = __rdiv__ # Py2

    def hyphenate(self):
        return _HyphenatedRef(self.part, self.setting)

class RelativeRef(Ref):
    """A reference that will be resolved within the current part."""

    def __new__(cls, setting):
        # pylint:disable=signature-differs
        return Ref.__new__(cls, '', setting) # pylint:disable=too-many-function-args

class _HyphenatedRef(Ref):
    __slots__ = ()
    hyphenated = True

class _Const(_Contained):

    def __init__(self, const):
        self.const = const

    def lower(self):
        return self.const.lower()

    def format_for_part(self, part):
        return part.format_value(self.const)

    def __str__(self):
        return str(self.const)

class hyphenated(_Const):
    hyphenated = True

class renamed(object):

    def __init__(self, new_name):
        self.new_name = new_name

class _CompoundValue(_Contained):
    def __init__(self, *values):
        self._values = values

    def __add__(self, other):
        v = self._values + (other,)
        return type(self)(*v)

    def __div__(self, other):
        v = self._values + ('/', other)
        return type(self)(*v)

    def __rdiv__(self, other):
        values = self._values
        # Careful not to double path seps.
        if isinstance(self._values[0], str) and self._values[0].startswith('/'):
            values = (self._values[0][1:],) + self._values[1:]

        v = (other, '/') + values
        return type(self)(*v)

    __truediv__ = __div__ # Py2
    __rtruediv__ = __rdiv__

    def format_for_part(self, part):
        strs = []
        for v in self._values:
            strs.append(str(part.format_value(v)))
        return ''.join(strs)

    def __str__(self):
        part = Part('<invalid part>')
        return self.format_for_part(part)



class ChoiceRef(_Contained):
    """
    References a different section:setting based on looking up the
    part's name in the section map.
    """
    __slots__ = ('section_map', 'setting')

    def __init__(self, section_map, setting):
        self.section_map = section_map
        self.setting = setting

    def format_for_part(self, part):
        section = self.section_map[part.name]
        return str(Ref(section, self.setting))
