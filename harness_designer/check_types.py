import inspect
import types
import sys
import typing
import traceback


_FROZEN = hasattr(sys, 'frozen')


_NO_SELF = object()  # sentinel: no bound self/cls arg available for this call


def _resolve_annotation(annot, globalns, self_arg=_NO_SELF):
    if annot is None:
        # `-> None` is by far the most common return annotation in this
        # codebase. inspect reports it as the literal `None` object, not
        # `type(None)`, so it must be normalized here or every isinstance()
        # check below crashes instead of comparing against NoneType.
        return type(None), True

    if annot is typing.Self:
        # Self (PEP 673) means "whatever the actual runtime type of the
        # bound self/cls is" -- it isn't a real type, and typing itself
        # deliberately raises on isinstance(x, Self). Resolve it to the
        # real type of the first positional argument (self/cls) instead.
        if self_arg is _NO_SELF:
            return annot, False
        return type(self_arg), True

    if isinstance(annot, typing.ForwardRef):
        # A quoted forward-reference INSIDE a typing.Union[...] (e.g.
        # Union["Decimal", int, float, str]) is auto-wrapped in a ForwardRef
        # by typing itself at the point the Union is built -- it's no longer
        # a plain str by the time this function sees it. Unwrap back to the
        # original string so the eval() below still applies.
        annot = annot.__forward_arg__

    if not isinstance(annot, str):
        return annot, True

    try:
        return eval(annot, globalns), True  # NOQA
    except Exception:
        return annot, False


def _is_union(type_):
    return isinstance(type_, types.UnionType) or typing.get_origin(type_) is typing.Union


def _union_args(type_):
    if isinstance(type_, types.UnionType):
        return type_.__args__
    return typing.get_args(type_)


_already_printed = []


def _report(message):
    # Dedup key is the message alone (type/arg/func signature), never the
    # stack trace -- the same mismatch reported from many call sites should
    # still only print once, but the one time it does print, show the stack
    # so the call site is visible (needed to tell whether the annotation or
    # the call's arguments are what's actually wrong).
    if message in _already_printed:
        return

    _already_printed.append(message)

    stack = ''.join(traceback.format_stack()[:-1])
    print(message)
    print(stack)
    print()


def _check_type(type_, value, arg_name, func, no_print=False, self_arg=_NO_SELF):
    # Resolve `type_` itself before doing anything else with it -- every
    # call site (top-level annotation, a union member, a list/tuple element
    # type, a nested element inside one of those) funnels through here, so
    # resolving once at the top covers all of them instead of requiring
    # each caller to remember to pre-resolve its own sub-annotations (the
    # list/tuple element-type checks below didn't, which is what let an
    # unresolved ForwardRef/None/Self reach a raw isinstance() call and
    # crash instead of being handled). A value that's already a concrete
    # type is returned unchanged (cheap no-op).
    globalns = getattr(func, '__globals__', {})
    type_, resolved = _resolve_annotation(type_, globalns, self_arg=self_arg)
    if not resolved:
        # Can't verify this annotation at all -- same "accept at face
        # value" policy as the equivalent unresolved-union-member case.
        return True

    if _is_union(type_):
        args = _union_args(type_)
        checked_any = False
        any_unresolved = False

        for type2_ in args:
            type2_, ok = _resolve_annotation(type2_, globalns, self_arg=self_arg)
            if not ok:
                any_unresolved = True
                continue

            checked_any = True

            # try:
            #     _check_type(type2_, value, arg_name, func)
            #     break
            # except TypeError:
            #     pass

            if _check_type(type2_, value, arg_name, func, no_print=True, self_arg=self_arg):
                break

        else:
            if any_unresolved:
                # At least one union member couldn't be resolved -- almost
                # always a TYPE_CHECKING-only forward reference (e.g.
                # _Union["_project.Project", None] where `_project` is only
                # imported under TYPE_CHECKING to dodge a circular import,
                # so the name genuinely never exists at runtime, by design).
                # None of the *resolvable* members matched either, but that
                # doesn't mean the value is wrong -- it may well satisfy the
                # unresolvable member, which can never be verified. Can't be
                # reported as a real mismatch.
                return True

            if checked_any:

                if not no_print:
                    msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                           f'actual type: {type(value)}',
                           f'needed type: {args}']

                    _report('\n'.join(msg))

                return False

    elif typing.get_origin(type_) is not None:
        # Covers both builtin generics (list[int], via types.GenericAlias)
        # and typing-module generics (typing.Iterable[str], typing.List[int],
        # etc., via typing's older _GenericAlias) under the same handling --
        # both expose the same __origin__/__args__ shape.
        origin = type_.__origin__
        args = type_.__args__

        if not isinstance(value, origin):
            if not no_print:
                msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                       f'actual type: {type(value)}',
                       f'needed type: {origin}']

                _report('\n'.join(msg))

            return False

        if (origin is list and len(args) == 1) or (origin is tuple and len(args) == 1) \
                or (origin is tuple and len(args) == 2 and args[1] is Ellipsis):
            # A single type arg on `list` or `tuple` (list[X] / tuple[X]),
            # or the standard tuple[X, ...] homogeneous-variadic-tuple form,
            # all mean "any length, including zero, where every item is
            # this type" in this codebase's convention -- not "must contain
            # exactly one item" (bare tuple[X]'s meaning under strict PEP
            # typing rules, which this codebase doesn't follow here: its
            # sequence-type aliases were built from a PyCharm-generated
            # stub that uses bare tuple[X] the same way as list[X]).
            # Multi-arg list[...]/tuple[...] (this codebase's separate
            # convention for documenting a fixed container shape, e.g.
            # list[float, float, float]) still uses the fixed-length/
            # positional check below.
            elem_type = args[0]
            all_match = True

            for item in value:
                if not _check_type(elem_type, item, arg_name, func, no_print=no_print, self_arg=self_arg):
                    all_match = False

            return all_match

        if origin is list or origin is tuple:
            if len(args) != len(value):
                if not no_print:

                    temp = [type(item) for item in value]
                    temp = origin(temp)

                    msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                           f'actual type: {temp}',
                           f'needed type: {origin(args)}']

                    _report('\n'.join(msg))
                return False

            for i in range(len(args)):
                _check_type(args[i], value[i], arg_name, func, self_arg=self_arg)

    elif (isinstance(type_, type) and isinstance(value, type)
          and type(type_) is not type and type(value) is type(type_)):
        # `type_` and `value` are both classes minted by the same custom
        # metaclass (e.g. Config's ConfigDB-based nested classes, which are
        # used directly as namespace objects -- the class itself is the
        # runtime value, never instantiated). Any two classes sharing that
        # metaclass are treated as interchangeable here, rather than
        # requiring `value` to literally be `type_` or a subclass of it --
        # otherwise every function would need to name the exact nested
        # Config class it expects instead of accepting any config section.
        pass

    elif not isinstance(value, type_):
        if not no_print:

            msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                   f'actual type: {type(value)}',
                   f'needed type: {type_}']

            _report('\n'.join(msg))
        return False

    return True


def do(func):
    return func

    if _FROZEN:
        return func

    try:
        arg_spec = inspect.getfullargspec(func)
    except TypeError:
        return func

    arg_names = arg_spec.args
    arg_annot = arg_spec.annotations
    # Quoted forward-reference annotations (e.g. `-> "Point"`) can't be
    # resolved at decoration time -- for self-referencing classes the name
    # doesn't exist in the module yet at that point. Resolve them lazily on
    # each call instead, once the module has finished loading. Annotations
    # that still can't be resolved (e.g. names only imported under
    # TYPE_CHECKING, which never exist at runtime) are skipped rather than
    # raising.
    globalns = getattr(func, '__globals__', {})

    def _wrapper(*args, **kwargs):
        # `Self` (see _resolve_annotation) resolves against the actual bound
        # self/cls -- always the first positional argument for a method
        # call, or absent entirely for a plain module-level function.
        self_arg = args[0] if args else _NO_SELF

        for i, name in enumerate(arg_names):
            if len(args) == i:
                break

            arg = args[i]
            if name not in arg_annot:
                continue

            annot, resolved = _resolve_annotation(arg_annot[name], globalns, self_arg=self_arg)
            if not resolved:
                continue

            _check_type(annot, arg, name, func, self_arg=self_arg)

        ret = func(*args, **kwargs)

        if 'return' in arg_annot:
            annot, resolved = _resolve_annotation(arg_annot['return'], globalns, self_arg=self_arg)
            if resolved:
                _check_type(annot, ret, 'return', func, self_arg=self_arg)

        return ret

    return _wrapper