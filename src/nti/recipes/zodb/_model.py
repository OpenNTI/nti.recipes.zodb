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

    def _owned(self, value):
        if isinstance(value, _Contained):
            # Refs are tuples.
            value = copy(value)
        elif isinstance(value, (list, tuple)):
            value = tuple(self._owned(v) for v in value)
        else:
            value = _Const(value)
        if hasattr(value, '__parent__'):
            value.__parent__ = self
        return value

    def _translate(self, kwargs):
        cls = type(self)
        values = {}
        for c in reversed(cls.mro()):
            for k, v in vars(c).items():
                if k.startswith('_') or callable(v):
                    continue
                # Backport to Python 2
                if hasattr(v, '__set_name__'):
                    v.__set_name__(c, k)
                # Give __get__ a chance, but only if
                # it's not hidden by a instance attribute.
                # (This is a bit weird, but it lets us use 'name'
                # both as a attribute and in our values)
                if k not in vars(self) or hasattr(v, '__set__'):
                    v = getattr(self, k)
                values[k] = v
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
            v = self._owned(v)
            if hasattr(v, '__name__'):
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

    def _write_indented_value(self, io, lines, part):
        with io.indented():
            if hasattr(lines, 'write_to'):
                lines.write_to(io, part)
                return

            for line in lines:
                if hasattr(line, 'write_to'):
                    line.write_to(io, part)
                else:
                    line = part.format_value(line)
                    io.begin_line(line)

    _key_value_sep = ' = '
    _skip_empty_values = False

    def _write_one(self, io, k, v, part):
        v = part.format_value(v)
        if not v and self._skip_empty_values:
            return
        io.begin_line(k, self._key_value_sep)

        if v:
            if isinstance(v, str):
                assert '\n' not in v
                io.append(v)
            else:
                # A list of lines.
                self._write_indented_value(io, v, part)

    def _write_header(self, io, part):
        "Does nothing"

    _write_trailer = _write_header

    def _values_to_write(self):
        return sorted(self.values.items())

    def _write_values(self, io, part):
        for k, v in self._values_to_write():
            self._write_one(io, k, v, part)

    def write_to(self, io, part=None):
        part = part if part is not None else self
        self._write_header(io, part)
        self._write_values(io, part)
        self._write_trailer(io, part)

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
        self.extends = tuple(e for e in extends if e is not None)
        self._defaults = {}

    def buildout_lookup(self, key, default=None):
        """
        By default, this is the same as :meth:`get`, but
        recipes running inside buildout that have a true picture
        of the precedence may replace this method to provide
        a lookup of the actual option value.
        """
        return self.get(key, default) # pragma: no cover

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

    def _write_header(self, io, part):
        assert part is self
        io.begin_line('[', self.name, ']')
        if self.extends:
            io.begin_line('<=')
            extends = [getattr(e, 'name', e) for e in self.extends]
            self._write_indented_value(io, extends, self)
        if 'recipe' in self.values:
            self._write_one(io, 'recipe', self.values['recipe'], part)

    def add_default(self, key, value):
        self._defaults[key] = value

    def _values_to_write(self):
        for k, v in super(Part, self)._values_to_write():
            if k != 'recipe':
                yield k, v

        for k, v in self._defaults.items():
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
        self.trailer = None
        if 'APPEND' in kwargs:
            self.trailer = kwargs.pop("APPEND")
            self.trailer.__parent__ = self
        _Values.__init__(self, kwargs)

    def _write_trailer(self, io, part):
        if self.trailer:
            with io.indented(self._body_indention):
                # It's always another snippet or a simple value.
                if hasattr(self.trailer, 'write_to'):
                    self.trailer.write_to(io, part)
                else:
                    io.begin_line(part.format_value(self.trailer))


class ZConfigSection(_NamedValues, ZConfigSnippet):

    def __init__(self, _section_key, _section_name, *sections, **kwargs):
        ZConfigSnippet.__init__(self, **kwargs)
        _NamedValues.__init__(self, _section_key, kwargs)
        self.values.pop('APPEND', None)
        self.name = _section_key
        self.zconfig_name = _section_name
        self.sections = [copy(s) for s in sections]
        for s in self.sections:
            s.__parent__ = self

    def _write_values(self, io, part):
        with io.indented(self._body_indention):
            super(ZConfigSection, self)._write_values(io, part)

    def _write_header(self, io, part):
        io.begin_line('<', part.format_value(self.name))
        if self.zconfig_name:
            io.append(' ', part.format_value(self.zconfig_name))
        io.append('>')

        with io.indented('    '):
            for section in self.sections:
                section.write_to(io)

    def _write_trailer(self, io, part):
        ZConfigSnippet._write_trailer(self, io, part)
        io.begin_line("</",
                      part.format_value(self.name),
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
        return self.__str__()

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
    hyphenated = False

    def __init__(self, const):
        self.const = const

    def __bool__(self):
        return self.const is not None

    __nonzero__ = __bool__

    def lower(self):
        return self.const.lower()

    def format_for_part(self, part):
        return part.format_value(self.const)

    def __str__(self):
        return str(self.const)

    def hyphenate(self):
        inst = type(self)(self.const)
        inst.hyphenated = True
        return inst

class hyphenated(_Const):
    hyphenated = True

class Default(_Const):
    """
    A default value is a type of constant that will defer to a
    setting in its part's inheritance hierarchy if one is available.

    The setting will always be the same as what this object is
    bound to in its class, but the name that gets written to
    ZCML may be hyphenated.
    """

    _bound_name = None

    def __set_name__(self, klass, name):
        # Called in 3.6+
        self._bound_name = name

    def __get__(self, inst, cls):
        return self

    def format_for_part(self, part):
        part.add_default(self._bound_name, self.const)
        return RelativeRef(self._bound_name).format_for_part(part)

class NoDefault(Default):
    """
    A value that can be set, but which has no default and thus
    doesn't appear in the configuration unless set.
    """

    def __init__(self, const=None):
        assert const is None
        Default.__init__(self, const)

    def format_for_part(self, part):
        buildout_value = part.buildout_lookup(self._bound_name)
        if buildout_value is not None:
            part.add_default(self._bound_name, buildout_value)
            return RelativeRef(self._bound_name).format_for_part(part)
        # Return a false value to suppress printing
        return ''

    def lower(self):
        return '' # pragma: no cover

    __str__ = lower


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
