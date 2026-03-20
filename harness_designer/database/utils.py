from typing import TYPE_CHECKING

import math
import os

from .. import utils as _utils
from .. import logger as _logger


if TYPE_CHECKING:
    from . import global_db as _global_db


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


def purge_stale_files(db: "_global_db.GLBTables"):
    con = db.connector

    def _get_files_to_prune(table, path):
        alias = table[:-1]
        con.execute(f'SELECT {alias}.uuid, ft.extension FROM {table} {alias} JOIN file_types ft ON {alias}.file_type_id=ft.id;')
        rows = con.fetchall()
        files_db = set([row[0] + '.' + row[1] for row in rows])
        files = set(list(os.listdir(image_path)))
        return list(files.difference(files_db))

    def _remove_files(files, path):
        for file in files:
            file = os.path.join(path, file)
            try:
                os.remove(file)
            except Exception as err:  # NOQA
                _logger.logger.traceback(err, 'PRUNING ERROR')

    image_path = db.settings_table['image_path']
    datasheet_path = db.settings_table['datasheet_path']
    cad_path = db.settings_table['cad_path']
    model_path = db.settings_table['model_path']

    image_diff = _get_files_to_prune('images', image_path)
    _logger.logger.info(f'purging {len(image_diff)} image files from {image_path}...')
    _remove_files(image_diff, image_path)

    datasheet_diff = _get_files_to_prune('datasheets', datasheet_path)
    _logger.logger.info(f'purging {len(datasheet_diff)} datasheet files from {datasheet_path}...')
    _remove_files(datasheet_diff, datasheet_path)

    cad_diff = _get_files_to_prune('cads', cad_path)
    _logger.logger.info(f'purging {len(cad_diff)} cad files from {cad_path}...')
    _remove_files(cad_diff, cad_path)

    model_diff = _get_files_to_prune('models3d', model_path)
    _logger.logger.info(f'purging {len(model_diff)} model files from {model_path}...')
    _remove_files(model_diff, model_path)
