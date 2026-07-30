import inspect
import types
import sys


_FROZEN = hasattr(sys, 'frozen')


def _check_type(type_, value, arg_name, func):

    if isinstance(type_, types.UnionType):
        for type2_ in type_.__args__:
            try:
                _check_type(type2_, value, arg_name, func)
                break
            except TypeError:
                pass
        else:
            msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                   f'actual type: {type(value)}',
                   f'needed type: {type_.__args__}']

            raise TypeError('\n'.join(msg))

    elif isinstance(type_, types.GenericAlias):
        if not isinstance(value, type_.__origin__):
            msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                   f'actual type: {type(value)}',
                   f'needed type: {type_.__origin__}']

            raise TypeError('\n'.join(msg))

        if type_.__origin__ is list or type_.__origin__ is tuple:
            if len(type_.__args__) != len(value):
                temp = [type(item) for item in value]
                temp = type_.__origin__(temp)

                msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
                       f'actual type: {temp}',
                       f'needed type: {type_.__origin__(type_.__args__)}']

                raise TypeError('\n'.join(msg))

            for i in range(len(type_.__args__)):
                _check_type(type_.__args__[i], value[i], arg_name, func)

    elif not isinstance(value, type_):

        msg = [f'\nincorrect type: {func.__qualname__} : {arg_name}',
               f'actual type: {type(value)}',
               f'needed type: {type_}']

        raise TypeError('\n'.join(msg))


def do(func):
    if _FROZEN:
        return func

    arg_spec = inspect.getfullargspec(func)

    arg_names = arg_spec.args
    arg_annot = arg_spec.annotations

    def _wrapper(*args, **kwargs):
        for i, name in enumerate(arg_names):
            if len(args) == i:
                break

            arg = args[i]
            if name not in arg_annot:
                continue

            annot = arg_annot[name]

            _check_type(annot, arg, name, func)

        ret = func(*args, **kwargs)

        if 'return' in arg_annot:
            annot = arg_annot['return']

            _check_type(annot, ret, 'return', func)

        return ret

    return _wrapper