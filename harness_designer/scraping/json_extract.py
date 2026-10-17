# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Turns point-and-click selections in a sample JSON value into working
Python extraction code.

A "click" on a leaf value in the JSON tree is just the path of keys/
indices that reach it. Clicking several fields inside one array element
(e.g. ``items[0].price`` and ``items[0].part_number``) is recognized as
"this is a list of records" from the shared array ancestor, and generates
one loop over the array rather than one hardcoded line per index -- the
whole point of clicking more than one field is to describe a repeating
record shape, not to grab a handful of fixed positions.

Clicking a single field of an array element gives the one hardcoded line
by default; ``every_item=True`` asks for that field from every element
instead.

For anything point-and-click can't express well (field sometimes missing,
nested differently per record, needs light transformation), ``describe``
hands the sample and a plain-language request to Claude instead.
"""

import json
import keyword
import re

from . import snippets as _snippets
from .. import check_types as _check_types
from .. import claude as _claude

PathStep = str | int
Path = tuple[PathStep, ...]


@_check_types.do
def format_path_access(path: Path, root_name: str) -> str:
    """Render *path* as a Python subscript expression off *root_name*.

    :Example: ``format_path_access(('items', 0, 'price'), 'data')`` ->
        ``"data['items'][0]['price']"``
    """
    expr = root_name
    for step in path:
        if isinstance(step, int):
            expr += f'[{step}]'
        else:
            expr += f'[{step!r}]'
    return expr


@_check_types.do
def suggest_name(path: Path) -> str:
    """A variable name for the value at *path*: its last key, made into a
    valid Python identifier (``unit-price`` -> ``unit_price``). A path that
    ends in an index is named after the key above it (``tags[2]`` ->
    ``tags_item``)."""
    suffix = ''
    steps = list(path)
    while steps and isinstance(steps[-1], int):
        steps.pop()
        suffix = '_item'

    if not steps:
        return 'value'

    name = re.sub(r'\W', '_', str(steps[-1])).strip('_').lower()
    if not name:
        name = 'value'

    if name[0].isdigit():
        name = '_' + name

    name += suffix
    if keyword.iskeyword(name):
        name += '_'

    return name


@_check_types.do
def generate_extraction_code(paths_with_names: list[tuple[Path, str]], root_name: str = 'data',
                             every_item: bool = False) -> str:
    """Python code extracting each named path from *root_name*.

    Paths that share a common array ancestor are pulled out inside one
    ``for`` loop over that array instead of as separate indexed lines.
    With *every_item* the values are taken from every element of the array
    that holds them, even when only one path was given.

    :raises ValueError: *every_item* was asked for but the paths do not all
        sit inside the same array.
    """
    if not paths_with_names:
        return ''

    paths = [path for path, _name in paths_with_names]

    if every_item:
        array_path = _shared_array(paths)
        if array_path is None:
            raise ValueError('"every item" needs all selected values to sit inside the same array')

        if len(paths_with_names) == 1:
            return _generate_comprehension(paths_with_names[0], root_name, array_path)

        return _generate_loop(paths_with_names, root_name, array_path)

    array_path = _common_array_ancestor(paths)
    if array_path is None:
        return _generate_flat_lines(paths_with_names, root_name)

    return _generate_loop(paths_with_names, root_name, array_path)


@_check_types.do
def has_array_step(path: Path) -> bool:
    """True when *path* goes through an array element, i.e. an "every
    item" extraction makes sense for it."""
    return any(isinstance(step, int) for step in path)


@_check_types.do
def describe(json_sample: object, description: str, root_name: str = 'data',
             client: _claude.ClaudeClient | None = None) -> str:
    """Ask Claude to write extraction code for *description* against
    *json_sample* (bound to *root_name* at runtime) -- for shapes a
    handful of clicks can't express cleanly (optional fields, light
    transforms, records nested differently from one another).

    :param client: The client to use; default is a new one on the
        application's settings and the user's stored key.
    :raises ClaudeError: The call failed (no key, rate limit, ...).
    """
    system = (
        'You write minimal, correct Python code that extracts specific '
        'fields from an already-parsed JSON value. Respond with ONLY the '
        'Python code itself -- no explanation, no markdown code fences. '
        f'The sample is already parsed and bound to the variable `{root_name}`. '
        'If the sample is a list of similar records, write a loop that '
        'builds a list of dicts, one per record, named `results`.'
    )
    sample_text = json.dumps(json_sample, indent=2, default=str)[:4000]
    prompt = f'Sample JSON (bound to `{root_name}`):\n{sample_text}\n\nExtract: {description}'

    if client is None:
        client = _claude.ClaudeClient()

    reply = client.ask(prompt, system=system)
    return _strip_code_fence(reply.text)


@_check_types.do
def snippet_for(paths_with_names: list[tuple[Path, str]], root_name: str = 'data',
                every_item: bool = False) -> _snippets.Snippet:
    """:func:`generate_extraction_code` as a :class:`~.snippets.Snippet`."""
    code = generate_extraction_code(paths_with_names, root_name, every_item)
    count = len(paths_with_names)

    if every_item:
        description = f'Extract {count} field(s) from every item'
    else:
        description = f'Extract {count} value(s) from the JSON'

    return _snippets.Snippet(code=code, description=description, result_name=paths_with_names[0][1])


@_check_types.do
def _common_array_ancestor(paths: list[Path]) -> Path | None:
    """The path prefix, shared by every path in *paths*, that ends just
    before an integer (array index) step -- the array all of them live
    inside, if they share one at all.

    Two paths that differ only in WHICH index they use at some position
    (``items[0].price`` vs. ``items[1].price``) still share that array --
    an index mismatch is itself array-boundary evidence, not just a plain
    divergence, so the forward scan has to count one more step past it
    before stopping (the backward walk below needs that index step
    present to recognize it).
    """
    if len(paths) < 2:
        return None

    shortest_length = min(len(path) for path in paths)
    common_length = 0
    for position in range(shortest_length):
        step_values = [path[position] for path in paths]
        if len(set(step_values)) == 1:
            common_length += 1
            continue
        if all(isinstance(value, int) for value in step_values):
            common_length += 1
        break

    for cut in range(common_length, 0, -1):
        if isinstance(paths[0][cut - 1], int):
            return paths[0][:cut - 1]

    return None


@_check_types.do
def _shared_array(paths: list[Path]) -> Path | None:
    """The array holding every path, taking the innermost array step of
    each; ``None`` when they are not all in the same one."""
    prefixes: set[Path] = set()
    for path in paths:
        cut = -1
        for position, step in enumerate(path):
            if isinstance(step, int):
                cut = position

        if cut == -1:
            return None

        prefixes.add(path[:cut])

    if len(prefixes) != 1:
        return None

    return prefixes.pop()


@_check_types.do
def _generate_flat_lines(paths_with_names: list[tuple[Path, str]], root_name: str) -> str:
    lines = [f'{name} = {format_path_access(path, root_name)}' for path, name in paths_with_names]
    return '\n'.join(lines)


@_check_types.do
def _generate_loop(paths_with_names: list[tuple[Path, str]], root_name: str, array_path: Path) -> str:
    array_expr = format_path_access(array_path, root_name)
    array_depth = len(array_path) + 1  # +1 to also skip the index step itself

    lines = ['results = []', f'for item in {array_expr}:']
    field_names = [name for _path, name in paths_with_names]
    for path, name in paths_with_names:
        relative_path = path[array_depth:]
        access = format_path_access(relative_path, 'item')
        lines.append(f'    {name} = {access}')

    assignments = ', '.join(f'{name}={name}' for name in field_names)
    lines.append(f'    results.append(dict({assignments}))')
    return '\n'.join(lines)


@_check_types.do
def _generate_comprehension(path_with_name: tuple[Path, str], root_name: str, array_path: Path) -> str:
    path, name = path_with_name
    array_expr = format_path_access(array_path, root_name)
    access = format_path_access(path[len(array_path) + 1:], 'item')
    return f'{name}_values = [{access} for item in {array_expr}]'


@_check_types.do
def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith('```'):
        return stripped

    lines = stripped.split('\n')
    lines = lines[1:]  # drop the opening ``` or ```python line
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines).strip()
