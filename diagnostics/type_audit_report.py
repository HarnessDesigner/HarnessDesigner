"""List the wrong calls that ``harness_designer/check_types.py`` recorded.

While the app runs, ``check_types.do`` compares the annotations of every decorated function with what really arrives
(each parameter, and the return value) and writes only what does not fit into a SQLite file, in two tables:

* ``functions`` -- one row per function that was called wrongly: name, signature and return type as annotated, source
  file and line.
* ``calls`` -- one row per wrong call: the calling function, its file and line, the signature of the call as it was made
  (the type of everything that was passed) and the type that came back, which is empty when the call raised.

This script prints them side by side, so the mismatch can be read by eye.

Usage::

    python diagnostics/type_audit_report.py [--db FILE] [--function REGEX] [--file REGEX] [--md FILE]

``--db`` defaults to ``type_audit.sqlite3`` in the repo root (or the file named by ``HARNESS_TYPE_AUDIT_DB``). ``--md`` also
writes a checklist table with *Fix?* and *Comments* columns.
"""

import argparse
import os
import re
import sqlite3
import sys


def with_return(signature: str, return_type: str) -> str:
    if return_type:
        return '%s -> %s' % (signature, return_type)

    return signature


def load(path: str, function: str, file: str) -> list[tuple[str, str, str, str, int, list[tuple[str, str, int, str, str]]]]:
    """(name, signature, return type, file, line, [(caller, file, line, signature, return type), ...]) per function."""

    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True)
    try:
        functions = con.execute(
            'SELECT id, name, signature, return_type, file, line FROM functions ORDER BY file, line, name').fetchall()

        by_function: dict[int, list[tuple[str, str, int, str, str]]] = {}
        for func_id, caller, call_file, call_line, signature, return_type in con.execute(
                'SELECT func_id, caller, file, line, signature, return_type FROM calls ORDER BY file, line, caller'):
            by_function.setdefault(func_id, []).append((caller, call_file, call_line, signature, return_type))
    finally:
        con.close()

    function_filter = None
    if function:
        function_filter = re.compile(function)

    file_filter = None
    if file:
        file_filter = re.compile(file)

    found = []
    for func_id, name, signature, return_type, source, line in functions:
        if function_filter is not None and not function_filter.search(name):
            continue

        if file_filter is not None and not file_filter.search(source):
            continue

        found.append((name, signature, return_type, source, line, by_function.get(func_id, [])))

    return found


def print_text(path: str, found: list[tuple[str, str, str, str, int, list[tuple[str, str, int, str, str]]]]) -> None:
    total = sum(len(item[5]) for item in found)
    print('database: %s' % path)
    print('functions called wrongly: %d | wrong calls: %d' % (len(found), total))

    for name, signature, return_type, source, line, calls in found:
        print()
        print('%s:%d  %s' % (source, line, name))
        print('    annotated: %s' % with_return(signature, return_type))

        for caller, call_file, call_line, passed, returned in calls:
            print('    called:    %s' % with_return(passed, returned))
            print('               from %s:%d in %s' % (call_file, call_line, caller))


def cell(text: str) -> str:
    return text.replace('\n', ' ').replace('|', '\\|')


def write_markdown(path: str, db: str, found: list[tuple[str, str, str, str, int, list[tuple[str, str, int, str, str]]]]) -> None:
    lines = ['# Wrong calls', '', 'From `%s`. Mark `[x]` in *Fix?* and use *Comments* freely.' % db, '']
    lines.append('| Fix? | Comments | Function | Annotated | Called | Called from |')
    lines.append('|:-:|---|---|---|---|---|')

    for name, signature, return_type, source, line, calls in found:
        for caller, call_file, call_line, passed, returned in calls:
            lines.append('| [ ] |  | `%s` (%s:%d) | `%s` | `%s` | %s:%d in `%s` |' % (
                cell(name), source, line, cell(with_return(signature, return_type)), cell(with_return(passed, returned)),
                call_file, call_line, cell(caller)))

    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')

    print('wrote %s' % path)


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_db = os.environ.get('HARNESS_TYPE_AUDIT_DB') or os.path.join(root, 'type_audit.sqlite3')

    parser = argparse.ArgumentParser(description='List the wrong calls recorded by check_types.')
    parser.add_argument('--db', default=default_db, help='database written by check_types.do')
    parser.add_argument('--function', default='', help='only functions whose name matches this regex')
    parser.add_argument('--file', default='', help='only functions whose source file matches this regex')
    parser.add_argument('--md', default='', help='also write a checklist table to this file')
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print('no database at %s -- nothing wrong has been recorded yet (or the check was off)' % args.db)
        return 1

    found = load(args.db, args.function, args.file)
    print_text(args.db, found)

    if args.md:
        write_markdown(args.md, args.db, found)

    return 0


if __name__ == '__main__':
    sys.exit(main())
