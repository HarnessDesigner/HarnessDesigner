# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Rewrite of :mod:`harness_designer.ui.dialogs.part_search`.

Design background: see the plan this was built from
(``C:\\Users\\drsch\\.claude\\plans\\smooth-jumping-gosling.md``) and the
session it came out of. ``part_search.py`` is left completely untouched
and is still the dialog every caller actually uses -- nothing here is
wired in yet. This module is a standalone, complete replacement
candidate.

The module is organized bottom-up:
    1. The query language -- pure Python, no Qt/DB imports, safe to
       import and exercise on its own (``parse``/``to_sql``/``to_text``).
    2. Search-history persistence (``Config``-backed).
    3. Async query plumbing (``QueryScope``).
    4. Qt widgets (search box, filter-assist panels, results view,
       "Searching..." popup, help dialog).
    5. ``SearchDialog`` itself, which owns all of the above.
"""
from typing import Any, Callable, Iterator, TYPE_CHECKING, Union

import re
import difflib
import sqlite3
import dataclasses
import collections
from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import dialog_base as _dialog_base
from ..widgets import auto_complete as _auto_complete
from ... import logger as _logger
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ...database import db_connectors as _db_connectors
    from ...database.global_db import bases as _glb_bases
    from ..editor_db import base as _editor_db_base


# =====================================================================
# 1. Query language -- pure, Qt-free, unit-testable on its own
# =====================================================================

#: The only comparison operators this grammar ever recognizes. Order
#: matters: longer operators must be checked before their single-char
#: prefixes (`>=` before `>`), which is why this is a tuple, not a set.
OPERATORS: tuple[str, ...] = ('==', '!=', '~=', '>=', '<=', '>', '<')

#: Numeric-only comparisons (meaningless against text/FK columns).
_NUMERIC_ONLY_OPERATORS = ('>=', '<=', '>', '<')

#: Internal sentinel key for the unscoped/default clause inside
#: SearchParameters.columns -- never a real field_name, so it can't
#: collide with one.
DEFAULT_KEY = '\x00default'

#: Preferred default columns a bare (unscoped) search term is checked
#: against, when present on the table -- mirrors today's part_search.py
#: behavior (part_number OR description).
_PREFERRED_DEFAULT_COLUMNS = ('part_number', 'description')

_EPSILON = 1e-9


@dataclasses.dataclass(frozen=True)
class SearchTerm:
    """
    One atomic condition. Exactly one of ``word`` / ``phrase`` /
    (``operator`` + ``value``) is ever set.

    ``word``: from an unquoted run of words -- each word in the run
    becomes its own ``SearchTerm`` (see ``_tokenize_value_text``), all
    landing in the same AND-group. Implicit match kind is resolved per
    column KIND at SQL-build time (``~=`` on free-text columns, ``==``
    on FK/enum/numeric columns) -- see ``_term_sql``.

    ``phrase``: from a quoted ``"..."`` with no operator prefix -- one
    literal string, word order/adjacency preserved. Same implicit-kind
    resolution as ``word``.

    ``operator`` + ``value``: an explicit ``<op><value>`` term (no
    space between them), one of the 7 whitelisted operators in
    ``OPERATORS``. Always overrides the implicit default.
    """

    word: str | None = None
    phrase: str | None = None
    operator: str | None = None
    value: str | None = None


@dataclasses.dataclass
class ColumnSearch:
    """
    One column's search: a list of OR'd groups, each group a list of
    AND'd :class:`SearchTerm`. ``comma`` in the text form starts a new
    group (OR); a run of terms separated only by whitespace stays in
    the same group (AND). Repeating a column's scope elsewhere in the
    text (the "merge rule") just appends more OR'd groups here -- see
    :func:`parse`.
    """

    column: str
    groups: list[list[SearchTerm]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class SearchParameters:
    """
    The parsed form of a search-box query string -- also the direct
    transport type for a caller wanting to preload the dialog
    programmatically (:meth:`to_text` renders it back to the exact text
    a user could have typed, so a preloaded search is never a hidden
    side-channel -- see ``SearchDialog.__init__``).
    """

    columns: "collections.OrderedDict[str, ColumnSearch]" = (  # NOQA
        dataclasses.field(default_factory=collections.OrderedDict))

    @_check_types.do
    def add(self, column: str, *terms: SearchTerm) -> None:
        """
        Convenience for callers building params by hand: add one
        OR-group (all of *terms* AND'd together) to *column*, merging
        with any group(s) already present for that column.
        """

        if column in self.columns:
            self.columns[column].groups.append(list(terms))
        else:
            self.columns[column] = ColumnSearch(column, [list(terms)])

    @_check_types.do
    def set_column(self, column: str, groups: list[list[SearchTerm]]) -> None:
        """
        Replace *column*'s entire clause with *groups* (a list of OR'd
        AND-groups) -- unlike :meth:`add`, this does NOT merge with
        whatever was there before. This is what filter-assist panels use
        to keep the search text in sync with their own current UI state
        (checked items / spinbox values), which is already the complete
        desired state for that column, not one more thing to merge in --
        merging there could only ever grow a column's clause, never
        shrink it back down when an option got unchecked. An empty
        *groups* removes the column's clause entirely.
        """

        non_empty = [list(g) for g in groups if g]
        if non_empty:
            self.columns[column] = ColumnSearch(column, non_empty)
        else:
            self.columns.pop(column, None)

    @classmethod
    @_check_types.do
    def from_part_numbers(cls, part_numbers: list[str] | None) -> Union["SearchParameters", None]:
        """
        Convenience for the common "Add X" case: a caller has only a
        flat compat part-number list (a catalog's manually-curated
        compat_terminals/compat_housings/... array) and wants it seeded
        into the dialog as ``part number: "PN1","PN2"`` -- literally
        visible, editable search text, not a hidden side-channel.
        Returns None for an empty/None list so callers can pass the
        result straight through as ``initial_params`` unconditionally.
        """

        if not part_numbers:
            return None

        params = cls()
        for pn in part_numbers:
            params.add('part_number', SearchTerm(phrase=pn))

        return params

    @_check_types.do
    def to_text(self, schema: "TableSchema") -> str:
        """
        Render back to the canonical search-box text -- what a panel
        click or a compat-seed builder actually types into the box.
        """

        parts = []
        for col_name, col_search in self.columns.items():
            rendered = ','.join(_render_group(g) for g in col_search.groups if g)
            if not rendered:
                continue

            if col_name == DEFAULT_KEY:
                parts.append(rendered)
            else:
                info = schema.columns.get(col_name)
                if info is not None:
                    label = info.label
                else:
                    label = col_name

                parts.append(f'{label}: {rendered}')

        return ' '.join(parts)


@_check_types.do
def _render_term(term: SearchTerm) -> str:
    if term.word is not None:
        return term.word

    if term.phrase is not None:
        return f'"{term.phrase}"'

    value = term.value or ''
    if any(c.isspace() for c in value):
        value = f'"{value}"'

    return f'{term.operator}{value}'


@_check_types.do
def _render_group(group: list[SearchTerm]) -> str:
    return ' '.join(_render_term(t) for t in group)


@dataclasses.dataclass(frozen=True)
class ParseProblem:
    """
    One flagged issue in a search-box string, in plain language (same
    voice as the help dialog) with the exact character span in the raw
    text it applies to -- used to red-highlight the offending text
    (``SearchTextEdit.set_error_spans``) instead of just rejecting the
    whole box.
    """

    start: int
    end: int
    message: str


@dataclasses.dataclass
class ParseResult:
    params: SearchParameters
    problems: list[ParseProblem] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class ColumnInfo:
    field_name: str
    label: str
    kind: str  # 'text' | 'fk' | 'numeric'
    sql_type: str
    ref_table: str | None = None
    ref_field: str | None = None


@dataclasses.dataclass
class TableSchema:
    """
    Everything the parser/SQL-builder/UI need to know about one
    catalog table, resolved ONCE, synchronously, with zero queries
    beyond a couple of cheap ``PRAGMA`` calls -- see :func:`build_schema`.
    Doubles as the identifier WHITELIST: a column only ever ends up in
    generated SQL text if it's a key of ``columns`` here (see
    ``_term_sql``/``to_sql``) -- never a raw string taken from typed
    search text.
    """

    table: str
    columns: dict[str, ColumnInfo] = dataclasses.field(default_factory=dict)

    # normalized alias -> field_name
    label_lookup: dict[str, str] = dataclasses.field(default_factory=dict)
    default_columns: tuple[str, ...] = ()


@_check_types.do
def _label_aliases(label: str) -> Iterator[str]:
    """
    Yield normalized (lowercase, whitespace-collapsed) forms of a
    column_mapping label a user could plausibly type -- the literal
    label, and the same thing with a trailing " (unit)" parenthetical
    stripped (e.g. "Blade Size (mm)" -> also "blade size").
    """

    base = re.sub(r'\s+', ' ', label.strip().lower())
    yield base

    stripped = re.sub(r'\s*\([^)]*\)\s*$', '', base).strip()
    if stripped and stripped != base:
        yield stripped


@_check_types.do
def build_schema(
    conn: "_db_connectors.SQLConnector",
    table_name: str,
    column_mapping: dict
) -> TableSchema:
    """
    Build a :class:`TableSchema` for *table_name* from *column_mapping*
    (the results panel's own page-class attribute that describes the
    database table being accessed, e.g.
    ``ui.editor_db.terminal.TerminalsPage.column_mapping`` -- a dict
    keyed 0, 1, 2, ... in the exact field order that page already
    presents, each value carrying that field's display label plus its
    ``field_name``/``ref_table``/``ref_field``) plus a single
    synchronous ``PRAGMA table_info`` call for real SQL types -- no
    other querying. Column order is *column_mapping*'s own key order,
    honored end to end (filter-assist panel strip order, help-dialog
    example selection, etc.) -- not re-derived from anywhere else (in
    particular NOT ``TableBase.field_names``, which is a bare,
    alphabetized column-name list with none of this descriptive info
    and isn't what "the results panel's own attribute describing the
    table" refers to here). FK/ref info comes straight from
    *column_mapping* itself, not from ``PRAGMA foreign_key_list``.
    """

    conn.execute(f'PRAGMA table_info("{table_name}")')
    type_by_column = {row[1]: (row[2] or '').upper() for row in conn.fetchall()}

    columns: dict[str, ColumnInfo] = {}
    label_lookup: dict[str, str] = {}

    for idx in sorted(column_mapping.keys()):
        entry = column_mapping[idx]
        label, info = entry[0], entry[1]
        field_name = info.get('field_name', '')

        if (
            not field_name or
            field_name == 'id' or
            field_name not in type_by_column
        ):
            continue

        ref_table = info.get('ref_table')
        ref_field = info.get('ref_field')
        sql_type = type_by_column[field_name]

        if ref_table and ref_field:
            kind = 'fk'
        elif any(t in sql_type
                 for t in ('INT', 'REAL', 'FLOA', 'DOUB', 'NUMERIC')):

            kind = 'numeric'
        else:
            kind = 'text'

        columns[field_name] = ColumnInfo(
            field_name, label, kind, sql_type, ref_table, ref_field)

        for alias in _label_aliases(label):
            label_lookup.setdefault(alias, field_name)

    default_columns = tuple(c for c in _PREFERRED_DEFAULT_COLUMNS
                            if c in columns)

    return TableSchema(table_name, columns, label_lookup, default_columns)


@_check_types.do
def _trigger_pattern(schema: TableSchema) -> re.Pattern | None:
    """
    Compile the `<label>: ` column-scope trigger regex for *schema*,
    or None if the table has no labeled columns at all. Labels are
    tried longest-first so e.g. "wire awg (min)" wins over a shorter
    "wire" alias at the same position; the left boundary requires
    start-of-text or preceding whitespace so "engender:" can't match
    "gender:" as a false positive.
    """

    if not schema.label_lookup:
        return None

    labels = sorted(schema.label_lookup.keys(), key=len, reverse=True)
    alternation = '|'.join(re.escape(label) for label in labels)

    return re.compile(r'(?:^|(?<=\s))(' + alternation + r'):[ \t]', re.IGNORECASE)


#: A `word:` -- like shape that COULD be an attempted (but misspelled)
#: column scope, used only for the best-effort "did you mean" check.
#: Requires a letter start and 3+ chars so short/numeric left sides
#: (a ratio like "3:1") never trigger it.
_CANDIDATE_LABEL_RE = re.compile(
    r'(?:^|(?<=\s))([A-Za-z][A-Za-z0-9 ]{2,40}?):[ \t]')


@_check_types.do
def _try_float(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@_check_types.do
def _tokenize_value_text(
    text: str,
    base_offset: int
) -> tuple[list[list[tuple[str, int, int]]], bool]:

    """
    Split one clause's raw value text into OR-groups (comma-
    separated) of AND'd raw term strings (whitespace-separated within a
    group), each tagged with its absolute ``(start, end)`` offset in
    the ORIGINAL search text (via *base_offset*). A single left-to-
    right character walk that respects quoting for both separators at
    once, so an unterminated quote is detected here rather than by a
    separate pass. Returns ``(groups, unterminated)``.
    """

    groups: list[list[tuple[str, int, int]]] = [[]]
    buf_start: int | None = None
    buf_chars: list[str] = []
    in_quote = False

    @_check_types.do
    def _flush() -> None:
        nonlocal buf_start, buf_chars

        if buf_chars:
            groups[-1].append((
                ''.join(buf_chars), buf_start + base_offset,
                buf_start + len(buf_chars) + base_offset))

        buf_chars = []
        buf_start = None

    for i, ch in enumerate(text):
        if ch == '"':
            if buf_start is None:
                buf_start = i

            buf_chars.append(ch)
            in_quote = not in_quote
        elif in_quote:
            buf_chars.append(ch)
        elif ch == ',':
            _flush()
            groups.append([])
        elif ch.isspace():
            _flush()
        else:
            if buf_start is None:
                buf_start = i

            buf_chars.append(ch)

    unterminated = in_quote
    _flush()

    return [g for g in groups if g], unterminated


@_check_types.do
def _classify_term(
    term_text: str,
    start: int,
    end: int
) -> tuple[SearchTerm | None, ParseProblem | None]:

    """
    Turn one raw term string into a :class:`SearchTerm`, or a
    :class:`ParseProblem` if it's structurally malformed (an operator
    with nothing after it).
    """

    if len(term_text) >= 2 and term_text[0] == '"' and term_text[-1] == '"':
        return SearchTerm(phrase=term_text[1:-1]), None

    for op in OPERATORS:
        if term_text.startswith(op):
            raw_value = term_text[len(op):]
            if (
                len(raw_value) >= 2 and
                raw_value[0] == '"' and
                raw_value[-1] == '"'
            ):
                raw_value = raw_value[1:-1]

            if not raw_value:
                return None, ParseProblem(
                    start, end,
                    f"'{op}' needs a value right after it, e.g. '{op}2.8'.")

            return SearchTerm(operator=op, value=raw_value), None

    return SearchTerm(word=term_text), None


@_check_types.do
def _validate_term(
    term: SearchTerm,
    field_name: str,
    schema: TableSchema,
    start: int,
    end: int
) -> ParseProblem | None:

    """
    Deterministic, schema-driven validation -- see the module design
    notes for exactly which cases are (and aren't) flagged as errors.
    """

    if field_name == DEFAULT_KEY:
        if term.operator in _NUMERIC_ONLY_OPERATORS:
            return ParseProblem(
                start, end,
                f"'{term.operator}' needs a column name in front of it, "
                f"e.g. 'blade size: {term.operator}{term.value}'.")

        return None

    col = schema.columns.get(field_name)
    if col is None:
        return None

    if term.operator in _NUMERIC_ONLY_OPERATORS and col.kind != 'numeric':
        return ParseProblem(
            start, end,
            f"'{term.operator}' only makes sense on a number column -- "
            f"'{col.label}' isn't one.")

    if (
        term.operator is not None and
        col.kind == 'numeric' and
        _try_float(term.value) is None
    ):
        return ParseProblem(
            start, end,
            f"'{term.value}' isn't a number, but '{col.label}' needs one.")

    if (
        term.word is not None and
        col.kind == 'numeric' and
        _try_float(term.word) is None
    ):
        return ParseProblem(
            start, end,
            f"'{term.word}' isn't a number, but '{col.label}' needs one.")

    return None


@_check_types.do
def _flag_unmatched_labels(
    text: str,
    schema: TableSchema,
    matched_spans: list[tuple[int, int]]
) -> list[ParseProblem]:

    """
    Best-effort "did you mean" pass: a `word:`-shaped span that
    ISN'T a real trigger (so it fell through into ordinary search text)
    but is a close spelling match to a real column label probably was
    a typo -- flag it. Not attempted for spans already claimed by a
    real trigger.
    """

    problems = []
    for m in _CANDIDATE_LABEL_RE.finditer(text):
        if any(s <= m.start() < e for s, e in matched_spans):
            continue

        candidate = re.sub(r'\s+', ' ', m.group(1).strip().lower())
        if candidate in schema.label_lookup:
            continue

        close = difflib.get_close_matches(
            candidate, schema.label_lookup.keys(), n=1, cutoff=0.72)

        if not close:
            continue

        real_field = schema.label_lookup[close[0]]
        real_label = schema.columns[real_field].label
        problems.append(ParseProblem(
            m.start(), m.end() - 1,
            f"There's no column called '{m.group(1).strip()}' -- did you mean '{real_label}'?"))

    return problems


@_check_types.do
def parse(text: str, schema: TableSchema) -> ParseResult:
    """
    Parse search-box *text* against *schema*. Always returns every
    problem found (doesn't stop at the first one) -- see
    :class:`ParseResult`.
    """

    problems: list[ParseProblem] = []
    columns: "collections.OrderedDict[str, ColumnSearch]" = collections.OrderedDict()

    pattern = _trigger_pattern(schema)
    if pattern is not None:
        triggers = list(pattern.finditer(text))
    else:
        triggers = []

    clauses: list[tuple[str, int, int]] = []
    prev_end = 0
    prev_field = DEFAULT_KEY
    for m in triggers:
        clauses.append((prev_field, prev_end, m.start()))
        prev_field = schema.label_lookup[m.group(1).lower()]
        prev_end = m.end()

    clauses.append((prev_field, prev_end, len(text)))

    for field_name, start, end in clauses:
        value_text = text[start:end]
        if not value_text.strip():
            continue

        groups_raw, unterminated = _tokenize_value_text(value_text, start)
        if unterminated:
            problems.append(ParseProblem(
                start, end, 'This has an opening " with nothing to close it.'))
            continue

        groups: list[list[SearchTerm]] = []
        for raw_group in groups_raw:
            terms: list[SearchTerm] = []
            for term_text, t_start, t_end in raw_group:
                term, problem = _classify_term(term_text, t_start, t_end)
                if problem is not None:
                    problems.append(problem)
                    continue

                validation = _validate_term(
                    term, field_name, schema, t_start, t_end)

                if validation is not None:
                    problems.append(validation)
                    continue

                terms.append(term)

            if terms:
                groups.append(terms)

        if not groups:
            continue

        if field_name in columns:
            columns[field_name].groups.extend(groups)
        else:
            columns[field_name] = ColumnSearch(field_name, groups)

    matched_spans = [(m.start(), m.end()) for m in triggers]
    problems.extend(_flag_unmatched_labels(text, schema, matched_spans))
    problems.sort(key=lambda p: p.start)

    return ParseResult(SearchParameters(columns), problems)


# ---------------------------------------------------------------------
# SQL safety: every VALUE below is passed as a bound `?` parameter,
# never string-interpolated. Every IDENTIFIER (column/table name) below
# comes only from `schema`/`col` -- never raw text. See the design
# notes' "SQL safety" section for the full rationale; do not add a
# string-built value anywhere in this file.
# ---------------------------------------------------------------------

@_check_types.do
def _escape_like(value: str) -> str:
    value = value.replace('\\', '\\\\')
    value = value.replace('%', '\\%')
    value = value.replace('_', '\\_')

    return value


@_check_types.do
def _term_sql(term: SearchTerm, col: ColumnInfo) -> tuple[str, list[Any]]:
    """
    Return (sql_fragment, params) for one term against one real
    (non-default) column. A term/kind combination that isn't
    meaningful (e.g. `~=` on a numeric column) resolves to an always-
    false fragment rather than an error -- parse() already flags the
    cases meant to be hard errors; anything reaching here that isn't
    meaningful is the documented "matches nothing" behavior.
    """

    operator = term.operator
    if operator is None:
        if term.phrase is not None:
            value = term.phrase
        elif term.word is not None:
            value = term.word
        else:
            return '0', []

        if col.kind != 'text':
            operator = '=='
        else:
            operator = '~='
    else:
        value = term.value or ''

    if col.kind == 'fk':
        if operator == '==':
            return (f"t.{col.field_name} IN (SELECT id FROM {col.ref_table} "
                    f"WHERE {col.ref_field} = ? COLLATE NOCASE)", [value])

        if operator == '!=':
            return (f"t.{col.field_name} NOT IN (SELECT id FROM {col.ref_table} "
                    f"WHERE {col.ref_field} = ? COLLATE NOCASE)", [value])

        if operator == '~=':
            pattern = '%' + _escape_like(value) + '%'
            return (f"t.{col.field_name} IN (SELECT id FROM {col.ref_table} "
                    f"WHERE {col.ref_field} LIKE ? ESCAPE '\\')", [pattern])

        return '0', []

    if col.kind == 'numeric':
        num = _try_float(value)
        if num is None:
            return '0', []

        is_real = any(
            t in col.sql_type for t in ('REAL', 'FLOA', 'DOUB', 'NUMERIC'))

        if operator == '==':
            if is_real:
                return f"ABS(t.{col.field_name} - ?) < {_EPSILON}", [num]

            return f"t.{col.field_name} = ?", [num]

        if operator == '!=':
            if is_real:
                return f"ABS(t.{col.field_name} - ?) >= {_EPSILON}", [num]

            return f"t.{col.field_name} != ?", [num]

        if operator == '>=':
            return f"t.{col.field_name} >= ?", [num]

        if operator == '<=':
            return f"t.{col.field_name} <= ?", [num]

        if operator == '>':
            return f"t.{col.field_name} > ?", [num]

        if operator == '<':
            return f"t.{col.field_name} < ?", [num]

        return '0', []

    # text column
    if operator == '==':
        return f"t.{col.field_name} = ? COLLATE NOCASE", [value]

    if operator == '!=':
        return f"t.{col.field_name} != ? COLLATE NOCASE", [value]

    if operator == '~=':
        return f"t.{col.field_name} LIKE ? ESCAPE '\\'", ['%' + _escape_like(value) + '%']

    return '0', []


@_check_types.do
def _default_term_sql(term: SearchTerm, schema: TableSchema) -> tuple[str, list[Any]]:
    """
    Same as :func:`_term_sql` but for the unscoped/default clause --
    OR'd across every one of ``schema.default_columns``.
    """

    if term.operator is not None:
        operator, value = term.operator, term.value or ''
    elif term.phrase is not None:
        operator, value = '~=', term.phrase
    elif term.word is not None:
        operator, value = '~=', term.word
    else:
        return '0', []

    clauses, params = [], []
    for field_name in schema.default_columns:
        col = schema.columns[field_name]
        frag, p = _term_sql(SearchTerm(operator=operator, value=value), col)
        clauses.append(frag)
        params.extend(p)

    if not clauses:
        return '0', []

    return '(' + ' OR '.join(clauses) + ')', params


@_check_types.do
def to_sql(params: SearchParameters, schema: TableSchema) -> tuple[str, list[Any]]:
    """
    The ONLY place a WHERE clause gets assembled. Every column's
    OR-groups-of-AND'd-terms combine into one bound-parameter clause,
    all columns AND'd together.
    """

    column_clauses = []
    sql_params: list[Any] = []

    for col_name, col_search in params.columns.items():
        group_clauses = []
        for group in col_search.groups:
            term_clauses = []
            for term in group:
                if col_name == DEFAULT_KEY:
                    frag, p = _default_term_sql(term, schema)
                else:
                    col = schema.columns.get(col_name)
                    if col is None:
                        continue

                    frag, p = _term_sql(term, col)
                term_clauses.append(frag)
                sql_params.extend(p)

            if term_clauses:
                group_clauses.append('(' + ' AND '.join(term_clauses) + ')')

        if group_clauses:
            column_clauses.append('(' + ' OR '.join(group_clauses) + ')')

    if not column_clauses:
        return '', []

    return ' AND '.join(column_clauses), sql_params


@_check_types.do
def without_column(params: SearchParameters, column: str) -> SearchParameters:
    """
    Return a copy of *params* with *column* entirely removed -- used
    by the zero-result diagnostic to test "would dropping this one
    column produce any results at all?".
    """

    remaining = collections.OrderedDict(
        (k, v) for k, v in params.columns.items() if k != column)

    return SearchParameters(remaining)


# =====================================================================
# 2. Search history -- Config-backed, MRU, capped at 50, per table
# =====================================================================

_HISTORY_CAP = 50


@_check_types.do
def get_search_history(table: str) -> list[str]:
    history = dict(_config.Config.part_search.history or {})

    return list(history.get(table, []))


@_check_types.do
def record_search(table: str, text: str) -> None:
    """
    Record a successfully-run search into history: move-to-end if it
    already exists (no duplicates, most-recent-last), capped at
    :data:`_HISTORY_CAP`, persisted via the existing ``Config`` system
    (so it survives both closing this dialog and restarting the app --
    see ``Config.part_search`` in ``config.py``).
    """

    text = text.strip()
    if not text:
        return

    history = dict(_config.Config.part_search.history or {})
    entries = list(history.get(table, []))

    if text in entries:
        entries.remove(text)

    entries.append(text)

    if len(entries) > _HISTORY_CAP:
        entries = entries[-_HISTORY_CAP:]

    history[table] = entries
    _config.Config.part_search.history = history


# =====================================================================
# 3. Async query plumbing
# =====================================================================

class _QueryWorker(QtCore.QObject):
    """Runs SQL on a dedicated worker thread against its own SQLite
    connection -- mirrors part_search.py's own worker exactly (that
    part of today's design isn't the problem, see the plan notes)."""

    # request_id, rows, error
    resultReady: QtCore.SignalInstance = QtCore.Signal(int, object, object)

    @_check_types.do
    def __init__(self, db_path: str):
        super().__init__()
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @QtCore.Slot()
    @_check_types.do
    def open(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)

    @QtCore.Slot(int, str, list)
    @_check_types.do
    def run_query(self, request_id: int, sql: str, params: list) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            self.resultReady.emit(request_id, rows, None)
        except Exception as exc:  # NOQA
            self.resultReady.emit(request_id, None, exc)


class QueryScope(QtCore.QObject):
    """
    One reusable "run async, drop the result if stale" primitive
    (see plan §6) -- replaces the hand-threaded request-id/generation-
    token bookkeeping today's part_search.py repeats in several places.
    Owns ONE long-lived worker thread for the SearchDialog's whole
    lifetime; :meth:`new_generation` marks every previously-issued,
    still-in-flight request as stale without needing to cancel it.
    """

    _queryRequested: QtCore.SignalInstance = QtCore.Signal(int, str, list)

    @_check_types.do
    def __init__(self, db_path: str, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._next_id = 0
        self._pending: dict[int, tuple[int, Callable]] = {}
        self._gen = 0

        self._thread = QtCore.QThread(parent)
        self._worker = _QueryWorker(db_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.open)  # NOQA
        self._queryRequested.connect(self._worker.run_query)  # NOQA
        self._worker.resultReady.connect(self._on_result)
        self._thread.start()

    @_check_types.do
    def new_generation(self) -> None:
        """
        Start a new generation -- results from any request issued
        before this call are silently dropped when they arrive.
        """

        self._gen += 1
        self._pending.clear()

    @_check_types.do
    def run(self, sql: str, params: list, callback: Callable) -> None:
        self._next_id += 1
        request_id = self._next_id
        self._pending[request_id] = (self._gen, callback)
        self._queryRequested.emit(request_id, sql, list(params))

    @_check_types.do
    def _on_result(self, request_id: int,
                   rows: list | None, error: Exception | None) -> None:

        entry = self._pending.pop(request_id, None)
        if entry is None:
            return

        gen, callback = entry
        if gen != self._gen:
            return

        if error is not None:
            _logger.error('Search dialog query failed:', error)
            callback([])
            return

        callback(rows)

    @_check_types.do
    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait()


# =====================================================================
# 4a. Search box widget -- red-span highlighting + contextual autocomplete
#     + keyboard-driven history (Down steps through it, Up opens a full
#     scrollable dropdown -- replaces the earlier "History" toolbutton)
# =====================================================================

class _HistoryPopup(QtWidgets.QFrame):
    """
    Scrollable dropdown of every past search for one table, opened by
    pressing Up in the search box. A real ``Qt.WindowType.Popup`` top-
    level widget (same window-type idiom ``QComboBox``'s own dropdown
    uses) positioned directly below the search box, same width as it --
    arrow keys move the current row, Enter or a click selects (fills
    the search box and closes), Escape (or losing focus, automatic for
    a ``Popup``-flagged window) closes without selecting.
    """

    entrySelected: QtCore.SignalInstance = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent, QtCore.Qt.WindowType.Popup)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)

        self.list = QtWidgets.QListWidget(self)
        self.list.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.list.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.list)

    @_check_types.do
    def show_for(self, entries: list[str], anchor: QtWidgets.QWidget) -> None:
        """Populate with *entries* (most-recent-first) and show directly
        below *anchor*, matching its width."""
        self.list.clear()
        self.list.addItems(entries)

        self.setFixedWidth(anchor.width())

        if self.list.count():
            row_height = self.list.sizeHintForRow(0)
        else:
            row_height = 20

        max_visible_rows = 10
        visible_rows = min(self.list.count(), max_visible_rows)
        self.setFixedHeight(visible_rows * row_height + 8)

        pos = anchor.mapToGlobal(QtCore.QPoint(0, anchor.height()))
        self.move(pos)

        if self.list.count():
            self.list.setCurrentRow(0)

        self.show()
        self.setFocus()

    @_check_types.do
    def _on_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        self.entrySelected.emit(item.text())
        self.close()

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key.Key_Up:
            row = max(0, self.list.currentRow() - 1)
            self.list.setCurrentRow(row)

            return

        if event.key() == QtCore.Qt.Key.Key_Down:
            row = min(self.list.count() - 1, self.list.currentRow() + 1)
            self.list.setCurrentRow(row)

            return

        if event.key() in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
            item = self.list.currentItem()
            if item is not None:
                self.entrySelected.emit(item.text())

            self.close()

            return

        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
            return

        super().keyPressEvent(event)


class SearchTextEdit(QtWidgets.QPlainTextEdit):
    """
    Single-line-constrained search box. A plain ``QLineEdit`` can't
    color a specific span of its own text (needed for red-highlighting
    a validation problem), so this is a height-locked ``QPlainTextEdit``
    using ``ExtraSelection`` for that instead -- see plan §9's widget
    note. Also owns contextual autocomplete (column labels at the start
    of a clause, that column's known values right after its `: `),
    built on the existing ``_AutoCompleter`` choice-bookkeeping class
    from ``ui/widgets/auto_complete.py`` -- that control's own
    ``setCompleter()`` convenience is QLineEdit/QComboBox-only, so the
    attach/popup wiring here is new, per the same file's own design
    notes.
    """

    searchRequested: QtCore.SignalInstance = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget,
                 schema: TableSchema, table_name: str):

        self._init = 2

        super().__init__(parent)
        self._schema = schema
        self._table_name = table_name
        self._fk_choices = _auto_complete._AutoCompleter([])  # NOQA

        self._label_choices = _auto_complete._AutoCompleter(  # NOQA
            [f'{c.label}: ' for c in schema.columns.values()])

        self._fk_values: dict[str, list[str]] = {}

        #: None = not currently stepping through history via Down;
        #: otherwise an index into get_search_history()'s own (oldest-
        #: first) list -- see _recall_history_step.
        self._history_index: int | None = None
        self._history_popup: _HistoryPopup | None = None

        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)

        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setTabChangesFocus(True)

        #: QPlainTextEdit's own sizeHint()/minimumSizeHint() are static
        #: (a generic 256x192 / 76x76 in this build, confirmed
        #: 2026-09-04) -- neither one accounts for NoWrap's horizontal
        #: scrollbar appearing/disappearing, so the box has to be told
        #: explicitly. The font's own metrics already bake in its
        #: natural top/bottom spacing, so fontMetrics().height() alone
        #: is the control's one-line height -- no separate margin/frame
        #: padding added on top. setFixedHeight() below locks the
        #: widget to exactly this, and _update_height()/eventFilter
        #: grow it by the scrollbar's own height only while that
        #: scrollbar is actually visible, so the text is never squeezed
        #: out of its own viewport by a scrollbar with nowhere to fit
        #: (confirmed reproduction of that exact failure mode
        #: 2026-09-04).
        metrics = self.fontMetrics()
        base_height = metrics.height()

        self.setFixedHeight(base_height + 14)
        self.horizontalScrollBar().installEventFilter(self)

        self._completer = QtWidgets.QCompleter(self)
        self._completer.setWidget(self)

        self._completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.PopupCompletion)

        self._completer.activated.connect(self._insert_completion)

        #: True while the same column label appears more than once in
        #: the box's own text (e.g. two separate "Gender: " clauses) --
        #: gates keyPressEvent/insertFromMimeData below so no further
        #: text can be typed or pasted in until the duplicate is
        #: resolved, rather than letting it silently pile up. Kept
        #: separate from _problem_selections (do_search's own parse-
        #: error highlighting) so the two features never clobber each
        #: other's ExtraSelections -- _apply_highlights() combines both.
        self._has_duplicate_columns = False
        self._problem_selections: list[QtWidgets.QTextEdit.ExtraSelection] = []
        self._duplicate_selections: list[QtWidgets.QTextEdit.ExtraSelection] = []
        self.textChanged.connect(self._check_duplicate_columns)  # NOQA

    @_check_types.do
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (
            obj is self.horizontalScrollBar() and
            event.type() in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.Hide)
        ):
            if self._init:
                self._init -= 1
            else:
                metrics = self.fontMetrics()
                base_height = metrics.height()

                if self.horizontalScrollBar().isVisible():
                    self.setFixedHeight(
                        base_height + self.horizontalScrollBar().size().height() + 18)
                else:
                    self.setFixedHeight(base_height + 14)

        return super().eventFilter(obj, event)

    @_check_types.do
    def set_fk_values(self, field_name: str, values: list[str]) -> None:
        self._fk_values[field_name] = list(values)

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if (
            self._completer.popup().isVisible() and
            event.key() in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return,
                            QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Tab)
        ):
            event.ignore()
            return

        completer_visible = self._completer.popup().isVisible()

        if event.key() == QtCore.Qt.Key.Key_Down and not completer_visible:
            self._recall_history_step()
            return

        if event.key() == QtCore.Qt.Key.Key_Up and not completer_visible:
            self._show_history_popup()
            return

        # Any other key breaks a Down-recall walk in progress -- the
        # next Down press starts fresh from the most recent entry.
        self._history_index = None

        if event.key() in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
            self.searchRequested.emit()
            return

        # A duplicated column label is flagged red/green by
        # _check_duplicate_columns -- block anything that would insert
        # more text (typing, paste) until it's resolved, while still
        # allowing Backspace/Delete/navigation/selection so the user
        # can actually fix it. event.text() is empty for those (and for
        # Escape/Tab, already handled above), so this only catches
        # genuine character insertion and the Paste shortcut.
        if self._has_duplicate_columns and (
            event.text() or event.matches(QtGui.QKeySequence.StandardKey.Paste)
        ):
            event.ignore()
            return

        super().keyPressEvent(event)
        self._update_completer()

    @_check_types.do
    def insertFromMimeData(self, source: QtCore.QMimeData) -> None:
        #: Covers paste/drop paths that bypass keyPressEvent entirely
        #: (context-menu Paste, drag-and-drop) -- same duplicate-column
        #: gate as above.
        if self._has_duplicate_columns:
            return

        super().insertFromMimeData(source)

    @_check_types.do
    def _set_text_and_move_to_end(self, text: str) -> None:
        self.setPlainText(text)
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    @_check_types.do
    def _recall_history_step(self) -> None:
        """
        Down: step backward through this table's search history, one
        entry per press -- first press recalls the most recent search,
        each subsequent press (without any other key breaking the walk)
        steps to the next-older one, clamped at the oldest.
        """

        entries = get_search_history(self._table_name)  # oldest-first
        if not entries:
            return

        if self._history_index is None:
            self._history_index = len(entries) - 1
        else:
            self._history_index = max(0, self._history_index - 1)

        self._set_text_and_move_to_end(entries[self._history_index])

    @_check_types.do
    def _show_history_popup(self) -> None:
        """
        Up: open the full history as a scrollable dropdown, most-
        recent-first, same width as this box.
        """

        entries = list(reversed(get_search_history(self._table_name)))
        if not entries:
            return

        if self._history_popup is None:
            self._history_popup = _HistoryPopup(self)
            self._history_popup.entrySelected.connect(self._on_history_selected)

        self._history_popup.show_for(entries, self)

    @_check_types.do
    def _on_history_selected(self, text: str) -> None:
        self._set_text_and_move_to_end(text)
        self._history_index = None
        self.setFocus()

    @_check_types.do
    def _current_fragment(self) -> tuple[int, int, str]:
        pos = self.textCursor().position()
        text = self.toPlainText()
        start = pos
        while start > 0 and text[start - 1] not in ' \t,\n':
            start -= 1

        return start, pos, text[start:pos]

    @_check_types.do
    def _update_completer(self) -> None:
        start, pos, fragment = self._current_fragment()
        if not fragment:
            self._completer.popup().hide()

            return

        text = self.toPlainText()
        prefix_text = text[:start]
        scope_match = re.search(
            r'([A-Za-z][A-Za-z0-9 ]*?):[ \t]*$', prefix_text)

        if scope_match:
            field_name = self._schema.label_lookup.get(
                scope_match.group(1).strip().lower())

            if field_name:
                choices = self._fk_values.get(field_name, [])
            else:
                choices = []
        else:
            boundary = max(prefix_text.rfind(','),
                           prefix_text.rfind('\n'),
                           prefix_text.rfind(' '))

            # column labels are only offered at the true start of a clause
            if boundary < 0 or prefix_text[:boundary + 1].strip() == '':
                choices = self._label_choices.GetChoices()
            else:
                choices = []

        if not choices:
            self._completer.popup().hide()
            return

        self._completer.setModel(QtCore.QStringListModel(choices, self._completer))
        self._completer.setCompletionPrefix(fragment)

        rect = self.cursorRect()
        rect.setWidth(self._completer.popup().sizeHintForColumn(0) + 24)
        self._completer.complete(rect)

    @_check_types.do
    def _insert_completion(self, text: str) -> None:
        start, pos, _fragment = self._current_fragment()
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(pos, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        self.setTextCursor(cursor)

    @_check_types.do
    def set_error_spans(self, spans: list[tuple[int, int]]) -> None:
        """
        Paint each [start, end) span in red -- ``ExtraSelection``
        colors text without altering it, same technique code editors
        use for spell-check underlining. Kept separate from
        _duplicate_selections (see _check_duplicate_columns) so a
        do_search() call re-evaluating parse problems never wipes out
        the live duplicate-column highlighting, or vice versa --
        _apply_highlights() below is what actually paints both.
        """

        selections = []
        doc = self.document()
        for start, end in spans:
            sel = QtWidgets.QTextEdit.ExtraSelection()
            cursor = QtGui.QTextCursor(doc)
            cursor.setPosition(max(0, start))

            cursor.setPosition(
                max(start + 1, end), QtGui.QTextCursor.MoveMode.KeepAnchor)

            sel.cursor = cursor
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor('red'))

            fmt.setUnderlineStyle(
                QtGui.QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

            fmt.setUnderlineColor(QtGui.QColor('red'))
            sel.format = fmt
            selections.append(sel)

        self._problem_selections = selections
        self._apply_highlights()

    @_check_types.do
    def _apply_highlights(self) -> None:
        self.setExtraSelections(self._problem_selections + self._duplicate_selections)

    @_check_types.do
    def _colored_span(
        self, start: int, end: int, color: QtGui.QColor
    ) -> QtWidgets.QTextEdit.ExtraSelection:
        sel = QtWidgets.QTextEdit.ExtraSelection()
        cursor = QtGui.QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QtGui.QTextCursor.MoveMode.KeepAnchor)
        sel.cursor = cursor
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(color)
        sel.format = fmt
        return sel

    @_check_types.do
    def _check_duplicate_columns(self) -> None:
        """
        Flag a column label (the "Label:" trigger itself, not the whole
        clause) that appears more than once in the box's own text --
        every occurrence after the first is painted red, the first is
        painted green, and keyPressEvent/insertFromMimeData refuse
        further text until it's resolved. Re-run on every textChanged,
        so it stays in sync with typing, undo/redo, and history-recall
        alike (filter-panel clicks route through apply_column_terms's
        own single-clause replace, which can't create this in the
        first place).
        """

        text = self.toPlainText()
        pattern = _trigger_pattern(self._schema)

        by_field: dict[str, list[tuple[int, int]]] = {}
        if pattern is not None:
            for m in pattern.finditer(text):
                field_name = self._schema.label_lookup[m.group(1).lower()]
                by_field.setdefault(field_name, []).append((m.start(), m.end()))

        selections = []
        has_duplicate = False
        for spans in by_field.values():
            if len(spans) < 2:
                continue

            has_duplicate = True
            selections.append(self._colored_span(*spans[0], QtGui.QColor('green')))
            for start, end in spans[1:]:
                selections.append(self._colored_span(start, end, QtGui.QColor('red')))

        self._has_duplicate_columns = has_duplicate
        self._duplicate_selections = selections
        self._apply_highlights()

    @_check_types.do
    def _clause_spans(self) -> list[tuple[str, int, int]]:
        """
        Every current clause's (field_name_or_DEFAULT_KEY, start, end)
        span in the box's own text -- shared by the filter-panel
        targeted-replace logic below. For a real (non-default) column,
        the span covers the WHOLE clause INCLUDING its own `Label: `
        trigger text, not just the value after it, so a caller can
        replace or remove one clause as a single atomic unit without
        needing to separately track/preserve the trigger prefix.
        """

        text = self.toPlainText()
        pattern = _trigger_pattern(self._schema)
        if pattern is not None:
            triggers = list(pattern.finditer(text))
        else:
            triggers = []

        spans = []
        prev_start = 0
        prev_field = DEFAULT_KEY

        for m in triggers:
            spans.append((prev_field, prev_start, m.start()))
            prev_field = self._schema.label_lookup[m.group(1).lower()]
            prev_start = m.start()

        spans.append((prev_field, prev_start, len(text)))

        return spans

    @_check_types.do
    def apply_column_terms(self, column: str,
                           groups: list[list[SearchTerm]]) -> None:
        """
        Replace *column*'s ENTIRE clause in the search text with
        *groups* (its complete desired state -- e.g. one group per
        currently-checked FK/enum value, or the single AND-group a Range
        panel's Min/Max currently represents), never merged/appended on
        top of whatever was there. A filter-assist panel always knows
        its own full current state after any click/Apply, so it always
        sends the complete picture rather than one incremental piece --
        merging there could only ever grow a clause (unchecking an item,
        or re-Applying a Range panel with new bounds, could never
        actually remove/replace the old text).

        Rewrites ONLY that column's clause span via a targeted cursor
        edit -- not a full-text ``setPlainText()`` -- so
        ``QPlainTextEdit``'s native undo stack gets one discrete step
        per call, same as the user selecting that span and typing over
        it themselves (plan §8). ``_clause_spans()`` hands back the
        WHOLE clause (trigger text included) specifically so this can
        treat replace/remove/append-new as one atomic text-splice each.
        """

        text = self.toPlainText()
        result = parse(text, self._schema)
        result.params.set_column(column, groups)

        col_search = result.params.columns.get(column)
        if col_search is not None:
            rendered_groups = ','.join(
                _render_group(g) for g in col_search.groups if g)

        else:
            rendered_groups = ''

        if column == DEFAULT_KEY:
            new_clause_text = rendered_groups
        elif rendered_groups:
            label = self._schema.columns[column].label
            new_clause_text = f'{label}: {rendered_groups}'
        else:
            new_clause_text = ''

        span = None
        for field_name, start, end in self._clause_spans():
            if field_name == column:
                span = (start, end)
                break

        cursor = self.textCursor()
        if span is not None:
            cursor.setPosition(span[0])
            cursor.setPosition(span[1], QtGui.QTextCursor.MoveMode.KeepAnchor)

            if new_clause_text:
                cursor.insertText(new_clause_text.strip() + ' ')
            else:
                cursor.insertText('')

        elif new_clause_text:
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

            if text and not text[-1].isspace():
                cursor.insertText(' ')

            cursor.insertText(new_clause_text.strip() + ' ')

        self.setTextCursor(cursor)
        self.setFocus()


# =====================================================================
# 4b. Filter-assist panels -- write INTO the search text, hold no state
# =====================================================================

PANEL_W = 190
PANEL_H = 220

#: Extra height the filter STRIP's own QScrollArea needs beyond a
#: single panel's minimum height -- its frame border plus the
#: horizontal scrollbar (ScrollBarAsNeeded, and it typically IS shown
#: since panels run side by side) both eat into the vertical viewport,
#: on top of PANEL_H. Deliberately a SEPARATE constant from PANEL_H,
#: not derived from it -- both filter_scroll's fixed height and each
#: panel's own minimum height used to come from PANEL_H together, so
#: raising PANEL_H moved the ceiling and the content needing to fit
#: under it by the same amount and never actually closed the gap
#: (confirmed 2026-09-03 -- changing PANEL_H alone had zero visible
#: effect on where the Reset button got clipped). This is the number
#: that actually controls that slack.
_FILTER_SCROLL_EXTRA = 40


class _FilterPanelBase(QtWidgets.QWidget):
    """
    A panel is purely an input ASSIST for the search text (plan §8)
    -- it has no independent filter state and no SQL path of its own.
    Clicking edits ``search_edit``'s text via
    :meth:`SearchTextEdit.apply_column_terms`; the panel's own displayed
    checked state is always re-derived from the CURRENT parsed text
    (:meth:`sync_from_text`), never held independently.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget,
                 search_edit: SearchTextEdit, col: ColumnInfo):

        super().__init__(parent)
        self.search_edit = search_edit
        self.col = col
        self.setMinimumSize(PANEL_W, PANEL_H)
        self.setMaximumWidth(PANEL_W)

    @_check_types.do
    def sync_from_text(self) -> None:
        raise NotImplementedError

    @_check_types.do
    def clear(self) -> None:
        raise NotImplementedError


class FKFilterPanel(_FilterPanelBase):
    """
    Checklist for an FK/enum column's known display values.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget,
                 search_edit: SearchTextEdit,
                 col: ColumnInfo, values: list[str]):

        super().__init__(parent, search_edit, col)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel(f'<b>{col.label}</b>', self))

        self.list = QtWidgets.QListWidget(self)

        for v in values:
            item = QtWidgets.QListWidgetItem(str(v))
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.list.addItem(item)

        lay.addWidget(self.list, 1)

        reset = QtWidgets.QPushButton('Reset', self)
        reset.clicked.connect(self.clear)
        lay.addWidget(reset)

        self.list.itemClicked.connect(self._on_click)

    @_check_types.do
    def _on_click(self, _: QtWidgets.QListWidgetItem) -> None:
        """
        Send the checklist's COMPLETE current selection every click --
        not just the one item that was toggled -- so the resulting
        clause always reflects exactly what's checked. This is what
        lets ``apply_column_terms`` correctly drop a value's group when
        it's unchecked, since it's told the whole desired state instead
        of one more piece to merge in (this used to only ever be able
        to append, never remove -- a confirmed real bug).
        """

        groups = []
        for i in range(self.list.count()):
            it = self.list.item(i)

            if it.checkState() == QtCore.Qt.CheckState.Checked:
                groups.append([SearchTerm(phrase=it.text())])

        self.search_edit.apply_column_terms(self.col.field_name, groups)

    @_check_types.do
    def sync_from_text(self) -> None:
        text = self.search_edit.toPlainText()
        result = parse(text, self.search_edit._schema)  # NOQA
        col_search = result.params.columns.get(self.col.field_name)
        checked_values = set()

        if col_search is not None:
            for group in col_search.groups:
                for term in group:
                    if term.phrase is not None:
                        checked_values.add(term.phrase.lower())
                    elif term.word is not None:
                        checked_values.add(term.word.lower())
                    elif term.value is not None:
                        checked_values.add(term.value.lower())

        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.text().lower() in checked_values:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
            else:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)

        self.list.blockSignals(False)

    @_check_types.do
    def clear(self) -> None:
        self.search_edit.apply_column_terms(self.col.field_name, [])
        self.sync_from_text()


class EnumFilterPanel(FKFilterPanel):
    """
    Same as :class:`FKFilterPanel`, for a plain integer/enum column
    (no ref table) -- kept as a thin alias since the display-value
    checklist mechanics are identical.
    """


class RangeFilterPanel(_FilterPanelBase):
    """
    Min/max spinboxes for a numeric column, rendered into the search
    text as two AND'd `>=`/`<=` operator terms (plan §2's range form).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget,
                 search_edit: SearchTextEdit, col: ColumnInfo,
                 lo: float, hi: float):

        super().__init__(parent, search_edit, col)
        self._lo_default, self._hi_default = lo, hi

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel(f'<b>{col.label}</b>', self))

        form = QtWidgets.QFormLayout()
        self.min_ctrl = QtWidgets.QDoubleSpinBox(self)
        self.max_ctrl = QtWidgets.QDoubleSpinBox(self)
        for ctrl in (self.min_ctrl, self.max_ctrl):
            ctrl.setRange(-1.0e15, 1.0e15)
            ctrl.setDecimals(4)

        self.min_ctrl.setValue(lo)
        self.max_ctrl.setValue(hi)

        form.addRow('Min:', self.min_ctrl)
        form.addRow('Max:', self.max_ctrl)
        lay.addLayout(form)

        apply_btn = QtWidgets.QPushButton('Apply', self)
        apply_btn.clicked.connect(self._on_apply)
        lay.addWidget(apply_btn)

        reset = QtWidgets.QPushButton('Reset', self)
        reset.clicked.connect(self.clear)
        lay.addWidget(reset)
        lay.addStretch()

    @_check_types.do
    def _on_apply(self) -> None:
        lo, hi = self.min_ctrl.value(), self.max_ctrl.value()
        terms = []

        if lo > self._lo_default:
            terms.append(SearchTerm(operator='>=', value=str(lo)))

        if hi < self._hi_default:
            terms.append(SearchTerm(operator='<=', value=str(hi)))

        if terms:
            groups = [terms]
        else:
            groups = []

        self.search_edit.apply_column_terms(self.col.field_name, groups)

    @_check_types.do
    def sync_from_text(self) -> None:
        # numeric spinboxes aren't re-derived from text; Apply is one-directional
        pass

    @_check_types.do
    def clear(self) -> None:
        self.min_ctrl.setValue(self._lo_default)
        self.max_ctrl.setValue(self._hi_default)
        self.search_edit.apply_column_terms(self.col.field_name, [])


# =====================================================================
# 4c. Results view -- reverted to the SAME EditorList-based page class
# today's part_search.py already uses (page_class, e.g.
# ui.editor_db.terminal.TerminalsPage), not a purpose-built model. It
# already owns its own windowed row cache/pagination, its own
# `set_filter(where_clause, params)` (synchronous from the caller's
# side), `.selected`/`get_obj_id()` for reading back the chosen row's
# id, and `itemSelected`/`itemUnselected` signals -- SearchDialog just
# feeds it the WHERE clause this module's own to_sql() built, exactly
# the same shape today's part_search.py already hands it, just sourced
# from the parsed search text instead of a hand-assembled predicate.
#
# Because set_filter() is synchronous, there's no async query phase
# left for a "Searching..." indicator to usefully cover once the
# results panel itself is EditorList -- see SearchDialog.do_search()
# for what this simplifies to. (The batched filter-assist-panel
# population in section 5/6 is unrelated and stays async via
# QueryScope -- that's a different query than the results themselves.)
# =====================================================================


class HelpDialog(QtWidgets.QDialog):
    """
    Plain-language "How to search" reference (plan §7) -- non-modal,
    parented to (and explicitly closed alongside) the search dialog
    that opened it. Fixed section order on every table, real column
    names substituted in where a symbol applies, a red "not usable
    here" note in that same position otherwise -- see the module design
    notes for the full reasoning (people remember WHERE something was
    more reliably than what it said).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, schema: TableSchema):
        super().__init__(parent)
        self.setWindowTitle('How to Search')
        self.setModal(False)
        self.resize(560, 640)

        view = QtWidgets.QTextBrowser(self)
        view.setHtml(_build_help_html(schema))

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(view)


@_check_types.do
def _example_column(schema: TableSchema, kind: str) -> ColumnInfo | None:
    for col in schema.columns.values():
        if col.kind == kind:
            return col


@_check_types.do
def _build_help_html(schema: TableSchema) -> str:
    text_col = (_example_column(schema, 'text') or
                _example_column(schema, 'fk'))

    fk_col = _example_column(schema, 'fk')
    numeric_col = _example_column(schema, 'numeric')

    eq_col = fk_col or text_col or numeric_col
    like_col = text_col or fk_col
    table_label = schema.table.replace('_', ' ').title()

    parts = ['<h2>How to Search</h2>',
             '<p>Just start typing, then press Search (or Enter) -- '
             'here is how to search more precisely when you need to.</p>',
             '<h3>Plain search</h3>']

    if text_col:
        parts.append(
            f'<p>Type any word or number and it is looked for in every '
            f'searchable column.<br>Example: <code>bracket</code> finds '
            f'anything mentioning &quot;bracket&quot; anywhere.</p>')
    else:
        parts.append('<p style="color:red">Not usable here -- '
                     f'{table_label} has no plain-text columns to search.</p>')

    parts.append('<h3>Search one specific column</h3>')
    example_col = text_col or fk_col or numeric_col
    if example_col:
        parts.append(
            f'<p>Type the column\'s name, then a colon, then a space, then '
            f'what you\'re looking for.<br>Example: '
            f'<code>{example_col.label.lower()}: bracket</code> only checks '
            f'that one column.</p>')

    parts.append('<h3>Exact phrases</h3>')
    parts.append(
        '<p>Put quotes around a phrase to require those exact words, in that '
        'exact order.<br>Example: <code>"right angle bracket"</code> only '
        'finds that exact phrase. Without quotes, the words can appear '
        'anywhere, in any order.</p>')

    parts.append('<h3>Searching for more than one thing at once</h3>')
    parts.append(
        '<p>Separate items with a comma to find rows matching ANY of '
        'them.<br>Example: <code>part number: "AB1234","AB5678"</code> '
        'finds either part number.</p>')

    parts.append('<h3>Fine-tuning with symbols</h3>')
    parts.append(
        '<p>For number columns, or columns with a fixed set of choices, put '
        'one of these symbols right before your answer (no space):</p><ul>')

    if eq_col:
        parts.append(
            f'<li><code>==</code> must match exactly -- Example: '
            f'<code>{eq_col.label.lower()}: =={_placeholder(eq_col)}</code></li>')

        parts.append(
            f'<li><code>!=</code> must NOT match -- Example: '
            f'<code>{eq_col.label.lower()}: !={_placeholder(eq_col)}</code></li>')
    else:
        parts.append(f'<li><code>==</code> / <code>!=</code> must (not) match exactly.'
                     f'<br><span style="color:red">Not usable here -- {table_label} '
                     f'has no columns to try this on.</span></li>')

    if like_col:
        parts.append(
            f'<li><code>~=</code> just needs to show up somewhere (a partial '
            f'match) -- Example: <code>{like_col.label.lower()}: ~=bracket</code></li>')
    else:
        parts.append(f'<li><code>~=</code> partial match.<br>'
                     f'<span style="color:red">Not usable here -- {table_label} '
                     f'has no text columns.</span></li>')

    if numeric_col:
        parts.append(
            f'<li><code>&gt;=</code> / <code>&lt;=</code> / <code>&gt;</code> / '
            f'<code>&lt;</code> at least / at most / more than / less than -- '
            f'Example: <code>{numeric_col.label.lower()}: &gt;=2.8</code></li>')

        parts.append(
            f'<li>Combine two with a space to search a range -- Example: '
            f'<code>{numeric_col.label.lower()}: &gt;=2 &lt;=3</code></li>')
    else:
        parts.append(f'<li><code>&gt;=</code> / <code>&lt;=</code> / <code>&gt;</code> / '
                     f'<code>&lt;</code> number comparisons.<br>'
                     f'<span style="color:red">Not usable here -- {table_label} '
                     f'has no number columns to compare this way.</span></li>')

    parts.append('</ul>')

    parts.append('<h3>Don\'t want to remember any of this?</h3>')

    parts.append('<p>Click the boxes on the left instead -- the right search text '
                 'gets typed in for you automatically.</p>')

    return ''.join(parts)


@_check_types.do
def _placeholder(col: ColumnInfo) -> str:
    if col.kind == 'fk':
        return 'Male'

    return 'example'


# =====================================================================
# 5. SearchDialog
# =====================================================================

class SearchDialog(_dialog_base.BaseDialog):
    """
    The rewrite of ``part_search.py``'s ``SearchDialog`` (plan §12-14)
    -- same class name, for a clean swap-over once callers are migrated
    (none are, in this pass; ``part_search.py`` is untouched and remains
    the dialog actually in use).
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame",
                 page_class: type["_editor_db_base.EditorList"],
                 table: "_glb_bases.TableBase", title: str,
                 initial_params: SearchParameters | None = None):

        super().__init__(parent, title=title, size=(1180, 780))

        self.table = table
        self.page_class = page_class
        self.mainframe = parent
        self.conn = parent.db_connector
        self._table_name = page_class.__table_name__
        self.schema = build_schema(
            self.conn, self._table_name, page_class.column_mapping)

        # field_name -> position in schema.columns (== column_mapping's
        # own declared order) -- filter-assist panels arrive out of
        # this order (numeric stats are one batched query, each FK
        # column is its own independent async query, see
        # _populate_filters/_add_filter_panel) and must be placed back
        # into it rather than left in arrival order.
        self._column_rank = {
            fn: i for i, fn in enumerate(self.schema.columns.keys())}

        self._help_window: HelpDialog | None = None
        self._filter_panels: list[_FilterPanelBase] = []

        self._scope = QueryScope(self.conn.db_name, self)

        self._build_ui()

        if initial_params is not None:
            self.search_edit.setPlainText(initial_params.to_text(self.schema))

        QtCore.QTimer.singleShot(0, self._populate_filters)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    @_check_types.do
    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self.panel)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel('Search:', self.panel))

        self.search_edit = SearchTextEdit(
            self.panel, self.schema, self._table_name)

        self.search_edit.searchRequested.connect(self.do_search)
        top.addWidget(self.search_edit, 1)

        search_btn = QtWidgets.QPushButton('Search', self.panel)
        search_btn.setStyleSheet('padding-left: 12px; padding-right: 12px;')
        search_btn.clicked.connect(self.do_search)
        top.addWidget(search_btn)

        help_btn = QtWidgets.QPushButton('?', self.panel)
        help_btn.setFixedWidth(28)
        help_btn.setToolTip('How to search')
        help_btn.clicked.connect(self._show_help)
        top.addWidget(help_btn)

        outer.addLayout(top)

        self.filter_scroll = QtWidgets.QScrollArea(self.panel)
        self.filter_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.filter_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setFixedHeight(PANEL_H + _FILTER_SCROLL_EXTRA)

        self._filter_container = QtWidgets.QWidget(self.panel)
        self.filter_sizer = QtWidgets.QHBoxLayout(self._filter_container)
        self.filter_sizer.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.filter_scroll.setWidget(self._filter_container)
        outer.addWidget(self.filter_scroll)

        self.status = QtWidgets.QLabel('', self.panel)
        outer.addWidget(self.status)

        # Same page-class-driven results widget today's part_search.py
        # already uses (an EditorList subclass -- e.g. TerminalsPage) --
        # it owns its own windowed row cache/pagination and its own
        # `.selected`/`get_obj_id()`/`itemSelected`/`itemUnselected`;
        # this dialog just feeds it a WHERE clause (see do_search()).
        self.results = self.page_class(
            self.panel, self.mainframe, '', self.table)

        # The page class's activation handler normally opens the
        # editor's own edit dialog on double-click/Enter -- replace
        # that with search-mode accept, same as today's part_search.py.
        try:
            self.results.activated.disconnect()
        except Exception:  # NOQA
            pass

        self.results.activated.connect(self._on_row_activated)
        outer.addWidget(self.results, 1)

        ok_btn = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)

        ok_btn.setEnabled(False)
        self.results.itemSelected.connect(lambda _row: ok_btn.setEnabled(True))
        self.results.itemUnselected.connect(lambda: ok_btn.setEnabled(False))

    @_check_types.do
    def _on_row_activated(self, index: QtCore.QModelIndex) -> None:
        self.results.selected = index.row()

        if self.GetValue() is not None:
            self.accept()

    # ------------------------------------------------------------------
    # Filter-assist panel population (batched, per plan §5)
    # ------------------------------------------------------------------

    @_check_types.do
    def _populate_filters(self) -> None:
        numeric_cols = [
            c for c in self.schema.columns.values() if c.kind == 'numeric']

        fk_cols = [c for c in self.schema.columns.values() if c.kind == 'fk']

        if numeric_cols:
            select = ', '.join(
                f'MIN(t.{c.field_name}), MAX(t.{c.field_name})' for c in numeric_cols)

            sql = f'SELECT {select} FROM {self._table_name} t;'

            @_check_types.do
            def _on_numeric(rows: list) -> None:
                if not rows:
                    return

                row = rows[0]
                for i, column in enumerate(numeric_cols):
                    lo, hi = row[i * 2], row[i * 2 + 1]
                    if lo is None or hi is None or lo == hi:
                        continue

                    panel = RangeFilterPanel(
                        self._filter_container, self.search_edit, column, lo, hi)

                    self._add_filter_panel(panel, column)

            self._scope.run(sql, [], _on_numeric)

        for col in fk_cols:
            sql = (f'SELECT DISTINCT r.{col.ref_field} FROM {self._table_name} t '
                   f'JOIN {col.ref_table} r ON t.{col.field_name} = r.id '
                   f'WHERE r.{col.ref_field} IS NOT NULL '
                   f'ORDER BY r.{col.ref_field} COLLATE NOCASE;')

            @_check_types.do
            def _on_fk(rows: list, column: ColumnInfo = col) -> None:
                values = [r[0] for r in rows]
                if not values:
                    return

                panel = FKFilterPanel(
                    self._filter_container, self.search_edit, column, values)

                self._add_filter_panel(panel, column)
                self.search_edit.set_fk_values(column.field_name, values)
                panel.sync_from_text()

            self._scope.run(sql, [], _on_fk)

    @_check_types.do
    def _add_filter_panel(self, panel: _FilterPanelBase, col: ColumnInfo) -> None:
        """
        Insert *panel* into the filter strip at the position matching
        *col*'s rank in ``schema.columns`` (== ``column_mapping``'s own
        declared order) -- NOT arrival order. Numeric stats arrive as
        one batched query while each FK column is its own independent
        async query (see :meth:`_populate_filters`), so a column later
        in ``column_mapping`` can easily get its data back before one
        earlier in it -- appending in arrival order would silently
        scramble the strip relative to the order the user actually
        sees fields listed in everywhere else (search-syntax help,
        typed column labels, etc). ``self._filter_panels`` is kept
        sorted by rank at all times, so the insertion point is just the
        first existing panel whose rank is not lower than the new one's.
        """

        rank = self._column_rank[col.field_name]

        insert_at = len(self._filter_panels)
        for i, existing in enumerate(self._filter_panels):
            if self._column_rank[existing.col.field_name] >= rank:
                insert_at = i
                break

        self._filter_panels.insert(insert_at, panel)
        self.filter_sizer.insertWidget(insert_at, panel)

    # ------------------------------------------------------------------
    # Explicit search action (plan §9)
    # ------------------------------------------------------------------

    @_check_types.do
    def do_search(self) -> None:
        text = self.search_edit.toPlainText()
        result = parse(text, self.schema)

        if result.problems:
            self.search_edit.set_error_spans(
                [(p.start, p.end) for p in result.problems])

            self.status.setStyleSheet('color: red;')
            self.status.setText(result.problems[0].message)

            return

        self.search_edit.set_error_spans([])
        self.status.setStyleSheet('')

        # set_filter() is synchronous from the caller's side (the page
        # class runs/counts the query itself) -- same as today's
        # part_search.py's own _push_filter_to_page, just fed a WHERE
        # clause built from the parsed search text instead of a hand-
        # assembled predicate.
        where_sql, params = to_sql(result.params, self.schema)
        self.results.set_filter(where_sql, params)
        total = self.results._row_count  # NOQA

        if total == 0:
            self.status.setText(self._zero_result_message(result.params))
        else:
            if total != 1:
                plural = 's'
            else:
                plural = ''

            self.status.setText(f'{total:,} result{plural}')

        record_search(self._table_name, text)

    @_check_types.do
    def _zero_result_message(self, params: SearchParameters) -> str:
        """
        Bounded zero-result diagnostic (plan §9): try dropping each
        column one at a time, suggest whichever single removal returns
        the FEWEST results.
        """

        columns = [c for c in params.columns.keys()]
        if len(columns) <= 1:
            return 'No matches.'

        best_column = None
        best_count = None

        for col_name in columns:
            trimmed = without_column(params, col_name)
            where_sql, sql_params = to_sql(trimmed, self.schema)
            if where_sql:
                where_clause = f'WHERE {where_sql}'
            else:
                where_clause = ''

            sql = f'SELECT COUNT(*) FROM {self._table_name} t {where_clause};'

            try:
                self.conn.execute(sql, sql_params)
                count = self.conn.fetchall()[0][0]
            except Exception:  # NOQA
                continue

            if count > 0 and (best_count is None or count < best_count):
                best_count, best_column = count, col_name

        if best_column is None:
            return 'No matches.'

        if best_column in self.schema.columns:
            label = self.schema.columns[best_column].label
        else:
            label = 'that part'

        return (f'No matches. Try removing "{label}" '
                f'from the search -- that alone would find {best_count}.')

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    @_check_types.do
    def _show_help(self) -> None:
        if self._help_window is None:
            self._help_window = HelpDialog(self, self.schema)

        self._help_window.show()
        self._help_window.raise_()

    # ------------------------------------------------------------------
    # Lifecycle / accessors
    # ------------------------------------------------------------------

    @_check_types.do
    def done(self, result: int) -> None:
        if self._help_window is not None:
            self._help_window.close()

        self._scope.shutdown()

        super().done(result)

    @_check_types.do
    def GetValue(self) -> int | None:
        sel = getattr(self.results, 'selected', None)
        if sel is None:
            return None

        try:
            # get_obj_id's query matches against SQL's 1-indexed RowNum;
            # self.results.selected is Qt's 0-indexed row.
            return self.results.get_obj_id(sel + 1)
        except Exception:  # NOQA
            return None
