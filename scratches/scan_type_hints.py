"""
Static scan of harness_designer for two classes of type-hint problems:

1. Unnecessarily string-quoted type hints (whole or nested) -- quoting a
   builtin/typing construct, or quoting a name that is already available
   unquoted at the point of use, breaks Cython compilation and is never
   required. Quoting is only legitimate when the quoted name is:
     - imported only inside an `if TYPE_CHECKING:` block, or
     - imported only inside a function body (lazy/local import), or
     - a name defined later in the same module (true forward reference), or
     - part of a genuine import cycle: the imported module is only fully
       importable because *this* module hasn't finished loading yet, which
       can only happen between two modules inside this package that both
       (transitively) import each other.

   A name imported from outside the package (numpy, wx, OpenGL, stdlib,
   etc.) can never need quoting for circular-import reasons -- an external
   library cannot import this package back. To tell a real intra-package
   import cycle apart from an ordinary direct import, this script builds
   the whole-package module import graph and computes strongly connected
   components (Kosaraju's algorithm): two modules only have a genuine
   circular-import risk between them if they land in the same component.

2. Missing type hints on function parameters and return values, including
   staticmethod/classmethod/property getter&setter. `self`/`cls` as the
   first parameter of an instance/class method are intentionally excluded,
   as is `__init__` entirely (never returns a value and its param hints
   aren't tracked by this scan).

   Among functions missing a return annotation, those that never actually
   return a value (no `return` statement at all, or only bare `return` /
   `return None`, and not a generator) are additionally called out as
   `-> None` candidates -- the annotation to add is unambiguous.

Before doing anything else, this script requires a clean git working tree
(`git status --porcelain` empty) in the repo containing root_dir, and exits
with an error otherwise. This is a read-only scan today, but the same gate
is meant to stay in place if/when the script grows the ability to apply
fixes -- a clean starting tree guarantees any edits it makes land as their
own isolated, easily-revertable commit rather than getting tangled up with
unrelated in-progress work.

Usage: python scan_type_hints.py
Always scans the harness_designer package (hardwired -- no arguments taken).
Writes three CSV reports next to this script:
    quoting_violations.csv
    missing_type_hints.csv       (has a likely_none_return/none_reason column)
    implicit_none_returns.csv    (just the -> None candidates, for convenience)
and prints a summary to stdout.
"""
import ast
import csv
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_PARENT = os.path.dirname(SCRIPT_DIR)  # repo root (this script lives in <repo>/scratches/)
ROOT = os.path.join(ROOT_PARENT, "harness_designer")
OUT_DIR = SCRIPT_DIR
PACKAGE_NAME = "harness_designer"


# Only the harness_designer package must be clean -- the repo also carries
# a lot of persistent untracked scratch/output content elsewhere (bosch/,
# te/, yazaki/, etc.) that has nothing to do with this scan and shouldn't
# block it. This is the only directory the scan reads or (eventually)
# would write fixes into, so it's the only one that needs to be clean.
GIT_CHECK_PATH = "harness_designer"


def require_clean_git_tree():
    """Refuse to run at all unless every .py file under GIT_CHECK_PATH is
    fully clean in git -- no staged/unstaged modifications and no untracked
    .py files. Non-Python files (data, generated artifacts, etc.) are
    ignored, since this scan only ever reads/reports on .py source. This
    forces a commit before every run, so anything the script does (today:
    writing reports; later: potentially applying fixes) starts from a
    known-good restore point and any edits it makes can land as their own
    commit."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", GIT_CHECK_PATH],
            cwd=ROOT_PARENT,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print("ERROR: git executable not found -- can't verify a clean working "
              "tree. Refusing to run.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: `git status` failed (not a git repo at {ROOT_PARENT}?): "
              f"{e.stderr.strip() if e.stderr else e}")
        sys.exit(1)

    def status_line_path(line):
        # porcelain v1: "XY path" or "XY old -> new" for renames; a quoted
        # path means git escaped special/non-ASCII characters in it.
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        return path

    all_lines = [line for line in result.stdout.splitlines() if line.strip()]
    dirty = [line for line in all_lines if status_line_path(line).endswith(".py")]
    if dirty:
        print(f"ERROR: {GIT_CHECK_PATH}/ not clean under {ROOT_PARENT} -- commit "
              f"or stash everything in it first, then re-run.\n"
              f"{len(dirty)} uncommitted change(s):")
        for line in dirty:
            print(f"  {line}")
        sys.exit(1)

    print(f"Git status clean for {GIT_CHECK_PATH}/ -- proceeding.")


BUILTIN_TYPE_NAMES = {
    "int", "float", "str", "bool", "bytes", "bytearray", "complex",
    "list", "dict", "set", "frozenset", "tuple", "type", "object",
    "None", "Any", "Optional", "Union", "Callable", "Tuple", "List",
    "Dict", "Set", "FrozenSet", "Iterable", "Iterator", "Sequence",
    "Mapping", "MutableMapping", "MutableSequence", "ClassVar", "Final",
    "Literal", "TypeVar", "Generic", "NoReturn", "ellipsis", "Type",
    "Awaitable", "Coroutine", "Generator", "AsyncGenerator", "AsyncIterator",
    "AsyncIterable", "Deque", "deque", "NamedTuple", "TypedDict", "Annotated",
}

EXTERNAL = "EXTERNAL"


def path_to_dotted(path):
    rel = os.path.relpath(os.path.abspath(path), ROOT_PARENT)
    parts = rel.split(os.sep)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return ".".join(parts)


def attach_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    tree.parent = None
    return tree


def is_literal_subscript(node):
    if not isinstance(node, ast.Subscript):
        return False
    v = node.value
    name = v.attr if isinstance(v, ast.Attribute) else getattr(v, "id", None)
    return name == "Literal"


def collect_quoted_constants(annotation_node):
    """Yield ast.Constant string nodes inside an annotation, skipping the
    value-slice of Literal[...] subscripts (those are real string values,
    not forward references)."""
    skip_ids = set()
    stack = [annotation_node]
    while stack:
        node = stack.pop()
        if is_literal_subscript(node):
            skip_ids.add(id(node.slice))
            for n2 in ast.walk(node.slice):
                skip_ids.add(id(n2))
            stack.append(node.value)
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in skip_ids:
                yield node
        for child in ast.iter_child_nodes(node):
            if id(child) not in skip_ids:
                stack.append(child)


def names_in_expr(expr_src):
    try:
        tree = ast.parse(expr_src, mode="eval")
    except SyntaxError:
        return None
    return [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]


class ModuleInfo:
    """Per-file facts needed to classify a quoted name: same-module
    forward references, TYPE_CHECKING-only imports, function-local/lazy
    imports, and the raw list of ordinary (unguarded, module-level)
    import statements (handed off to RepoGraph for cross-file analysis)."""

    def __init__(self, tree):
        self.type_checking_names = set()
        self.local_import_names = set()
        self.module_level_defs = {}  # name -> lineno the def/class body ends
        self.normal_import_nodes = []  # raw Import/ImportFrom nodes, module-level, unguarded
        self._collect(tree)

    @staticmethod
    def _bound_names(node):
        names = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.append(alias.asname or alias.name)
        return names

    def _collect(self, tree):
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                # Use end_lineno: the name isn't bound in the module
                # namespace until the whole class/def statement finishes
                # executing, so a self-reference anywhere inside a class's
                # own body (e.g. a method returning its own class) is a
                # true forward reference even though it's textually after
                # the `class Foo:` line.
                self.module_level_defs.setdefault(node.name, node.end_lineno)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.module_level_defs.setdefault(t.id, node.end_lineno)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    self.module_level_defs.setdefault(node.target.id, node.end_lineno)

        for node in tree.body:
            if isinstance(node, ast.If):
                test = node.test
                is_tc = (
                    (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
                    or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
                )
                if is_tc:
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.Import, ast.ImportFrom)):
                            self.type_checking_names.update(self._bound_names(sub))
                    continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.normal_import_nodes.append(node)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(node):
                    if isinstance(sub, (ast.Import, ast.ImportFrom)):
                        self.local_import_names.update(self._bound_names(sub))

    def classify_local(self, name, use_lineno):
        """Classify against same-file facts only. Returns (severity, reason)
        with severity in {"HIGH", None} if resolved here, or None (as the
        whole tuple) if RepoGraph needs to be consulted next."""
        if name in BUILTIN_TYPE_NAMES:
            return "HIGH", "builtin/typing construct never needs quoting"
        if name in self.type_checking_names:
            return None, "legitimately deferred (TYPE_CHECKING import)"
        if name in self.local_import_names:
            return None, "legitimately deferred (function-local/lazy import)"
        if name in self.module_level_defs:
            def_line = self.module_level_defs[name]
            if def_line < use_lineno:
                return "HIGH", (f"'{name}' fully defined earlier in file (its def/class "
                                 f"body ends at line {def_line}); no forward-ref needed")
            return None, "true forward reference (defined later in same file)"
        return "UNRESOLVED", None


class RepoGraph:
    """Whole-package module import graph, used to tell a genuine circular
    import (two modules that transitively import each other) apart from an
    ordinary direct import (which can never require quoting, since if it
    imports cleanly today there's no cycle stalling it)."""

    def __init__(self, module_map):
        self.module_map = module_map  # dotted name -> file path
        self.edges = {}  # dotted -> set(dotted), internal-only
        self.name_targets = {}  # path -> {bound_name: dotted-or-EXTERNAL}
        self._scc_id = {}

    def _resolve_absolute(self, dotted_name):
        if dotted_name == PACKAGE_NAME or dotted_name.startswith(PACKAGE_NAME + "."):
            return dotted_name
        return EXTERNAL

    @staticmethod
    def _relative_base(cur_dotted, is_init, level):
        base = cur_dotted if is_init else (cur_dotted.rsplit(".", 1)[0] if "." in cur_dotted else "")
        for _ in range(level - 1):
            base = base.rsplit(".", 1)[0] if "." in base else ""
        return base

    def add_file_imports(self, path, dotted, is_init, import_nodes):
        bound = {}
        self.edges.setdefault(dotted, set())
        for node in import_nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    target = self._resolve_absolute(alias.name)
                    bound[name] = target
                    if target != EXTERNAL:
                        self.edges[dotted].add(target)
            else:  # ast.ImportFrom
                if node.level and node.level > 0:
                    base = self._relative_base(dotted, is_init, node.level)
                    if node.module:
                        base = f"{base}.{node.module}" if base else node.module
                else:
                    base = node.module or ""
                    if base and not (base == PACKAGE_NAME or base.startswith(PACKAGE_NAME + ".")):
                        base = EXTERNAL
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    if base == EXTERNAL or not base:
                        target = EXTERNAL if base == EXTERNAL else self._resolve_absolute(alias.name)
                    else:
                        candidate = f"{base}.{alias.name}"
                        if candidate in self.module_map:
                            target = candidate
                        elif base in self.module_map or base == PACKAGE_NAME or base.startswith(PACKAGE_NAME + "."):
                            target = base  # attribute of that module, still an edge to it
                        else:
                            target = EXTERNAL
                    bound[name] = target
                    if target != EXTERNAL:
                        self.edges[dotted].add(target)
        self.name_targets[path] = bound

    def compute_scc(self):
        """Kosaraju's algorithm, iterative to avoid recursion-depth issues."""
        nodes = set(self.edges)
        for targets in self.edges.values():
            nodes.update(targets)

        order = []
        visited = set()
        for start in nodes:
            if start in visited:
                continue
            visited.add(start)
            stack = [(start, iter(self.edges.get(start, ())))]
            while stack:
                node, it = stack[-1]
                advanced = False
                for nxt in it:
                    if nxt not in visited:
                        visited.add(nxt)
                        stack.append((nxt, iter(self.edges.get(nxt, ()))))
                        advanced = True
                        break
                if not advanced:
                    order.append(node)
                    stack.pop()

        rev = {n: set() for n in nodes}
        for n, targets in self.edges.items():
            for t in targets:
                rev[t].add(n)

        visited2 = set()
        comp_id = 0
        for node in reversed(order):
            if node in visited2:
                continue
            stack = [node]
            visited2.add(node)
            while stack:
                n = stack.pop()
                self._scc_id[n] = comp_id
                for nxt in rev.get(n, ()):
                    if nxt not in visited2:
                        visited2.add(nxt)
                        stack.append(nxt)
            comp_id += 1

    def same_cycle(self, dotted_a, dotted_b):
        if dotted_a == dotted_b:
            return False
        ida = self._scc_id.get(dotted_a)
        idb = self._scc_id.get(dotted_b)
        return ida is not None and ida == idb

    def target_for(self, path, name):
        return self.name_targets.get(path, {}).get(name)

    def classify(self, name, path, dotted):
        target = self.target_for(path, name)
        if target is None:
            return "LOW", f"'{name}' not resolved to any import/definition in this file; verify manually"
        if target == EXTERNAL:
            return "HIGH", (f"'{name}' is an external (non-package) import; an outside "
                             f"library can't import this package back, so it can never "
                             f"need quoting for circular-import reasons")
        if self.same_cycle(dotted, target):
            return None, (f"'{name}' ({target}) and this module ({dotted}) transitively "
                           f"import each other (same import cycle); quoting may genuinely be required")
        return "HIGH", (f"'{name}' ({target}) imported directly; no import cycle exists "
                         f"between it and this module ({dotted}); quoting unnecessary")


def iter_annotation_nodes(tree):
    """Yield (annotation_ast_node, function_or_none) for every annotation
    location: function args/returns and AnnAssign (class/instance vars)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            for a in all_args:
                if a.annotation is not None:
                    yield a.annotation, node
            if node.returns is not None:
                yield node.returns, node
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation, None


def classify_name(name, use_lineno, info, graph, path, dotted):
    """Single source of truth for 'does this name need to stay quoted',
    shared by detection (scan_quoting) and fix application. Returns
    (severity, reason): "HIGH" = safe/should be unquoted, None = must
    stay deferred (quoted), "LOW" = unresolved, can't tell either way."""
    severity, reason = info.classify_local(name, use_lineno)
    if severity == "UNRESOLVED":
        severity, reason = graph.classify(name, path, dotted)
    return severity, reason


def scan_quoting(path, tree, info, graph, dotted, rows):
    for annotation_node, _fn in iter_annotation_nodes(tree):
        for const in collect_quoted_constants(annotation_node):
            content = const.value
            names = names_in_expr(content)
            if names is None:
                rows.append([path, const.lineno, content, "LOW", "quoted content is not a parsable expression"])
                continue
            if not names:
                continue
            best_severity = None
            reasons = []
            for n in names:
                severity, reason = classify_name(n, annotation_node.lineno, info, graph, path, dotted)
                if severity:
                    reasons.append(f"{n}: {reason}")
                    if severity == "HIGH":
                        best_severity = "HIGH"
                    elif best_severity != "HIGH" and best_severity is None:
                        best_severity = severity
            if best_severity:
                rows.append([path, const.lineno, content, best_severity, "; ".join(reasons)])


def maximal_ref_nodes(sub_tree):
    """Within a parsed annotation-content expression, yield each Name or
    Attribute node that is a *whole* reference on its own -- i.e. not the
    base of a longer dotted chain (that chain's own outermost Attribute is
    the maximal node instead). `_wire_marker.WireMarker` yields one node
    (the Attribute), not two."""
    parent_of = {}
    for node in ast.walk(sub_tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node

    for node in ast.walk(sub_tree):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            continue
        parent = parent_of.get(id(node))
        if isinstance(parent, ast.Attribute) and parent.value is node:
            continue  # embedded in a longer chain; the outer Attribute is the maximal node
        yield node


def root_name_of(ref_node):
    n = ref_node
    while isinstance(n, ast.Attribute):
        n = n.value
    return n.id if isinstance(n, ast.Name) else None


def plan_constant_fix(const, use_lineno, info, graph, path, dotted):
    """Decide what to do with one flagged quoted Constant node. Returns a
    dict: {"action": "fix", "replacement": str}
        | {"action": "skip", "reason": str}
        | {"action": "noop"}   (nothing needed -- shouldn't normally occur
                                 for a flagged node, but safe to no-op)."""
    content = const.value
    if const.lineno != const.end_lineno:
        return {"action": "skip", "reason": "multi-line quoted annotation; needs manual review"}

    try:
        sub_tree = ast.parse(content, mode="eval")
    except SyntaxError:
        return {"action": "skip", "reason": "quoted content is not a parsable expression"}

    parent_of = {}
    for node in ast.walk(sub_tree):
        for child in ast.iter_child_nodes(node):
            parent_of[id(child)] = node

    refs = list(maximal_ref_nodes(sub_tree))
    if not refs:
        return {"action": "noop"}

    safe_refs = []
    defer_refs = []
    for ref in refs:
        name = root_name_of(ref)
        if name is None:
            continue
        severity, _reason = classify_name(name, use_lineno, info, graph, path, dotted)
        if severity == "HIGH":
            safe_refs.append(ref)
        elif severity is None:
            defer_refs.append(ref)
        else:  # LOW / unresolved
            return {"action": "skip", "reason": f"'{name}' not resolved; needs manual review"}

    if not safe_refs:
        return {"action": "noop"}  # nothing here was actually a violation

    # A name that must stay a string can't sit directly on either side of a
    # bare `X | Y` union operator -- `int | "Foo"` raises TypeError at
    # runtime (unlike `Union[int, "Foo"]` or `list["Foo"]`, both of which
    # accept a plain string operand fine). If that's the shape here, fixing
    # it means restructuring to `Union[...]`, which is a bigger, judgment-
    # requiring rewrite -- flag for manual review instead of guessing.
    for ref in defer_refs:
        parent = parent_of.get(id(ref))
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.BitOr):
            return {"action": "skip",
                    "reason": ("mixes a builtin/safe type with a name that must stay quoted "
                               "inside a bare `X | Y` union -- needs a manual rewrite to "
                               "`typing.Union[...]` (or equivalent), not a mechanical unquote")}

    if not defer_refs:
        return {"action": "fix", "replacement": content}

    new_content = content
    for ref in sorted(defer_refs, key=lambda r: r.col_offset, reverse=True):
        start, end = ref.col_offset, ref.end_col_offset
        new_content = new_content[:start] + '"' + new_content[start:end] + '"' + new_content[end:]
    return {"action": "fix", "replacement": new_content}


def apply_quoting_fixes(path, tree, src, info, graph, dotted, fixed_count, skipped):
    """Rewrite `src` (the file's current text) in place, splicing in the
    planned fix for every flagged Constant node, and return the new text
    (unchanged if nothing to do). Mutates fixed_count[0] and appends to
    `skipped` for anything that needed a human instead."""
    edits = []  # (lineno, col_offset, end_lineno, end_col_offset, replacement)
    for annotation_node, _fn in iter_annotation_nodes(tree):
        for const in collect_quoted_constants(annotation_node):
            plan = plan_constant_fix(const, annotation_node.lineno, info, graph, path, dotted)
            action = plan["action"]
            if action == "noop":
                continue
            if action == "skip":
                skipped.append((path, const.lineno, const.value, plan["reason"]))
                continue
            edits.append((const.lineno, const.col_offset, const.end_lineno, const.end_col_offset,
                           plan["replacement"]))

    if not edits:
        return src

    lines = src.splitlines(keepends=True)
    # Apply bottom-to-top, right-to-left so earlier edits' offsets stay valid.
    for lineno, col_offset, end_lineno, end_col_offset, replacement in sorted(
            edits, key=lambda e: (e[0], e[1]), reverse=True):
        assert lineno == end_lineno, "multi-line spans are filtered out in plan_constant_fix"
        line = lines[lineno - 1]
        newline = ""
        if line.endswith("\r\n"):
            line, newline = line[:-2], "\r\n"
        elif line.endswith("\n"):
            line, newline = line[:-1], "\n"
        lines[lineno - 1] = line[:col_offset] + replacement + line[end_col_offset:] + newline
        fixed_count[0] += 1

    return "".join(lines)


NON_LOCAL_SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def own_scope_nodes(func_node):
    """All descendant nodes belonging to func_node's own scope -- does not
    descend into a nested def/lambda/class, since a `return`/`yield` there
    belongs to that inner scope, not to func_node."""
    stack = list(func_node.body)
    out = []
    while stack:
        n = stack.pop()
        out.append(n)
        if isinstance(n, NON_LOCAL_SCOPE_TYPES):
            continue
        stack.extend(ast.iter_child_nodes(n))
    return out


def is_empty_return(ret_node):
    if ret_node.value is None:
        return True
    return isinstance(ret_node.value, ast.Constant) and ret_node.value.value is None


def none_return_candidate(func_node):
    """Return a reason string if func_node provably never returns a value
    (so `-> None` is the correct, unambiguous annotation), else None.
    Generators (contain yield/yield from in their own scope) are excluded:
    a bare `return` there just stops iteration, it doesn't mean the
    function's return type is None."""
    nodes = own_scope_nodes(func_node)
    if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in nodes):
        return None
    return_nodes = [n for n in nodes if isinstance(n, ast.Return)]
    if not return_nodes:
        return "no return statement in function body (implicit None)"
    if all(is_empty_return(r) for r in return_nodes):
        return "only bare `return` / `return None` statement(s)"
    return None


def decorator_labels(node):
    labels = []
    for d in node.decorator_list:
        if isinstance(d, ast.Name):
            labels.append(d.id)
        elif isinstance(d, ast.Attribute):
            labels.append(d.attr)
    return labels


def scan_missing_hints(path, tree, rows, none_return_rows):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "__init__":
            continue
        parent = getattr(node, "parent", None)
        is_method = isinstance(parent, ast.ClassDef)
        labels = decorator_labels(node)
        is_static = "staticmethod" in labels

        args = node.args
        positional = list(args.posonlyargs) + list(args.args)
        skip_first = is_method and not is_static and positional
        first_name = positional[0].arg if positional else None
        implicit_first = skip_first and first_name in ("self", "cls")

        all_args = list(positional)
        if args.vararg:
            all_args.append(args.vararg)
        for a in args.kwonlyargs:
            all_args.append(a)
        if args.kwarg:
            all_args.append(args.kwarg)

        qualname = node.name
        if is_method and isinstance(parent, ast.ClassDef):
            qualname = f"{parent.name}.{node.name}"

        deco = ",".join(labels) if labels else ""

        for a in all_args:
            if implicit_first and a is positional[0]:
                continue
            if a.annotation is None:
                rows.append([path, a.lineno, qualname, a.arg, "parameter", deco, "", ""])

        if node.returns is None:
            reason = none_return_candidate(node)
            rows.append([path, node.lineno, qualname, "(return)", "return", deco,
                         "yes" if reason else "", reason or ""])
            if reason:
                none_return_rows.append([path, node.lineno, qualname, deco, reason])


def collect_py_files(root):
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for fn in filenames:
            if fn.endswith(".py"):
                paths.append(os.path.join(dirpath, fn))
    return paths


def main():
    require_clean_git_tree()

    py_files = collect_py_files(ROOT)

    module_map = {}
    file_dotted = {}
    file_is_init = {}
    for path in py_files:
        dotted = path_to_dotted(path)
        file_dotted[path] = dotted
        file_is_init[path] = os.path.basename(path) == "__init__.py"
        module_map[dotted] = path

    graph = RepoGraph(module_map)

    parsed = {}
    sources = {}
    module_infos = {}
    error_count = 0
    for path in py_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
            tree = ast.parse(src, filename=path)
        except (SyntaxError, UnicodeDecodeError) as e:
            error_count += 1
            print(f"SKIP (parse error): {path}: {e}")
            continue
        attach_parents(tree)
        parsed[path] = tree
        sources[path] = src
        info = ModuleInfo(tree)
        module_infos[path] = info
        graph.add_file_imports(path, file_dotted[path], file_is_init[path], info.normal_import_nodes)

    graph.compute_scc()

    quoting_rows = []
    missing_rows = []
    none_return_rows = []
    for path, tree in parsed.items():
        scan_quoting(path, tree, module_infos[path], graph, file_dotted[path], quoting_rows)
        scan_missing_hints(path, tree, missing_rows, none_return_rows)

    quoting_path = os.path.join(OUT_DIR, "quoting_violations.csv")
    with open(quoting_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "line", "quoted_content", "confidence", "reason"])
        for r in sorted(quoting_rows, key=lambda r: (r[3] != "HIGH", r[0], r[1])):
            w.writerow(r)

    missing_path = os.path.join(OUT_DIR, "missing_type_hints.csv")
    with open(missing_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "line", "function", "parameter", "kind", "decorators",
                     "likely_none_return", "none_reason"])
        for r in sorted(missing_rows, key=lambda r: (r[0], r[1])):
            w.writerow(r)

    none_return_path = os.path.join(OUT_DIR, "implicit_none_returns.csv")
    with open(none_return_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "line", "function", "decorators", "reason"])
        for r in sorted(none_return_rows, key=lambda r: (r[0], r[1])):
            w.writerow(r)

    print(f"\nScanned {len(py_files)} files ({error_count} parse errors).")
    print(f"Quoting violations: {len(quoting_rows)} -> {quoting_path}")
    high = sum(1 for r in quoting_rows if r[3] == "HIGH")
    med = sum(1 for r in quoting_rows if r[3] == "MEDIUM")
    low = sum(1 for r in quoting_rows if r[3] == "LOW")
    print(f"  HIGH confidence: {high}   MEDIUM: {med}   LOW: {low}")
    print(f"Missing type hints: {len(missing_rows)} -> {missing_path}")
    params = sum(1 for r in missing_rows if r[4] == "parameter")
    rets = sum(1 for r in missing_rows if r[4] == "return")
    print(f"  missing params: {params}   missing returns: {rets}")
    print(f"Implicit `-> None` candidates (subset of missing returns): "
          f"{len(none_return_rows)} -> {none_return_path}")

    if "--apply" in sys.argv:
        print("\nApplying quoting fixes...")
        fixed_count = [0]
        skipped = []
        files_changed = 0
        for path, tree in parsed.items():
            new_src = apply_quoting_fixes(
                path, tree, sources[path], module_infos[path], graph, file_dotted[path],
                fixed_count, skipped,
            )
            if new_src != sources[path]:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new_src)
                files_changed += 1

        print(f"Fixed {fixed_count[0]} quoted annotation(s) across {files_changed} file(s).")
        if skipped:
            print(f"Skipped {len(skipped)} (needs manual review):")
            for path, lineno, content, reason in skipped:
                print(f"  {path}:{lineno}: {content!r} -- {reason}")


if __name__ == "__main__":
    main()
