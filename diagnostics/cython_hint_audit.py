# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Find call sites whose arguments the *compiled* build would reject.

harness_designer is compiled with Cython, which turns many parameter
annotations into runtime type checks that a run from source -- and mypy,
which follows PEP 484 -- never performs. This tool reads the code statically
and reports calls that pass a value such a check refuses: the failure that
only shows up in the frozen app, as ``TypeError: Argument 'params' has
incorrect type (expected tuple, got list)``.

What Cython 3.2.4 enforces (probed against the real compiler, 2026-10-21):

* ``tuple``, ``list``, ``dict``, ``set``, ``frozenset``, ``str`` and ``bytes``
  (also ``list[...]`` and friends, and ``X | None``) get an EXACT type check.
  Subclasses are rejected as well -- a ``NamedTuple`` for ``tuple``, a
  ``defaultdict`` for ``dict``. ``None`` is rejected unless the hint says
  ``| None``.
* A union of two or more non-None types (``tuple | list | None``), ``Any``,
  ``object`` and user classes get no check at all.
* ``int`` / ``float`` hints convert any number first, so only non-numbers
  raise; a float passed to an ``int`` is silently truncated (``--float-to-int``
  reports those too).

Usage::

    python diagnostics/cython_hint_audit.py [target_dir] [--json] [--float-to-int]

``target_dir`` defaults to ``harness_designer``. As with ``dep_trace.py``'s
cross-file modes, the index of definitions and classes is built only from the
files under the target, so point it at the whole package for a real answer.

How it decides: every parameter whose hint Cython enforces is indexed. Each
call is matched to the definitions it could reach, and the type of every
argument is inferred where the code makes it obvious (literals, builtin calls,
comprehensions, local variables, ``self.x`` attributes, ``a, b = self.method()``
returns). A finding is reported only when EVERY definition the call could reach
rejects the argument. The tier says how the call was matched:

* ``A`` -- through ``self`` / ``super()`` / a plain function or class name.
* ``T`` -- a database wrapper receiver (``...table.execute(...)``,
  ``connector.insert(...)``).
* ``B`` -- a method-name match only; names that also exist on builtin, Qt,
  numpy or sqlite types are skipped because they cannot be told apart by name.
* ``S`` -- ``self.x = value`` where the property setter rejects the value.

Findings whose argument "may also be None" are listed separately: the tool
cannot see an ``if x is not None`` guard above the call, so each one needs a
look. Not seen at all: argument types that come from another object's return
value, callbacks and Qt slots, subclass instances built elsewhere, and
``getattr`` dispatch -- "nothing found" is a good sign, not proof.
"""

import argparse
import ast
import collections
import json
import os
import re
import sys


CONTAINERS = {'tuple', 'list', 'dict', 'set', 'frozenset', 'str', 'bytes'}
NUMS = {'int', 'float'}
NUMERIC_LABELS = {'int', 'float', 'bool', 'ndarray'}

# (kind, accepted builtin type names, whether None is accepted); kind is
# 'container' (exact-type check) or 'num' (number conversion).
HintInfo = tuple[str, set[str], bool]

FLOAT_TO_INT = False


# ---------------------------------------------------------------- hints

def flatten_union(node: ast.AST) -> list[ast.AST]:
    """Members of ``A | B | None`` / ``Union[A, B, None]`` (quoted forms too)."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return flatten_union(node.left) + flatten_union(node.right)

    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and
            node.value.id in ('Union', '_Union')):
        if isinstance(node.slice, ast.Tuple):
            elts = node.slice.elts
        else:
            elts = [node.slice]

        out = []
        for elt in elts:
            out += flatten_union(elt)

        return out

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return flatten_union(ast.parse(node.value, mode='eval').body)
        except SyntaxError:
            return [node]

    return [node]


def ann_info(ann: ast.AST | None) -> HintInfo | None:
    """What Cython enforces for this annotation, or ``None`` when nothing."""
    if ann is None:
        return None

    types = set()
    none_ok = False

    for member in flatten_union(ann):
        if isinstance(member, ast.Constant) and member.value is None:
            none_ok = True
            continue

        base = member
        if isinstance(base, ast.Subscript):
            base = base.value

        if isinstance(base, ast.Name) and base.id in CONTAINERS | NUMS:
            types.add(base.id)
        else:
            return None

    if len(types) != 1:
        return None

    name = next(iter(types))
    if name in NUMS:
        return 'num', {name}, none_ok

    return 'container', {name}, none_ok


def accepts(info: HintInfo, label: str) -> bool:
    """Would the compiled check accept an argument of inferred type *label*?"""
    kind, types, none_ok = info

    if label == 'None':
        return none_ok

    if kind == 'num':
        if FLOAT_TO_INT and types == {'int'} and label == 'float':
            return False  # PyNumber_Long: no error, silently a different value

        return label in NUMERIC_LABELS

    return label in types


def hint_text(info: HintInfo) -> str:
    text = '/'.join(sorted(info[1]))
    if info[2]:
        text += '|None'

    return text


# ---------------------------------------------------------------- index

class Definition:
    """One function/method whose enforced parameters are indexed."""

    def __init__(self, file: str, node: ast.FunctionDef | ast.AsyncFunctionDef, cls: str | None) -> None:
        self.file = file
        self.line = node.lineno
        self.cls = cls
        self.name = node.name
        self.node = node

        if cls:
            self.qual = f'{cls}.{node.name}'
        else:
            self.qual = node.name

        decorators = [ast.unparse(d) for d in node.decorator_list]
        static = 'staticmethod' in decorators
        self.setter = any(d.endswith('.setter') for d in decorators)

        args = node.args
        positional = args.posonlyargs + args.args
        if cls and not static and positional:
            positional = positional[1:]  # self / cls

        self.params = [(a.arg, ann_info(a.annotation)) for a in positional]
        self.params += [(a.arg, ann_info(a.annotation)) for a in args.kwonlyargs]
        self.params_pos = len(positional)
        self.has_var = args.vararg is not None


DEFS: list[Definition] = []
BY_NAME: dict[str, list[Definition]] = collections.defaultdict(list)
CLASSES: dict[str, list[tuple[str, ast.ClassDef]]] = {}
CLASS_BASES: dict[str, set[str]] = collections.defaultdict(set)
NAMEDTUPLES: set[str] = set()
TREES: dict[str, ast.Module] = {}
EXTERNAL: set[str] = set()
ATTR_CACHE: dict[tuple[str, str], set[str] | None] = {}
ATTR_GUARD: set[tuple[str, str]] = set()
FINDINGS: list[dict] = []


def _register_defs(body: list[ast.stmt], cls: str | None, rel: str) -> None:
    for node in body:
        if isinstance(node, ast.ClassDef):
            _register_defs(node.body, node.name, rel)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definition = Definition(rel, node, cls)
            DEFS.append(definition)
            BY_NAME[node.name].append(definition)
            _register_defs(node.body, cls, rel)

        elif isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            for attr in ('body', 'orelse', 'finalbody'):
                _register_defs(getattr(node, attr, []), cls, rel)

            for handler in getattr(node, 'handlers', []):
                _register_defs(handler.body, cls, rel)


def build_index(root: str) -> int:
    """Parse every ``.py`` under *root*; return how many files were skipped."""
    skipped = 0

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue

            path = os.path.join(dirpath, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    TREES[path] = ast.parse(f.read(), path)
            except (SyntaxError, UnicodeDecodeError, OSError):
                skipped += 1

    for path, tree in TREES.items():
        rel = os.path.relpath(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                CLASSES.setdefault(node.name, []).append((rel, node))

                for base in node.bases:
                    base_name = ast.unparse(base).split('.')[-1].split('[')[0]
                    CLASS_BASES[node.name].add(base_name)
                    if base_name == 'NamedTuple':
                        NAMEDTUPLES.add(node.name)

            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if ast.unparse(node.value.func).split('.')[-1] == 'namedtuple':
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            NAMEDTUPLES.add(target.id)

        _register_defs(tree.body, None, rel)

    return skipped


def collect_external_names() -> set[str]:
    """Method names that exist on builtin / stdlib / numpy / pandas / Qt types.

    A call to one of these cannot be told apart from a call to a project
    method of the same name, so such calls are not resolved by name.
    """
    import builtins  # NOQA
    import collections as _collections
    import datetime
    import io
    import json as _json
    import logging
    import math
    import multiprocessing
    import pathlib
    import queue
    import sqlite3
    import struct
    import threading
    import time
    import weakref
    import zipfile

    names = set()
    objs = [list, dict, set, frozenset, tuple, str, bytes, bytearray, int, float, bool, object, type,
            range, memoryview, _collections.deque, _collections.defaultdict, _collections.OrderedDict,
            _collections.Counter, threading.Thread, threading.Lock, threading.RLock, threading.Event,
            threading.Semaphore, threading.Condition, queue.Queue, sqlite3.Connection, sqlite3.Cursor,
            io.StringIO, io.BytesIO, io.TextIOWrapper, re.Pattern, re.Match, pathlib.Path, logging.Logger,
            zipfile.ZipFile, datetime.datetime, datetime.date, datetime.timedelta, weakref.ref,
            weakref.WeakSet, weakref.WeakKeyDictionary, weakref.WeakValueDictionary,
            multiprocessing.Process, os, os.path, sys, time, math, _json, struct, re]

    for obj in objs:
        names |= set(dir(obj))

    try:
        import numpy as np
        names |= set(dir(np.ndarray)) | set(dir(np))
    except ImportError:
        pass

    try:
        import pandas as pd
        names |= set(dir(pd.DataFrame)) | set(dir(pd.Series))
    except ImportError:
        pass

    try:
        from PIL import Image as _pil_image
        names |= set(dir(_pil_image.Image))
    except ImportError:
        pass

    try:
        from PySide6 import QtCore, QtGui, QtWidgets

        modules = [QtCore, QtGui, QtWidgets]
        for module_name in ('QtOpenGL', 'QtOpenGLWidgets', 'QtNetwork', 'QtSvg',
                            'QtWebEngineWidgets', 'QtWebEngineCore'):
            try:
                modules.append(__import__('PySide6.' + module_name, fromlist=['x']))
            except ImportError:
                pass

        for module in modules:
            for attr_name in dir(module):
                obj = getattr(module, attr_name, None)
                if isinstance(obj, type):
                    names |= set(dir(obj))
    except ImportError:
        print('warning: PySide6 not importable, Qt method names are not excluded', file=sys.stderr)

    return names


# ---------------------------------------------------------------- inference

BUILTIN_CALL = {
    'list': 'list', 'tuple': 'tuple', 'dict': 'dict', 'set': 'set', 'frozenset': 'frozenset',
    'str': 'str', 'bytes': 'bytes', 'int': 'int', 'float': 'float', 'bool': 'bool',
    'sorted': 'list', 'len': 'int', 'ord': 'int', 'repr': 'str', 'chr': 'str',
    'zip': 'iterator', 'map': 'iterator', 'filter': 'iterator', 'reversed': 'iterator',
    'enumerate': 'iterator', 'iter': 'iterator', 'range': 'range', 'bytearray': 'bytearray',
}
NP_ARRAY = {'array', 'zeros', 'ones', 'empty', 'arange', 'linspace', 'asarray', 'stack',
            'concatenate', 'eye', 'identity', 'full', 'cross', 'cumsum', 'vstack', 'hstack',
            'zeros_like', 'ones_like', 'diff', 'transpose', 'dot'}
SPECIAL = {'defaultdict': 'defaultdict', 'OrderedDict': 'OrderedDict', 'deque': 'deque', 'Counter': 'Counter'}
VIEW_METHODS = {'keys', 'values', 'items'}

Labels = set[str]


class Ctx:
    """Local-variable knowledge for one function (or a class body)."""

    def __init__(self, fn: ast.FunctionDef | ast.AsyncFunctionDef | None, cls: str | None) -> None:
        self.fn = fn
        self.cls = cls
        self.assign: dict[str, list[tuple]] = collections.defaultdict(list)
        self.unknown: set[str] = set()
        self.memo: dict[str, Labels | None] = {}
        self.guard: set[str] = set()

        if fn is None:
            return

        a = fn.args
        for arg in a.posonlyargs + a.args + a.kwonlyargs:
            info = ann_info(arg.annotation)
            if info and info[0] == 'container' and not info[2]:
                self.assign[arg.arg].append(('label', next(iter(info[1]))))
            else:
                self.unknown.add(arg.arg)

        if a.vararg:
            self.unknown.add(a.vararg.arg)

        if a.kwarg:
            self.unknown.add(a.kwarg.arg)

        self._collect(fn.body)

    def _mark_names_unknown(self, node: ast.AST) -> None:
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                self.unknown.add(n.id)

    def _collect(self, body: list[ast.stmt]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.unknown.add(node.name)
                continue

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.assign[target.id].append(('expr', node.value))
                    elif (isinstance(target, ast.Tuple) and isinstance(node.value, ast.Call) and
                          all(isinstance(x, ast.Name) for x in target.elts)):
                        for idx, x in enumerate(target.elts):
                            self.assign[x.id].append(('unpack', (node.value, idx)))
                    else:
                        self._mark_names_unknown(target)

            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                info = ann_info(node.annotation)
                if node.value is not None:
                    self.assign[node.target.id].append(('expr', node.value))
                elif info and info[0] == 'container':
                    self.assign[node.target.id].append(('label', next(iter(info[1]))))
                else:
                    self.unknown.add(node.target.id)

            else:
                self._collect_nested(node)

    def _collect_nested(self, node: ast.stmt) -> None:
        """Bindings inside if/for/with/try bodies of a statement."""
        for n in ast.walk(node):
            if isinstance(n, (ast.For, ast.AsyncFor)):
                self._mark_names_unknown(n.target)

            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                self.unknown.add(n.target.id)

            elif isinstance(n, ast.NamedExpr):
                self.unknown.add(n.target.id)

            elif isinstance(n, ast.withitem) and n.optional_vars is not None:
                self._mark_names_unknown(n.optional_vars)

            elif isinstance(n, ast.ExceptHandler) and n.name:
                self.unknown.add(n.name)

            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for alias in n.names:
                    self.unknown.add((alias.asname or alias.name).split('.')[0])

            elif isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Name):
                        self.assign[target.id].append(('expr', n.value))
                    else:
                        self._mark_names_unknown(target)

            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
                self.assign[n.target.id].append(('expr', n.value))


def label_union(parts: list[Labels | None]) -> Labels | None:
    out = set()
    for part in parts:
        if part is None:
            return None

        out |= part

    return out


def _single(labels: Labels | None) -> str | None:
    if labels and len(labels) == 1:
        return next(iter(labels))

    return None


def infer(e: ast.AST | None, ctx: Ctx, depth: int = 0) -> Labels | None:
    """Possible concrete types of expression *e*, or ``None`` when unknown."""
    if depth > 6 or e is None:
        return None

    if isinstance(e, ast.Constant):
        v = e.value
        if v is None:
            return {'None'}
        if isinstance(v, bool):
            return {'bool'}
        if isinstance(v, str):
            return {'str'}
        if isinstance(v, bytes):
            return {'bytes'}
        if isinstance(v, int):
            return {'int'}
        if isinstance(v, float):
            return {'float'}
        return None

    if isinstance(e, ast.JoinedStr):
        return {'str'}
    if isinstance(e, (ast.List, ast.ListComp)):
        return {'list'}
    if isinstance(e, ast.Tuple):
        return {'tuple'}
    if isinstance(e, (ast.Dict, ast.DictComp)):
        return {'dict'}
    if isinstance(e, (ast.Set, ast.SetComp)):
        return {'set'}
    if isinstance(e, ast.GeneratorExp):
        return {'iterator'}

    if isinstance(e, ast.IfExp):
        return label_union([infer(e.body, ctx, depth + 1), infer(e.orelse, ctx, depth + 1)])

    if isinstance(e, ast.BoolOp):
        return label_union([infer(v, ctx, depth + 1) for v in e.values])

    if isinstance(e, ast.BinOp):
        left = infer(e.left, ctx, depth + 1)
        right = infer(e.right, ctx, depth + 1)
        left_one = _single(left)

        if isinstance(e.op, ast.Add) and left and left == right and left_one in ('list', 'tuple', 'str', 'bytes'):
            return left

        if isinstance(e.op, ast.Mult):
            for a, b in ((left, right), (right, left)):
                if _single(a) in ('list', 'tuple', 'str', 'bytes') and b == {'int'}:
                    return a

        if isinstance(e.op, ast.Mod) and left == {'str'}:
            return {'str'}

        return None

    if isinstance(e, ast.Name):
        return _infer_name(e, ctx, depth)

    if isinstance(e, ast.Attribute):
        if isinstance(e.value, ast.Name) and e.value.id == 'self' and ctx.cls:
            return attr_labels(ctx.cls, e.attr)

        return None

    if isinstance(e, ast.Call):
        return _infer_call(e, ctx, depth)

    return None


def _infer_name(e: ast.Name, ctx: Ctx, depth: int) -> Labels | None:
    if e.id in ctx.unknown:
        return None

    entries = ctx.assign.get(e.id)
    if not entries:
        return None

    if e.id in ctx.memo:
        return ctx.memo[e.id]

    if e.id in ctx.guard:
        return None

    ctx.guard.add(e.id)

    parts = []
    for kind, val in entries:
        if kind == 'label':
            parts.append({val})
        elif kind == 'unpack':
            parts.append(infer_unpack(val[0], val[1], ctx, depth + 1))
        else:
            parts.append(infer(val, ctx, depth + 1))

    ctx.guard.discard(e.id)

    result = label_union(parts)
    ctx.memo[e.id] = result
    return result


def _infer_call(e: ast.Call, ctx: Ctx, depth: int) -> Labels | None:
    f = e.func

    if isinstance(f, ast.Name):
        if f.id in BUILTIN_CALL and f.id not in ctx.unknown:
            return {BUILTIN_CALL[f.id]}
        if f.id in NAMEDTUPLES:
            return {'NamedTuple'}
        if f.id in SPECIAL:
            return {SPECIAL[f.id]}
        return None

    if not isinstance(f, ast.Attribute):
        return None

    attr = f.attr
    receiver = f.value

    if isinstance(receiver, ast.Name) and receiver.id in ('np', 'numpy') and attr in NP_ARRAY:
        return {'ndarray'}

    if attr in SPECIAL and isinstance(receiver, ast.Name) and receiver.id in ('collections', '_collections'):
        return {SPECIAL[attr]}

    if attr == 'join' and (isinstance(receiver, ast.Constant) or ast.unparse(receiver) in ('os.path', '_os.path')):
        return {'str'}

    if attr == 'format' and isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
        return {'str'}

    if attr == 'encode':
        return {'bytes'}

    if attr == 'tolist':
        return {'list'}

    if attr in VIEW_METHODS and not e.args:
        return {'dict_view'}

    receiver_labels = infer(receiver, ctx, depth + 1)

    if attr in ('split', 'splitlines') and receiver_labels == {'str'}:
        return {'list'}

    if attr in ('strip', 'lower', 'upper', 'replace', 'lstrip', 'rstrip') and receiver_labels == {'str'}:
        return {'str'}

    if attr == 'copy' and _single(receiver_labels) in ('list', 'dict', 'set'):
        return receiver_labels

    return None


def infer_unpack(call: ast.Call, idx: int, ctx: Ctx, depth: int) -> Labels | None:
    """``a, b = self.method()`` -> labels of element *idx* of every ``return x, y``."""
    if depth > 6:
        return None

    cands, mode = candidates(call, ctx.cls)
    if mode != 'resolved' or len(cands) != 1:
        return None

    definition = cands[0]
    dctx = Ctx(definition.node, definition.cls)
    parts = []

    for n in ast.walk(definition.node):
        if isinstance(n, ast.Return) and n.value is not None:
            v = n.value
            if isinstance(v, ast.Tuple) and idx < len(v.elts) and not any(isinstance(x, ast.Starred) for x in v.elts):
                parts.append(infer(v.elts[idx], dctx, depth + 1))
            else:
                parts.append(None)

    if not parts:
        return None

    return label_union(parts)


def attr_labels(cls: str, attr: str) -> Labels | None:
    """Union of everything ever assigned to ``self.<attr>`` inside class *cls*."""
    key = (cls, attr)
    if key in ATTR_CACHE:
        return ATTR_CACHE[key]

    if key in ATTR_GUARD:
        return None

    ATTR_GUARD.add(key)

    parts = []
    found = False

    for _, cnode in CLASSES.get(cls, []):
        for item in cnode.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == attr:
                        found = True
                        parts.append(infer(item.value, Ctx(None, cls)))

            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ctx = None

                for n in ast.walk(item):
                    targets = []
                    value = None

                    if isinstance(n, ast.Assign):
                        targets, value = n.targets, n.value
                    elif isinstance(n, ast.AnnAssign):
                        targets, value = [n.target], n.value
                    elif isinstance(n, ast.AugAssign):
                        targets = [n.target]

                    for target in targets:
                        is_self_attr = (isinstance(target, ast.Attribute) and
                                        isinstance(target.value, ast.Name) and
                                        target.value.id == 'self' and target.attr == attr)
                        if not is_self_attr:
                            continue

                        found = True
                        if value is None:
                            parts.append(None)
                        else:
                            if ctx is None:
                                ctx = Ctx(item, cls)
                            parts.append(infer(value, ctx))

    ATTR_GUARD.discard(key)

    result = None
    if found:
        result = label_union(parts)

    ATTR_CACHE[key] = result
    return result


# ---------------------------------------------------------------- resolution

DB_WRAPPERS = {'execute', 'executemany', 'insert', 'select', 'update', 'delete', 'fetchall', 'fetchone'}
TABLE_RECEIVER = re.compile(r'(table|_con|\.con|connector|cursor|broker)$', re.I)
TABLE_CLASS_PATTERN = re.compile(r'Table(Base)?$')
CONNECTOR_CLASS_PATTERN = re.compile(r'Connector|Broker')


def class_chain(cls: str, seen: set[str] | None = None) -> list[str]:
    """*cls* followed by its bases (by simple name), nearest first."""
    if seen is None:
        seen = set()

    if cls in seen:
        return []

    seen.add(cls)
    out = [cls]
    for base in CLASS_BASES.get(cls, ()):
        out += class_chain(base, seen)

    return out


def candidates(call: ast.Call, cur_cls: str | None) -> tuple[list[Definition], str | None]:
    """The definitions *call* could reach, and how it was matched."""
    f = call.func

    if isinstance(f, ast.Name):
        found = [d for d in BY_NAME.get(f.id, []) if d.cls is None]
        if f.id in CLASSES:
            found += [d for d in BY_NAME.get('__init__', []) if d.cls == f.id]
        return found, 'func'

    if not isinstance(f, ast.Attribute):
        return [], None

    receiver = f.value
    methods = [d for d in BY_NAME.get(f.attr, []) if d.cls is not None]

    is_self = isinstance(receiver, ast.Name) and receiver.id in ('self', 'cls')
    is_super = (isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and
                receiver.func.id == 'super')

    if (is_self or is_super) and cur_cls:
        chain = class_chain(cur_cls)
        if is_super:
            chain = chain[1:]

        resolved = [d for d in methods if d.cls in chain]
        if resolved:
            return resolved, 'resolved'

    receiver_text = ast.unparse(receiver)
    if f.attr in DB_WRAPPERS and TABLE_RECEIVER.search(receiver_text):
        if receiver_text.lower().endswith('table'):
            pattern = TABLE_CLASS_PATTERN
        else:
            pattern = CONNECTOR_CLASS_PATTERN

        wrapped = [d for d in methods if pattern.search(d.cls)]
        if wrapped:
            return wrapped, 'table'

    if f.attr in EXTERNAL:
        return [], None

    return methods, 'method'


def check_args(call: ast.Call, cands: list[Definition]) -> list[tuple]:
    """``(arg_expr, param_name, hint_info, definition)``; hint None = accepts anything."""
    out = []

    if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
        return out

    for definition in cands:
        if len(call.args) > definition.params_pos and not definition.has_var:
            continue  # this candidate cannot take that many positionals

        by_param_name = dict(definition.params)

        for i, arg in enumerate(call.args):
            name, info = None, None
            if i < definition.params_pos and i < len(definition.params):
                name, info = definition.params[i]
            out.append((arg, name, info, definition))

        for keyword in call.keywords:
            out.append((keyword.value, keyword.arg, by_param_name.get(keyword.arg), definition))

    return out


# ---------------------------------------------------------------- scan

def scan_scope(body: list[ast.stmt], fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
               cls: str | None, rel: str) -> None:
    ctx = Ctx(fn, cls)

    def handle_call(call: ast.Call) -> None:
        cands, mode = candidates(call, cls)
        if not cands:
            return

        by_arg: dict[int, list[tuple]] = collections.defaultdict(list)
        for item in check_args(call, cands):
            by_arg[id(item[0])].append(item)

        for items in by_arg.values():
            expr = items[0][0]
            labels = infer(expr, ctx)
            if not labels:
                continue

            rejected = []
            accepted = 0

            for _, pname, info, definition in items:
                if info is None:
                    accepted += 1
                    continue

                bad = [label for label in labels if not accepts(info, label)]
                if bad:
                    rejected.append((pname, info, definition, bad))
                else:
                    accepted += 1

            if not rejected or accepted:
                continue  # fine, or ambiguous because some candidate accepts it

            if mode == 'table':
                tier = 'T'
            elif mode in ('resolved', 'func'):
                tier = 'A'
            else:
                tier = 'B'

            pname, info, definition, bad = rejected[0]
            FINDINGS.append({
                'tier': tier, 'file': rel, 'line': call.lineno,
                'call': ast.unparse(call.func)[:60], 'arg': ast.unparse(expr)[:70],
                'inferred': sorted(labels), 'bad': sorted(bad),
                'param': pname, 'hint': hint_text(info),
                'callee': f'{definition.file}:{definition.line} {definition.qual}',
                'candidates': len(rejected)})

    def handle_setter(assign: ast.Assign) -> None:
        for target in assign.targets:
            # only `self.x = ...` can be tied to a class; anything else is a guess
            if not (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and
                    target.value.id == 'self' and cls):
                continue

            chain = class_chain(cls)
            setters = [d for d in BY_NAME.get(target.attr, []) if d.setter and d.cls in chain]
            if not setters:
                continue

            labels = infer(assign.value, ctx)
            if not labels:
                continue

            rejected = []
            accepted = 0

            for definition in setters:
                info = None
                if definition.params:
                    info = definition.params[0][1]

                if info is None:
                    accepted += 1
                    continue

                bad = [label for label in labels if not accepts(info, label)]
                if bad:
                    rejected.append((info, definition, bad))
                else:
                    accepted += 1

            if rejected and not accepted:
                info, definition, bad = rejected[0]
                FINDINGS.append({
                    'tier': 'S', 'file': rel, 'line': assign.lineno,
                    'call': f'{ast.unparse(target)} = ...', 'arg': ast.unparse(assign.value)[:70],
                    'inferred': sorted(labels), 'bad': sorted(bad), 'param': definition.params[0][0],
                    'hint': hint_text(info),
                    'callee': f'{definition.file}:{definition.line} {definition.qual} (setter)',
                    'candidates': len(rejected)})

    for stmt in body:
        stack = [stmt]
        while stack:
            node = stack.pop()

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scan_scope(node.body, node, cls, rel)
                continue

            if isinstance(node, ast.ClassDef):
                scan_scope(node.body, None, node.name, rel)
                continue

            if isinstance(node, ast.Call):
                handle_call(node)

            if isinstance(node, ast.Assign):
                handle_setter(node)

            stack.extend(ast.iter_child_nodes(node))


def run_scan() -> list[dict]:
    for path, tree in TREES.items():
        scan_scope(tree.body, None, None, os.path.relpath(path))

    seen = set()
    unique = []
    for finding in FINDINGS:
        key = (finding['file'], finding['line'], finding['call'], finding['arg'],
               finding['param'], finding['callee'])
        if key in seen:
            continue

        seen.add(key)
        unique.append(finding)

    return sorted(unique, key=lambda f: (f['file'], f['line'], f['arg']))


# ---------------------------------------------------------------- output

TIER_HELP = [
    ('A', 'through self / super() / a plain function or class name; every candidate rejects it'),
    ('T', 'a database wrapper receiver (...table.execute(...), connector.insert(...)); every candidate rejects it'),
    ('B', 'method-name match only (names that also exist on builtin / Qt / numpy / sqlite types are skipped)'),
    ('S', 'self.x = value where the property setter rejects the value'),
]


def print_finding(f: dict) -> None:
    print(f"  {f['tier']}  {f['file']}:{f['line']}  {f['call']}(.. {f['arg']} ..)")
    print(f"       passes {'/'.join(f['inferred'])} -> {f['callee']}({f['param']}: {f['hint']})")


def print_report(findings: list[dict], enforced: int, files: int) -> None:
    definite = [f for f in findings if 'None' not in f['inferred']]
    possible = [f for f in findings if 'None' in f['inferred']]

    print(f'{enforced} parameters with a type check in the compiled build, {files} files indexed.')
    print()
    print(f'DEFINITE ({len(definite)}) -- the argument can only be of a type the check rejects:')
    for f in definite:
        print_finding(f)

    if not definite:
        print('  none')

    print()
    print(f'POSSIBLE ({len(possible)}) -- the argument may also be None; look for a guard above the call:')
    for f in possible:
        print_finding(f)

    if not possible:
        print('  none')

    print()
    print('Tiers:')
    for tier, text in TIER_HELP:
        print(f'  {tier}  {text}')


def main(argv: list[str] | None = None) -> int:
    global FLOAT_TO_INT

    parser = argparse.ArgumentParser(
        prog='cython_hint_audit',
        description="Find call sites whose arguments Cython's runtime type checks would reject.")
    parser.add_argument('target', nargs='?', default='harness_designer',
                        help='directory to scan (default: harness_designer)')
    parser.add_argument('--json', action='store_true', help='print the findings as JSON')
    parser.add_argument('--float-to-int', action='store_true',
                        help='also report a float passed to an int-hinted parameter (silently truncated)')
    args = parser.parse_args(argv)

    FLOAT_TO_INT = args.float_to_int

    if not os.path.isdir(args.target):
        print(f'error: {args.target} is not a directory', file=sys.stderr)
        return 2

    skipped = build_index(args.target)
    if skipped:
        print(f'warning: {skipped} file(s) could not be parsed and were skipped', file=sys.stderr)

    EXTERNAL.update(collect_external_names())

    findings = run_scan()
    enforced = sum(1 for d in DEFS for _, info in d.params if info)

    if args.json:
        print(json.dumps(findings, indent=1))
    else:
        print_report(findings, enforced, len(TREES))

    return 0


if __name__ == '__main__':
    sys.exit(main())
