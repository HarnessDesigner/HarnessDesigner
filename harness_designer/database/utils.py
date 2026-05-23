# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Utility helpers for database identifier parsing and file maintenance."""

from typing import TYPE_CHECKING

import os

from .. import utils as _utils
from .. import logger as _logger


if TYPE_CHECKING:
    from . import global_db as _global_db


get_appdata = _utils.get_appdata


def _sep_cavity_id(id_):
    """Split a cavity identifier into its alphabetic and numeric segments.

    :param id_: Cavity identifier to split or expand.
    :type id_: UNKNOWN

    :returns: The separated identifier components.
    :rtype: tuple[str, str]
    """
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
    """Enumerate inclusive alphabetical identifiers between two characters.

    :param start: Inclusive start value for the range.
    :type start: UNKNOWN
    :param stop: Inclusive stop value for the range.
    :type stop: UNKNOWN

    :returns: A list of inclusive alphabetical identifiers.
    :rtype: list[str]
    """
    res = []

    for i in range(ord(start), ord(stop) + 1):
        res.append(chr(i))

    return res


def _enumerate_int(start, stop):

    """Enumerate inclusive numeric identifiers between two values.

    :param start: Inclusive start value for the range.
    :type start: UNKNOWN
    :param stop: Inclusive stop value for the range.
    :type stop: UNKNOWN

    :returns: A list of inclusive numeric identifiers as strings.
    :rtype: list[str]
    """
    res = []

    for i in range(int(start), int(stop) + 1):
        res.append(str(i))

    return res


def _enumerate_ids(start, stop):

    """Expand a mixed cavity identifier range into individual identifiers.

    :param start: Inclusive start value for the range.
    :type start: UNKNOWN
    :param stop: Inclusive stop value for the range.
    :type stop: UNKNOWN

    :returns: Expanded identifiers for the requested range.
    :rtype: list[str]
    """
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
    """Expand a comma-separated cavity identifier specification.

    :param str_cav: Comma-separated cavity identifier specification.
    :type str_cav: UNKNOWN

    :returns: Expanded cavity identifiers.
    :rtype: list[str]
    """
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
    """Remove resource files that are no longer referenced by the database.

    :param db: Database table collection used to locate configured resource paths.
    :type db: '_global_db.GLBTables'

    :returns: ``None``.
    :rtype: None
    """
    con = db.connector

    def _get_files_to_prune(table, path):
        """Return files present on disk that are missing from the database records.

        :param table: Database table name containing file references.
        :type table: UNKNOWN
        :param path: Directory that should contain the referenced files.
        :type path: UNKNOWN

        :returns: File names present on disk but not referenced in the database.
        :rtype: list[str]
        """
        alias = table[:-1]
        con.execute(f'SELECT {alias}.uuid, ft.extension FROM {table} {alias} JOIN file_types ft ON {alias}.file_type_id=ft.id;')
        rows = con.fetchall()
        files_db = set([row[0] + '.' + row[1] for row in rows])
        files = set(list(os.listdir(image_path)))
        return list(files.difference(files_db))

    def _remove_files(files, path):
        """Delete the supplied files from disk, logging any failures.

        :param files: File names to remove from ``path``.
        :type files: UNKNOWN
        :param path: Directory containing the files to remove.
        :type path: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
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
