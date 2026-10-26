"""
Runtime annotation check behind ``@_check_types.do``.

``do`` is applied to essentially every function and method in the package. In a
normal run it returns the function untouched. When it is switched on
(``_ENABLED`` below) it wraps the function and, on every call that is checked,
compares the annotations with what really arrived: each parameter that has a
hint, and the return value (or each item a generator yields). What fits is
forgotten; only what does NOT fit is recorded, into a SQLite database that
``diagnostics/type_audit_report.py`` reads.

Two tables hold what is found. ``functions`` has one row per function that was
called wrongly: its name, its signature and return type as annotated, and the
source file and line. ``calls`` has one row per wrong call: the calling
function, the file and line it is in, the signature of the call as it was made
(the type of everything that was passed) and the type that came back, written
next to the annotated ones so the mismatch can be read by eye. A call that
raised has no return type. Before a row is written the database is asked: is
there a function with this name and source file (take its id, add it only if
not), and is there already a call with that function id, calling function,
calling file, signature and return type (add it only if not). So a repeat is
never written; a row appears only when the calling function, the file or the
signature differs. Up to ``_SITE_LIMIT`` rows are kept per (function, parameter,
type that arrived).

How a value is judged (``_accepts``): a hint is read once per function, on its
first checked call (when the module is complete), into a small tree. A class
accepts its subclasses and anything registered with it (``Iterable`` takes a
``dict_keys``), ``float`` also takes an ``int``, ``X | None`` and ``Union`` take
any member, ``list[int]`` / ``dict[str, X]`` / ``tuple[int, ...]`` also look at
the contents that were sampled (below), ``Callable`` takes anything that has
``__call__``, and a hint written as a quoted name that cannot be imported at
run time (a ``TYPE_CHECKING`` import) is matched by class name against the
type's bases; a bare ``_Name`` that cannot be imported is an import alias
(``ObjectBase as _ObjectBase``), so it is matched as ``Name`` and never held against
anything else. An ``__init__`` builds the object and returns nothing (by project
convention it has no return annotation), so its return is neither checked nor
reported: its rows show the parameters only. Whatever cannot be understood (a
``TypeVar``, a ``Protocol``, a ``Literal``, ``Self``, a numpy scalar for a number hint)
is never recorded: the check reports only what it is sure about.

Containers are judged by their contents too. Up to 8 items are looked at, not
all: every item of a list, set or tuple with 8 or fewer, otherwise 8 spread
evenly over a list (always the first and the last), the first 8 of a set or
tuple, and for a dict the first 7 entries and the last (keys and values apart).
Containers inside containers are looked into the same way, three levels down.
An item that is not looked at is not seen, so a lone odd item in the middle of a
long list can be missed. ``*args`` and ``**kwargs`` are not checked, nor are
defaults that were not overridden.

Settings are the constants near the top of this file: ``_ENABLED``,
``_FULL_CALLS`` (the first N calls of each function are all checked),
``_STRIDE`` (after that only every Nth call is checked; 1 checks every call),
``_FLUSH_SECONDS``, ``_SITE_LIMIT``, ``_SAMPLES`` and ``_SHAPE_DEPTH``. The
database is ``type_audit.sqlite3`` in the repo root unless the environment
variable ``HARNESS_TYPE_AUDIT_DB`` names another file. Delete the file to start
over.

Where the data lives: wrong calls are kept in plain lists while the app runs (a
call that fits costs a few dict lookups). Every flush interval they are written
into a SQLite database that exists only in memory, and that database is written
to the file in one transaction -- only when something changed -- and once more
when the process ends (``atexit`` for the app, a ``multiprocessing`` finalizer
for its worker processes). Both writes use the look-up-then-add rule above, so
the app, its worker processes and every session add to the same file without
repeating a row. A process that is killed, or a worker that ends with
``os._exit``, loses at most the last interval. If the file cannot be written
the data stays in memory and the dump is retried on the next tick. A forked
child (not Windows) is not checked: its records would only repeat its parent's.

This module is deliberately standalone (standard library only, no package
imports) so it can be imported from anywhere without import cycles, and nothing
it does is allowed to raise into the app: a failure of the check is printed once
to the real stderr and the call goes on.

Apart from the signature of ``do`` itself, this module is deliberately free of
type annotations. ``do`` is typed ``Callable[_P, _R] -> Callable[_P, _R]`` (a
ParamSpec): the one form that type checkers read as "same signature in, same
signature out". A bare ``-> Callable`` makes them see every decorated function as
``(...) -> Unknown`` (no argument or return checking at any call site), and leaving
``do`` unannotated only works in some checkers, by accident of how they guess a
decorator's result. Nothing ``do`` calls is annotated, so none of the machinery can
leak a type into what ``do`` returns. Do not add hints to the rest of this file.
"""


from typing import ParamSpec, TypeVar, cast
from collections.abc import Callable

import ast
import atexit
import builtins
import functools
import inspect
import multiprocessing.util
import os
import sqlite3
import sys
import threading
import time
import types
import typing


# HARNESS_TYPE_AUDIT
_ENABLED = 0

# HARNESS_TYPE_AUDIT_FULL
_FULL_CALLS = 1000

# HARNESS_TYPE_AUDIT_STRIDE
_STRIDE = 8

# HARNESS_TYPE_AUDIT_FLUSH
_FLUSH_SECONDS = 10

# call sites: different callers kept per (function, slot, type), and how many of a type's first occurrences are looked at

# HARNESS_TYPE_AUDIT_SITES
_SITE_LIMIT = 5

_SITE_CALLS = 10

# how much of a container is looked at: items sampled from a list / dict / set, tuples up to this many items, and this
# many levels of containers inside containers

# HARNESS_TYPE_AUDIT_SAMPLES
_SAMPLES = 8
_MAX_TUPLE = 8

# HARNESS_TYPE_AUDIT_DEPTH
_SHAPE_DEPTH = 3

# call sites inside the repo are stored relative to it ("harness_designer/ui/x.py"), which keeps the file smaller
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep

# a forked child gets a copy of its parent's counters; it must not write them again
_PID = os.getpid()
_STARTED = time.strftime('%Y-%m-%d %H:%M:%S')

# first parameter names that mean "the bound instance / class", never recorded
_RECEIVERS = ('self', 'cls', 'mcs', 'mcls', 'metacls')


_FROZEN = hasattr(sys, 'frozen')

# for the signature of ``do`` only -- see the module docstring
_P = ParamSpec('_P')
_R = TypeVar('_R')

_NoneType = type(None)


def _db_path():
    path = os.environ.get('HARNESS_TYPE_AUDIT_DB', '')
    if path:
        return path

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(root, 'type_audit.sqlite3')


# the in-memory database and the file share this schema. `functions` is every function that was called wrongly, as it is
# annotated (one row per name + source file); `calls` is one row per wrong call: who made it and what it passed, next to the
# signature in `functions` (one row per function + calling function + calling file + signature + return type; the line is
# kept but is not part of what makes a call the same)
_SCHEMA = '''
CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    signature TEXT NOT NULL,
    return_type TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    UNIQUE (name, file)
);

CREATE TABLE IF NOT EXISTS calls (
    func_id INTEGER NOT NULL,
    caller TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    signature TEXT NOT NULL,
    return_type TEXT NOT NULL,
    UNIQUE (func_id, caller, file, signature, return_type)
);
'''


class _FuncState:
    """Everything the check keeps about one decorated function."""

    __slots__ = (
        'module', 'qualname', 'params', 'file', 'line',
        'positional', 'first', 'keywords', 'func', 'constructor',
        'calls', 'yields', 'trees', 'verdicts', 'signature', 'name', 'rows',
        'folded', 'seen', 'distinct', 'db_id',
    )

    def __init__(self, module, qualname, params, file, line, positional, first, keywords, func):
        self.module = module
        self.qualname = qualname
        self.params = params
        self.file = file
        self.line = line

        # positional parameter names (receiver included), where the checked
        # ones start, and the names a keyword can use
        self.positional = positional
        self.first = first
        self.keywords = keywords

        # the function itself, for its annotations and its signature;
        # they are read on the first checked call
        self.func = func

        # an __init__ builds the object and returns nothing (and by project
        # convention has no return annotation): its
        # return is neither checked nor reported
        self.constructor = func.__name__ == '__init__'

        self.calls = 0
        self.yields = 0

        # slot -> the hint as a tree; (slot, type or (type, contents)) -> 0 fits,
        # 1 does not fit, 2 the contents decide
        self.trees = {}
        self.verdicts = {}

        # (parameters, return type) of the annotated signature as text,
        # and the name the function is stored under; both
        # worked out when the first row is written
        self.signature = None
        self.name = None

        # one tuple per wrong call: (caller, file, line, calling signature,
        # what it returned). Only ever appended to;
        # `folded` is how many of them are already in the in-memory database
        self.rows = []
        self.folded = 0

        # (caller, file, calling signature, what it returned) of every row:
        # a repeat in this process is not looked up again
        self.seen = set()

        # (slot, type that arrived) -> how many rows exist for it
        self.distinct = {}
        self.db_id = None


class _Busy(threading.local):
    """
    Per-thread flag set while a type is being named,
    so naming it cannot recurse into the recorder.
    """

    on = False


_busy = _Busy()
_LOCK = threading.Lock()
_STATES = []
_BY_CODE = {}
_ACTIVE = []
_RUN = {}
_REPORTED = set()


def _fail(where, exc):
    message = f'check_types: {where}: {type(exc).__name__}: {exc}'
    if message in _REPORTED:
        return

    _REPORTED.add(message)

    try:
        sys.__stderr__.write(message + '\n')
    except Exception:  # NOQA
        pass


# frames in this file are the recorder's own;
# the call site is the first frame outside it
_OWN_FILE = _fail.__code__.co_filename


# -------- types -> text

def _key_of(value, depth):
    t = type(value)
    if (
        depth > 0 and
        (t is list or t is tuple or t is dict or t is set or t is frozenset)
    ):
        return t, _shape(value, depth - 1)

    return t


def _shape(value, depth):
    """
    What a container holds, as hashable data: a tuple's items by position,
    otherwise the SET of types sampled from it.
    """

    t = type(value)
    if t is tuple:
        items = tuple(_key_of(item, depth) for item in value[:_MAX_TUPLE])
        if len(value) > _MAX_TUPLE:
            items += (Ellipsis,)

        return items

    if not value:
        return None

    if t is dict:
        # the first entries, then the last one (cheap on a dict),
        # keys and values kept apart
        key_types = set()
        value_types = set()
        taken = 0
        limit = _SAMPLES - 1
        if limit < 1:
            limit = 1

        for key, item in value.items():
            key_types.add(_key_of(key, depth))
            value_types.add(_key_of(item, depth))
            taken += 1
            if taken >= limit:
                break

        if _SAMPLES > 1 and len(value) > taken:
            last = next(reversed(value))
            key_types.add(_key_of(last, depth))
            value_types.add(_key_of(value[last], depth))

        return frozenset(key_types), frozenset(value_types)

    if t is list:
        size = len(value)
        if size <= _SAMPLES:
            sampled = value
        elif _SAMPLES == 1:
            sampled = (value[0],)
        else:
            # evenly spaced, always including the first and the last
            sampled = [value[(index * (size - 1)) // (_SAMPLES - 1)] for index in range(_SAMPLES)]

        return frozenset(_key_of(item, depth) for item in sampled)

    # set / frozenset: the first few in iteration order
    item_types = set()
    taken = 0
    for item in value:
        item_types.add(_key_of(item, depth))
        taken += 1
        if taken >= _SAMPLES:
            break

    return frozenset(item_types)


def _call_mark(t):
    """
    ``__call__`` when the class or a base of it defines one
    (so an instance can be called), ``__nocall__`` when not.
    """

    for base in t.__mro__:
        if '__call__' in vars(base):
            return '__call__'

    return '__nocall__'


def _render_union(keys):
    """The sampled types as one text, ``a | b``, in a fixed order."""

    return ' | '.join(sorted({_render(key) for key in keys}))


def _render(key):
    if isinstance(key, type):
        if key is _NoneType:
            return 'None'

        return _class_label(key)

    t, shape = key
    base = _render(t)

    if t is tuple:
        if not shape:
            return f'{base}[()]'

        parts = []
        for item in shape:
            if item is Ellipsis:
                parts.append('...')
            else:
                parts.append(_render(item))

        return f'{base}[{", ".join(parts)}]'

    if shape is None:
        return base

    if t is dict:
        return f'{base}[{_render_union(shape[0])}, {_render_union(shape[1])}]'

    return f'{base}[{_render_union(shape)}]'


# ----------------- the annotation check
#
# A hint is turned into a small tree of _Hint nodes once per function and slot,
# on the first checked call (when the module is complete):
#
#   any  none  unknown  ellipsis  callable  type
#   cls    .cls = a class; takes subclasses, registered virtual
#          subclasses, int for float ...
#   name   .name = a quoted name that could not be imported at run time:
#            matched by class name against the bases, then against every
#            class a loaded module has under that name (so an alias such
#            as `ConfigEditor3DType = ConfigDB` works)
#   alias  .name = a bare `_Name` that could not be imported:
#            an import alias (`ObjectBase as _ObjectBase`), so it is matched
#            as `Name`, and anything that does not match is left alone because
#            what the alias stands for is not known
#   union  .args = the members
#   gen    .cls = list / dict / tuple / Iterable ..., .args = what it holds:
#            list[int], dict[str, X], tuple[int, ...] ...
#
# _accepts() then answers for the type (or type + sampled contents) that arrived:
#   2 it fits, 1 cannot tell, 0 it does not fit. Only 0 is ever recorded, so
#   whatever cannot be understood is never reported.

class _Hint:
    """
    One node of a hint tree; `kind` says which of the shapes above it is.
    """

    __slots__ = ('kind', 'cls', 'name', 'args')

    def __init__(self, kind, cls=None, name='', args=()):
        self.kind = kind
        self.cls = cls
        self.name = name
        self.args = args


_ANY = _Hint('any')
_NONE = _Hint('none')
_UNKNOWN = _Hint('unknown')
_ELLIPSIS = _Hint('ellipsis')
_CALLABLE = _Hint('callable')
_TYPE_OF = _Hint('type')
_MISSING = object()

# typing names that mean nothing without the machinery behind them
_VAGUE_NAMES = frozenset(('Self', 'LiteralString', 'Never', 'NoReturn',
                          'TypeVar', 'ParamSpec', 'Concatenate', 'TypeGuard',
                          'TypeAlias', 'Unpack'))

_YIELDING = frozenset(('Iterator', 'Iterable', 'Generator'))

_SIGNATURES = {}


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value

    if not isinstance(node, ast.Name):
        return None

    parts.append(node.id)

    return '.'.join(reversed(parts))


def _lookup(dotted, scope):
    """
    What a dotted name means in the function's module (or builtins);
    _MISSING when it is not there at run time.
    """

    first, _, rest = dotted.partition('.')
    found = scope.get(first, _MISSING)
    if found is _MISSING:
        found = vars(builtins).get(first, _MISSING)
        if found is _MISSING:
            return _MISSING

    if rest:
        for part in rest.split('.'):
            try:
                found = getattr(found, part)
            except AttributeError:
                return _MISSING

    return found


def _tree_of(ann, scope, depth):
    if depth > 12:
        return _UNKNOWN

    if ann is None or ann is _NoneType:
        return _NONE

    if ann is Ellipsis:
        return _ELLIPSIS

    if ann is typing.Any or ann is object:
        return _ANY

    if isinstance(ann, str):
        return _tree_of_text(ann, scope, depth + 1)

    if isinstance(ann, typing.ForwardRef):
        return _tree_of_text(ann.__forward_arg__, scope, depth + 1)

    if isinstance(ann, typing.NewType):
        return _tree_of(ann.__supertype__, scope, depth + 1)  # NOQA

    origin = typing.get_origin(ann)
    if origin is not None:
        args = typing.get_args(ann)

        if origin is typing.Union or origin is types.UnionType:
            return _Hint('union',
                         args=tuple(_tree_of(arg, scope, depth + 1) for arg in args))

        if origin is typing.Annotated:
            return _tree_of(args[0], scope, depth + 1)

        if origin is Callable:
            return _CALLABLE

        if origin is type:
            return _TYPE_OF

        if isinstance(origin, type):
            return _Hint('gen', origin,
                         args=tuple(_tree_of(arg, scope, depth + 1) for arg in args))

        return _UNKNOWN

    if isinstance(ann, type):
        return _Hint('cls', ann)

    return _UNKNOWN


def _tree_of_text(text, scope, depth):
    try:
        node = ast.parse(text.strip(), mode='eval').body
    except SyntaxError:
        return _UNKNOWN

    return _tree_of_node(node, scope, depth)


def _tree_of_node(node, scope, depth):
    if depth > 12:
        return _UNKNOWN

    if isinstance(node, ast.Constant):
        if node.value is None:
            return _NONE

        if node.value is Ellipsis:
            return _ELLIPSIS

        if isinstance(node.value, str):
            return _tree_of_text(node.value, scope, depth + 1)

        return _UNKNOWN

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _Hint('union',
                     args=(_tree_of_node(node.left, scope, depth + 1),
                           _tree_of_node(node.right, scope, depth + 1)))

    if isinstance(node, (ast.Name, ast.Attribute)):
        dotted = _dotted(node)
        if dotted is None:
            return _UNKNOWN

        found = _lookup(dotted, scope)
        if found is not _MISSING:
            return _tree_of(found, scope, depth + 1)

        last = dotted.rpartition('.')[2]
        if last == 'Any':
            return _ANY

        if last in _VAGUE_NAMES:
            return _UNKNOWN

        if last.startswith('_') and '.' not in dotted:
            return _Hint('alias', name=last.lstrip('_'))

        return _Hint('name', name=last)

    if isinstance(node, ast.Subscript):
        base = _dotted(node.value)
        if base is None:
            return _UNKNOWN

        elements = [node.slice]
        if isinstance(node.slice, ast.Tuple):
            elements = list(node.slice.elts)

        last = base.rpartition('.')[2]

        if last == 'Union' or last == '_Union':
            return _Hint('union',
                         args=tuple(_tree_of_node(element, scope, depth + 1)
                                    for element in elements))

        if last == 'Optional':
            return _Hint('union',
                         args=(_tree_of_node(elements[0], scope, depth + 1), _NONE))

        if last == 'Annotated':
            return _tree_of_node(elements[0], scope, depth + 1)

        if last == 'Literal':
            return _UNKNOWN

        if last == 'Callable':
            return _CALLABLE

        if last == 'type' or last == 'Type':
            return _TYPE_OF

        found = _lookup(base, scope)
        if found is _MISSING:
            # the contents of a hint whose class cannot be
            # imported here cannot be checked
            return _Hint('name', name=last)

        origin = typing.get_origin(found)
        if origin is None:
            origin = found

        if isinstance(origin, type):
            return _Hint('gen', origin,
                         args=tuple(_tree_of_node(element, scope, depth + 1)
                                    for element in elements))

        return _UNKNOWN

    return _UNKNOWN


def _wants_contents(tree):
    """
    True when the hint says something about what is inside a
    container (list[int], not just list).
    """

    if tree.kind == 'gen':
        return bool(tree.args)

    if tree.kind == 'union':
        for member in tree.args:
            if _wants_contents(member):
                return True

    return False


def _accepts_class(cls, t):
    if cls is t or cls is object:
        return 2

    try:
        if issubclass(t, cls):
            return 2

    except Exception:  # NOQA
        # a Protocol that is not runtime-checkable, a TypedDict ...
        return 1

    if cls is float and issubclass(t, int):
        return 2

    if cls is complex and issubclass(t, (int, float)):
        return 2

    # numpy scalars convert to the plain number types,
    # so they are not held against a number hint
    if (
        t.__module__.startswith('numpy') and
        (cls is int or cls is float or cls is complex or cls is bool)
    ):
        return 1

    return 0


def _worst(tree, keys):
    worst = 2
    for key in keys:
        result = _accepts(tree, key)
        if result < worst:
            worst = result

    return worst


def _accepts_contents(origin, args, t, shape):
    if t is tuple:
        items = [item for item in shape if item is not Ellipsis]

        if origin is tuple:
            if len(args) == 1 or (len(args) == 2 and args[1].kind == 'ellipsis'):
                return _worst(args[0], items)

            # a fixed shape: the recorder keeps only the
            # first few items of a long tuple
            if len(items) != len(shape):
                if len(args) <= _MAX_TUPLE:
                    return 0

                return 1

            if len(args) != len(items):
                return 0

            worst = 2
            for tree, item in zip(args, items):
                result = _accepts(tree, item)
                if result < worst:
                    worst = result

            return worst

        if len(args) == 1:
            return _worst(args[0], items)

        return 2

    if t is dict:
        key_types, value_types = shape
        if len(args) == 2:
            return min(_worst(args[0], key_types), _worst(args[1], value_types))

        if len(args) == 1:
            # iterating a dict gives its keys
            return _worst(args[0], key_types)

        return 2

    # list / set / frozenset: one argument, or the project's list[a, b, c]
    # which means "any of these"
    tree = args[0]
    if len(args) > 1:
        tree = _Hint('union', args=args)

    return _worst(tree, shape)


def _named_classes(name):
    """
    Every class a loaded module has under `name`:
      how a name from a TYPE_CHECKING-only import is found at run time.

    `ConfigEditor3DType = ConfigDB` at run time has a different name from the
    class it stands for, so matching the name against the bases of what
    arrived is not enough.
    """

    found = []
    for module in list(sys.modules.values()):
        try:
            item = vars(module).get(name)
        except Exception:  # NOQA
            continue

        if isinstance(item, type) and item not in found:
            found.append(item)

    return found


def _accepts(tree, key):
    """
    2: what arrived fits the hint.
    1: cannot tell.
    0: it does not fit.
    """

    if isinstance(key, type):
        t = key
        shape = None
    else:
        t, shape = key

    kind = tree.kind

    if kind == 'any':
        return 2

    if kind == 'unknown' or kind == 'ellipsis':
        return 1

    if kind == 'none':
        if t is _NoneType:
            return 2

        return 0

    if kind == 'union':
        best = 0
        for member in tree.args:
            result = _accepts(member, key)
            if result == 2:
                return 2

            if result > best:
                best = result

        return best

    if kind == 'cls':
        return _accepts_class(tree.cls, t)

    if kind == 'name' or kind == 'alias':
        for base in t.__mro__:
            if base.__name__ == tree.name:
                return 2

        for candidate in _named_classes(tree.name):
            if _accepts_class(candidate, t) == 2:
                return 2

        if kind == 'alias':
            return 1

        return 0

    if kind == 'callable':
        if _call_mark(t) == '__call__':
            return 2

        return 0

    if kind == 'type':
        if issubclass(t, type):
            return 2

        return 0

    # a generic: the class first, then what is in it
    outer = _accepts_class(tree.cls, t)
    if outer != 2 or shape is None or not tree.args:
        return outer

    return _accepts_contents(tree.cls, tree.args, t, shape)


def _slot_tree(state, slot):
    tree = state.trees.get(slot)
    if tree is not None:
        return tree

    wanted = slot
    if slot == '<return>' or slot == '<yield>':
        wanted = 'return'

    ann = state.func.__annotations__.get(wanted, _MISSING)
    if ann is _MISSING:
        tree = _ANY
    else:
        tree = _tree_of(ann, state.func.__globals__, 0)

        if slot == '<yield>':
            # Iterator[X] / Iterable[X] / Generator[X, ...]: the items are X
            if (
                tree.kind == 'gen' and
                tree.cls.__name__ in _YIELDING and
                tree.args
            ):
                tree = tree.args[0]
            else:
                tree = _UNKNOWN

    state.trees[slot] = tree

    return tree


def _first_verdict(state, slot, t):
    """
    0: any value of this type fits.
    1: none does.
    2: the type fits but the hint also names contents.
    """

    _busy.on = True
    try:
        tree = _slot_tree(state, slot)
        if _accepts(tree, t) == 0:
            return 1

        if (
            _wants_contents(tree) and
            (t is list or t is tuple or t is dict or t is set or t is frozenset)
        ):
            return 2

        return 0

    finally:
        _busy.on = False


def _judge(state, slot, key):
    _busy.on = True
    try:
        if _accepts(_slot_tree(state, slot), key) == 0:
            return 1

        return 0
    finally:
        _busy.on = False


def _bad_slot(state, slot, value):
    """
    What arrived in the slot as a key (a type, or a type with its contents)
    when it does not fit the hint; else None.
    """

    t = type(value)
    verdicts = state.verdicts
    verdict = verdicts.get((slot, t))
    if verdict is None:
        verdict = _first_verdict(state, slot, t)
        verdicts[(slot, t)] = verdict

    if verdict == 0:
        return None

    if verdict == 1:
        return t

    key = t, _shape(value, _SHAPE_DEPTH)
    inner = verdicts.get((slot, key))
    if inner is None:
        inner = _judge(state, slot, key)
        verdicts[(slot, key)] = inner

    if inner:
        return key

    return None


def _verify_args(state, args, kwargs):
    """
    [(slot, key)] for the parameters whose value does not fit the hint;
    None when they all do.
    """

    bad = None
    names = state.positional
    stop = len(args)
    if stop > len(names):
        stop = len(names)

    index = state.first
    while index < stop:
        key = _bad_slot(state, names[index], args[index])
        if key is not None:
            if bad is None:
                bad = []

            bad.append((names[index], key))

        index += 1

    if kwargs:
        allowed = state.keywords
        for name, value in kwargs.items():
            if name in allowed:
                key = _bad_slot(state, name, value)
                if key is not None:
                    if bad is None:
                        bad = []

                    bad.append((name, key))

    return bad


# ------------- recording a mismatch

def _call_keys(state, args, kwargs):
    """
    (parameter, key) for everything that was passed, in call order.
    """

    keys = []
    names = state.positional
    stop = len(args)
    if stop > len(names):
        stop = len(names)

    index = state.first
    while index < stop:
        keys.append((names[index], _key_of(args[index], _SHAPE_DEPTH + 1)))
        index += 1

    if kwargs:
        allowed = state.keywords
        for name, value in kwargs.items():
            if name in allowed:
                keys.append((name, _key_of(value, _SHAPE_DEPTH + 1)))

    return tuple(keys)


def _short_path(name):
    """A file inside the repo is stored relative to it ("harness_designer/ui/x.py"); anything else as it is."""

    if name.startswith(_ROOT):
        return name[len(_ROOT):].replace(os.sep, '/')

    return name


def _call_site():
    """(file, line, function) of whoever made the call being checked: the first frame that is not in this file."""

    try:
        frame = sys._getframe(0)
        while frame is not None and frame.f_code.co_filename == _OWN_FILE:
            frame = frame.f_back
    except Exception as exc:
        _fail('finding a call site', exc)
        return '', 0, ''

    if frame is None:
        # called from C++ (a Qt slot) or from a thread's bootstrap: no Python caller
        return '', 0, ''

    code = frame.f_code
    return _short_path(code.co_filename), frame.f_lineno, code.co_name


def _class_label(cls):
    if cls.__module__ == 'builtins':
        return cls.__qualname__

    return f'{cls.__module__}.{cls.__qualname__}'


def _ann_label(cls):
    """A class in a hint: builtins and the typing / abc names bare, anything else in full."""

    if cls.__module__ in ('builtins', 'typing', 'collections.abc'):
        return cls.__qualname__

    return f'{cls.__module__}.{cls.__qualname__}'


def _ann_text(ann):
    """A hint as it reads in the source: ``"_canvas.Canvas"``, ``int | None``, ``list[str]``."""

    try:
        if ann is None or ann is _NoneType:
            return 'None'

        if ann is Ellipsis:
            return '...'

        if isinstance(ann, str):
            return ann

        if isinstance(ann, typing.ForwardRef):
            return ann.__forward_arg__

        if isinstance(ann, list):
            return '[' + ', '.join(_ann_text(item) for item in ann) + ']'

        origin = typing.get_origin(ann)
        if origin is not None:
            args = typing.get_args(ann)

            if origin is typing.Union or origin is types.UnionType:
                return ' | '.join(_ann_text(arg) for arg in args)

            if origin is typing.Annotated:
                return _ann_text(args[0])

            if origin is typing.Literal:
                return 'Literal[' + ', '.join(repr(arg) for arg in args) + ']'

            label = _ann_label(origin)
            if not args:
                return label

            return label + '[' + ', '.join(_ann_text(arg) for arg in args) + ']'

        if isinstance(ann, type):
            return _ann_label(ann)

        if isinstance(ann, typing.TypeVar):
            return ann.__name__

        return repr(ann)
    except Exception:
        return repr(ann)


def _default_text(default):
    if default is None or default is True or default is False:
        return repr(default)

    if isinstance(default, (int, float)):
        return repr(default)

    if isinstance(default, str) and len(default) <= 24:
        return repr(default)

    # anything else could run user code to print itself
    return '...'


def _expected_signature(state):
    """The function as annotated: (``(canvas: _canvas.Canvas, parent: QWidget | None = None)``, ``None``)."""

    found = state.signature
    if found is not None:
        return found

    try:
        signature = inspect.signature(state.func)
    except (TypeError, ValueError):
        found = '(...)', ''
    else:
        parts = []
        star = False
        for parameter in signature.parameters.values():
            part = parameter.name
            if parameter.kind is parameter.VAR_POSITIONAL:
                part = '*' + part
                star = True
            elif parameter.kind is parameter.VAR_KEYWORD:
                part = '**' + part
            elif parameter.kind is parameter.KEYWORD_ONLY and not star:
                parts.append('*')
                star = True

            if parameter.annotation is not parameter.empty:
                part += ': ' + _ann_text(parameter.annotation)

            if parameter.default is not parameter.empty:
                part += ' = ' + _default_text(parameter.default)

            parts.append(part)

        returned = ''
        if signature.return_annotation is not signature.empty:
            returned = _ann_text(signature.return_annotation)

        found = '(' + ', '.join(parts) + ')', returned

    state.signature = found
    return found


def _property_role(state):
    """'getter', 'setter' or 'deleter' when this function is an accessor of a property of its class; '' when it is not.

    `do` only ever sees the plain function, but by the time a row is written the class exists: walk the qualified name to the
    class, and see whether the attribute of that name is a property one of whose accessors leads back to this function
    (through any decorators in between that used functools.wraps).
    """

    try:
        owner = sys.modules.get(state.module)
        parts = state.qualname.split('.')
        if owner is None or len(parts) < 2 or '<locals>' in parts:
            return ''

        for part in parts[:-1]:
            owner = getattr(owner, part)

        attribute = vars(owner).get(parts[-1])
        if not isinstance(attribute, property):
            return ''

        for role, accessor in (('getter', attribute.fget), ('setter', attribute.fset), ('deleter', attribute.fdel)):
            link = accessor
            for _ in range(12):
                if link is None:
                    break

                if link is state.func:
                    return role

                link = getattr(link, '__wrapped__', None)
    except Exception:
        return ''

    return ''


def _function_name(state):
    """The name a function is stored under: its qualified name, with (getter) / (setter) / (deleter) in front for a property."""

    name = state.name
    if name is None:
        name = state.qualname
        role = _property_role(state)
        if role:
            name = '(%s) %s' % (role, name)

        state.name = name

    return name


def _actual_signature(keys, ret):
    """The call as it was made: (the type of everything passed, the type that came back or '' when nothing did)."""

    cache_key = keys, ret
    found = _SIGNATURES.get(cache_key)
    if found is None:
        passed = '(' + ', '.join('%s: %s' % (name, _render(key)) for name, key in keys) + ')'
        returned = ''
        if ret is not None:
            if ret[0] == '<yield>':
                returned = 'yield ' + _render(ret[1])
            else:
                returned = _render(ret[1])

        found = passed, returned
        _SIGNATURES[cache_key] = found

    return found


def _record(state, bad, args, kwargs, ret):
    """Keep one wrong call. `bad` is [(slot, key)]; `ret` is (slot, key) of what the call produced, or None."""

    if _busy.on:
        return

    _busy.on = True
    try:
        keys = _call_keys(state, args, kwargs)
        file, line, caller = _call_site()
        passed, returned = _actual_signature(keys, ret)

        # the same calling function, file and signature is already there
        record_key = caller, file, passed, returned
        if record_key in state.seen:
            return

        # a function called wrongly from very many places keeps only the first few for each type that arrived
        wrong = [(slot, _render(key)) for slot, key in bad]
        if all(state.distinct.get(item, 0) >= _SITE_LIMIT for item in wrong):
            return

        for item in wrong:
            state.distinct[item] = state.distinct.get(item, 0) + 1

        state.seen.add(record_key)
        state.rows.append((caller, file, line, passed, returned))
    finally:
        _busy.on = False


def _record_call(state, bad, args, kwargs, ret):
    try:
        _record(state, bad, args, kwargs, ret)
    except Exception as exc:
        _fail(f'{state.qualname} recording', exc)


# ------------------------------------------------------------------ the wrappers

def _make_wrapper(func, state):
    full = _FULL_CALLS
    stride = _STRIDE
    active = _ACTIVE
    constructor = state.constructor

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        state.calls += 1
        calls = state.calls
        if calls == 1:
            active.append(state)

        if calls > full and calls % stride:
            return func(*args, **kwargs)

        bad = None
        if not _busy.on:
            try:
                bad = _verify_args(state, args, kwargs)
            except Exception as exc:
                _fail(f'{state.qualname} arguments', exc)

        try:
            result = func(*args, **kwargs)
        except BaseException:
            # the call failed: what was wrong with its arguments is still worth keeping
            if bad:
                _record_call(state, bad, args, kwargs, None)

            raise

        wrong = None
        if not constructor and not _busy.on:
            try:
                wrong = _bad_slot(state, '<return>', result)
            except Exception as exc:
                _fail(f'{state.qualname} return', exc)

        if wrong is not None:
            if bad is None:
                bad = []

            bad.append(('<return>', wrong))

        if bad:
            returned = None
            if not constructor:
                returned = '<return>', _key_of(result, _SHAPE_DEPTH + 1)

            _record_call(state, bad, args, kwargs, returned)

        return result

    return wrapper


def _make_generator_wrapper(func, state):
    full = _FULL_CALLS
    stride = _STRIDE
    active = _ACTIVE

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        state.calls += 1
        calls = state.calls
        if calls == 1:
            active.append(state)

        if (calls <= full or not calls % stride) and not _busy.on:
            try:
                bad = _verify_args(state, args, kwargs)
                if bad:
                    _record_call(state, bad, args, kwargs, None)
            except Exception as exc:
                _fail(f'{state.qualname} arguments', exc)

        generator = func(*args, **kwargs)

        # a hand-rolled `yield from` so every yielded item can be looked at
        try:
            item = next(generator)
        except StopIteration as stop:
            return stop.value

        while True:
            state.yields += 1
            yields = state.yields
            if (yields <= full or not yields % stride) and not _busy.on:
                try:
                    wrong = _bad_slot(state, '<yield>', item)
                    if wrong is not None:
                        _record_call(state, [('<yield>', wrong)], args, kwargs, ('<yield>', wrong))
                except Exception as exc:
                    _fail(f'{state.qualname} yield', exc)

            try:
                sent = yield item
            except GeneratorExit:
                generator.close()
                raise
            except BaseException as exc:
                try:
                    item = generator.throw(exc)
                except StopIteration as stop:
                    return stop.value
            else:
                try:
                    item = generator.send(sent)
                except StopIteration as stop:
                    return stop.value

    return wrapper


def _instrument(func):
    try:
        code = func.__code__
    except AttributeError:
        # not a plain function (a class, a partial, a builtin): nothing to wrap
        return func

    if inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func):
        return func

    argcount = code.co_argcount
    positional = code.co_varnames[:argcount]
    keyword_only = code.co_varnames[argcount:argcount + code.co_kwonlyargcount]

    first = 0
    if positional and positional[0] in _RECEIVERS:
        first = 1

    keyword_start = first
    if code.co_posonlyargcount > keyword_start:
        keyword_start = code.co_posonlyargcount

    keywords = frozenset(positional[keyword_start:]) | frozenset(keyword_only)

    # every closure made from one `def` shares a code object, so it shares one state: a nested function decorated inside
    # a function that runs often must not register a new state on every call
    state = _BY_CODE.get(code)
    if state is None:
        state = _FuncState(str(func.__module__), func.__qualname__, ','.join(positional + keyword_only),
                           code.co_filename, code.co_firstlineno, positional, first, keywords, func)
        _BY_CODE[code] = state
        _STATES.append(state)

    if inspect.isgeneratorfunction(func):
        return _make_generator_wrapper(func, state)

    return _make_wrapper(func, state)


def do(func: Callable[_P, _R]) -> Callable[_P, _R]:
    if not _ENABLED:
        return func

    try:
        # _instrument is unannotated on purpose; the wrapper really does keep func's signature
        return cast(Callable[_P, _R], _instrument(func))
    except Exception as exc:
        _fail('decorating a function', exc)
        return func


# ------------------------------------------------------------------ database
#
# Wrong calls are kept in plain dicts and lists while the app runs (a call that fits costs a few dict lookups). Every tick
# they are written into a SQLite database that lives in memory, and that database is written to the file in one
# transaction. Both writes work the same way: look the function up by name and source file and take its row id (adding the
# function only when it is not there), then look in `calls` for that function id with the same calling function, calling
# file and signatures, and add the call only when there is no such row. So a row is never written twice -- not by a repeat
# in this process, not by another process, not by an earlier session.

def _memory():
    con = _RUN.get('memory')
    if con is None:
        # autocommit: the transactions are explicit. The flush thread and the exit hook share it, one at a time (_LOCK)
        con = sqlite3.connect(':memory:', check_same_thread=False, isolation_level=None)
        con.executescript(_SCHEMA)
        _RUN['memory'] = con

    return con


def _fold(con):
    """Write the new wrong calls into the in-memory database; True when that added anything."""

    pending = [state for state in _STATES if state.folded < len(state.rows)]
    if not pending:
        return False

    taken = []
    added = False

    con.execute('BEGIN')
    try:
        for state in pending:
            new = state.rows[state.folded:]

            if state.db_id is None:
                name = _function_name(state)
                file = _short_path(state.file)
                found = con.execute('SELECT id FROM functions WHERE name = ? AND file = ?', (name, file)).fetchone()
                if found is None:
                    signature, returned = _expected_signature(state)
                    cursor = con.execute(
                        'INSERT INTO functions (name, signature, return_type, file, line) VALUES (?, ?, ?, ?, ?)',
                        (name, signature, returned, file, state.line))
                    state.db_id = cursor.lastrowid
                else:
                    state.db_id = found[0]

            for caller, file, line, passed, returned in new:
                exists = con.execute(
                    'SELECT 1 FROM calls WHERE func_id = ? AND caller = ? AND file = ? AND signature = ? AND return_type = ?',
                    (state.db_id, caller, file, passed, returned)).fetchone()
                if exists is None:
                    con.execute(
                        'INSERT INTO calls (func_id, caller, file, line, signature, return_type) VALUES (?, ?, ?, ?, ?, ?)',
                        (state.db_id, caller, file, line, passed, returned))
                    added = True

            taken.append((state, len(new)))

        con.execute('COMMIT')
    except BaseException:
        if con.in_transaction:
            con.execute('ROLLBACK')

        for state in pending:
            state.db_id = None

        raise

    # only now is it certain the rows are in the database; until then a failed fold is simply redone
    for state, count in taken:
        state.folded += count

    return added


# the same look-up-then-add, from the in-memory database into the file
_DUMP_SQL = (
    'INSERT INTO disk.functions (name, signature, return_type, file, line) '
    'SELECT m.name, m.signature, m.return_type, m.file, m.line FROM main.functions m '
    'WHERE NOT EXISTS (SELECT 1 FROM disk.functions d WHERE d.name = m.name AND d.file = m.file)',

    'INSERT INTO disk.calls (func_id, caller, file, line, signature, return_type) '
    'SELECT d.id, c.caller, c.file, c.line, c.signature, c.return_type FROM main.calls c '
    'JOIN main.functions m ON m.id = c.func_id '
    'JOIN disk.functions d ON d.name = m.name AND d.file = m.file '
    'WHERE NOT EXISTS (SELECT 1 FROM disk.calls x WHERE x.func_id = d.id AND x.caller = c.caller AND x.file = c.file '
    'AND x.signature = c.signature AND x.return_type = c.return_type)',
)


def _dump(con):
    """Write what the in-memory database holds and the file does not, in one transaction."""

    con.execute('ATTACH DATABASE ? AS disk', (_db_path(),))
    try:
        con.execute('PRAGMA disk.journal_mode=WAL')
        con.execute('PRAGMA disk.synchronous=NORMAL')

        # a file from an earlier layout of this check has a `functions` table with other columns
        existing = [row[1] for row in con.execute('PRAGMA disk.table_info(functions)')]
        if existing and 'return_type' not in existing:
            raise RuntimeError('%s was written by an older check_types.py; delete it and record again' % _db_path())

        con.executescript(_SCHEMA.replace('CREATE TABLE IF NOT EXISTS ', 'CREATE TABLE IF NOT EXISTS disk.'))

        # IMMEDIATE: take the file's write lock now, so two processes dumping at once wait for each other here
        con.execute('BEGIN IMMEDIATE')
        try:
            for statement in _DUMP_SQL:
                con.execute(statement)

            con.execute('COMMIT')
        except BaseException:
            if con.in_transaction:
                con.execute('ROLLBACK')

            raise
    finally:
        try:
            con.execute('DETACH DATABASE disk')
        except Exception:
            pass


def _flush():
    if not _STATES or os.getpid() != _PID:
        return

    with _LOCK:
        try:
            con = _memory()
            if _fold(con):
                _RUN['dirty'] = True
        except Exception as exc:
            _fail('keeping the in-memory database', exc)
            return

        if not _RUN.get('dirty'):
            return

        try:
            _dump(con)
        except Exception as exc:
            # the data is still in memory; the next tick tries again
            _fail('writing the database file', exc)
            return

        _RUN['dirty'] = False


def _flush_loop():
    while True:
        time.sleep(_FLUSH_SECONDS)
        _flush()


if _ENABLED:
    atexit.register(_flush)

    # a multiprocessing worker leaves through os._exit, which skips atexit but runs these
    multiprocessing.util.Finalize(None, _flush, exitpriority=10)
    threading.Thread(target=_flush_loop, name='type-audit-flush', daemon=True).start()
