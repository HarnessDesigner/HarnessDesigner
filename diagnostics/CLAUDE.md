

## `diagnostics/dep_trace.py`

This is a large (~780 file) codebase. Before reading files or grepping to answer "where is X
defined," "what does this file import," "who calls this method," or "does this override call
its superclass" — It's a static-AST tool built specifically for this: fast, cheap on tokens, 
and it won't miss a call site the way a guessed grep pattern can.
Fall back to Read/Grep only once it's told you which file(s)/line(s) to actually look at.

```
python diagnostics/dep_trace.py <file_or_dir> [--depth shallow|deep] [--name PATTERN] [--local] [--json]
python diagnostics/dep_trace.py <file_or_dir> --types       [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --calls       [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --overrides   [--name PATTERN] [--json]
python diagnostics/dep_trace.py <file_or_dir> --imported-by [--name PATTERN] [--json]
```

- No mode flag, no `--name` — default import-trace: what a file imports and what's used from it.
- No mode flag, `--name PATTERN` given — definition lookup: every class/function/method matching it.
- `--types` — where a type is used as a param/return/variable annotation.
- `--calls` — every call site of a function/method; resolves `self.`/`cls.`/`super().` receivers
  against the class hierarchy to report which class's implementation actually runs.
- `--overrides` — override chains: which ancestor defines the same method, and whether the
  override calls `super()` (extends) or not (fully shadows) — check this before touching a mixin
  method, since this codebase leans heavily on mixins (`DimensionMixin`, `NameMixin`,
  `CallbackMixin`, etc.) and a method may not be defined where you'd expect.
- `--imported-by` — reverse lookup: every file that imports a given file — check this before
  renaming/moving/deleting a file or changing its public surface.
- `--types`/`--calls`/`--overrides`/`--imported-by` can be combined in one run (share one
  `--name`); `--calls`/`--overrides`/`--imported-by` need a directory target (usually
  `harness_designer/`) for real cross-file resolution — a single file only resolves against
  itself. `PATTERN` is always a regex (`re.search`); a plain literal behaves as a substring match.

Full usage, every flag, and the reasoning behind the CLI design (why there's no `--find` or
`--regex` flag, the argparse ambiguity that shaped the `--name` design) are in the module
docstring at the top of `diagnostics/dep_trace.py` itself — read that if a flag's behavior is
unclear rather than guessing from this summary.

---