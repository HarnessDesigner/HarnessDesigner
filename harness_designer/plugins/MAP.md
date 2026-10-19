## FILES

#### PLUGIN_DESIGN.md

The full design document for this package — read before adding a new plugin type or changing the
registration mechanism.

#### __init__.py

Empty besides the copyright header; no re-exports. Importers reach `plugin.py`/`register.py` directly
(`from harness_designer.plugins import plugin` / `register`), not through this file.

#### plugin.py

`Plugin` base class + `start_registration(instance)`. The `_PluginMeta` metaclass attaches whatever
`RegisterPlugin` instance was just handed to `start_registration()` onto the *next* `Plugin` subclass
defined — `cls._registration = _registering` runs in `_PluginMeta.__init__`, which fires for every class
statement using this metaclass. **The `start_registration()` call and the `class Foo(Plugin):` statement
must be textually adjacent** — anything in between, or omitting the call, raises `RuntimeError` (either
"registration conflict" if called twice without a class consuming the first, or a bare `RuntimeError` if a
`Plugin` subclass is defined with no pending registration at all). Any statement between the call and the
class it's meant to tag still works in practice as long as no OTHER `Plugin` subclass gets defined in
between, but keep them adjacent — it's easy to break this accidentally.

#### register.py

`RegisterPlugin` — plugin metadata (name, plugin_type, short/long description, author, email, support_url,
optional icon). `PLUGIN_TYPE_*` is a bitmask: `MISC` (0x00), `DATABASE` (0x01), `SCRAPER` (0x02), `3D`
(0x04), `SCHEMATIC` (0x08), `PEGBOARD` (0x10), `AI` (0x20).

## FOLDERS

#### ai/

The provider-agnostic AI plugin contract built on top of this framework — see `ai/MAP.md`. No discovery or
loading mechanism exists yet for this package as a whole — a `Plugin` subclass being defined and registered
doesn't mean anything in the app actually finds or activates it. Don't assume otherwise when reading code
that touches this package.

#### plugins/

Concrete plugin implementations, as distinct from this package's registration framework and `ai/`'s
contract — see `plugins/MAP.md`. Currently holds `claude_ai/`, the former top-level `harness_designer/claude/`
package relocated here. The move (confirmed via `git status` — a clean rename, no content changes) appears to
be a pure relocation so far: `claude_ai/` does not yet subclass `Plugin` or `plugins.ai.base.AIBase`, so despite
its new address it isn't actually wired into this registration framework or the `ai/` contract yet. Don't
assume the relocation alone means it conforms to either.
