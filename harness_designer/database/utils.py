import math
from .. import utils as _utils


get_appdata = _utils.get_appdata


def _sep_cavity_id(id_):
    res = ''

    if id_[0].isdigit():
        while not id_[-1].isdigit():
            res = id_[-1] + res
            id_ = id_[:-1]
        res = (id_, res)
    else:
        while not id_[0].isdigit():
            res += id_[0]
            id_ = id_[1:]
        res = (res, id_)

    return res


def enumerate_alpha(start, stop):
    res = []

    for i in range(ord(start), ord(stop) + 1):
        res.append(chr(i))

    return res


def _enumerate_int(start, stop):

    res = []

    for i in range(int(start), int(stop) + 1):
        res.append(str(i))

    return res


def _enumerate_ids(start, stop):

    for char in '1234567890':
        if char in start:
            has_numbers = True
            break
    else:
        has_numbers = False

    res = []

    if start.isdigit():
        res.extend(_enumerate_int(start, stop))

    elif has_numbers:
        start_prefix, start_suffix = _sep_cavity_id(start)
        stop_prefix, stop_suffix = _sep_cavity_id(stop)

        if start_prefix.isdigit():
            for prefix in _enumerate_int(start_prefix, stop_prefix):
                for suffix in enumerate_alpha(start_suffix, stop_suffix):
                    res.append(f'{prefix}{suffix}')
        else:
            res = []
            for prefix in enumerate_alpha(start_prefix, stop_prefix):
                for suffix in _enumerate_int(start_suffix, stop_suffix):
                    res.append(f'{prefix}{suffix}')
    else:
        res.extend(enumerate_alpha(start, stop))

    return res


def get_cavity_ids(str_cav):
    in_ids = [item.strip() for item in str_cav.split(',')]
    out_ids = []

    for id_ in in_ids:
        if '-' in id_:
            start_id, stop_id = [item.strip() for item in id_.split('-')]
            out_ids.extend(_enumerate_ids(start_id, stop_id))
        else:
            out_ids.append(id_)

    return out_ids
