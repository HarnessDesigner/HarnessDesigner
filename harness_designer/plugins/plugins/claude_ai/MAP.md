## FILES

#### __init__.py

Package init.

#### cancel.py

`CancelToken` — cancellation for an in-flight Claude call. Predates (and is distinct from) the more general `plugins/ai/cancel.py` `CancelToken`, which is generalized from this one with an added reason (`REASON_STEER` vs `REASON_CLOSE`) — see `plugins/ai/MAP.md`. Whether this module should eventually be replaced by that one, or kept as this backend's own, isn't resolved yet.

#### client.py

`ClaudeClient` — owns the SDK client built from the stored key. `ask()` (one question), `conversation()` (start a `Conversation`), `check_connection()`, `derive()`. Always streams (nothing times out; calls can be cancelled); translates SDK errors into this package's own `ClaudeError` subclasses; keeps a running `usage` total. `warm_up()` pre-imports the SDK on a background thread (the first import takes ~3s).

#### context.py

`ContextProvider`/`ContextBlock`/`StaticContext` — how outside knowledge gets rendered once into a conversation's frozen system prompt (the seam for what a future feature, e.g. concentric twisting, would feed the model).

#### conversation.py

`Conversation` — **APPEND-ONLY**: model, tools, and system prompt are fixed at creation; history only ever grows. Claude's thinking blocks are bound to the conversation, so editing an earlier turn is an API error (400), not just semantically wrong. `send()` runs the tool loop and structured output; `note()` adds a later-learned fact as a `role: system` message rather than rewriting history; a failed or cancelled `send()` leaves history exactly as it was before the call.

#### errors.py

`ClaudeError` and subclasses, each with a `user_message` fit to show directly to the user.

#### keys.py

`ApiKeyStore` — the user's API key in the system credential store (service `HarnessDesigner`, name `anthropic_api_key` — the same slot the earlier scraper-tool Claude client used). `MemoryKeyring` is the in-memory fallback for a key the user chooses not to save to the system store.

#### messages.py

`Tool`, `Usage` (carries a cost estimate), `Response`.

#### models.py

The offered models and their prices (cost-estimate purposes only); `DEFAULT_MODEL`.

#### settings.py

`ClaudeSettings` (model, effort, max_tokens, refusal fallback, retries, timeout) plus the application-wide `current()`/`update()` and a `SettingsBackend` seam so the host app can persist them (e.g. into `Config`).

#### wire.py

Reads raw SDK messages (text, usage, tool calls, refusal-fallback cleaning) into this package's own shapes.

## FOLDERS

#### qt/

The Qt-facing layer — `ClaudeJob`, `call_in_gui()`, and the API-key dialog. See `qt/MAP.md`.

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.

#### Claude API: one shared package, now `harness_designer/plugins/plugins/claude_ai/` (moved from `harness_designer/claude/` during the plugin-system rewrite, 2026-10-19); design in CLAUDE_API_DESIGN.md (repo root) (started 2026-10-17)
User's instruction: the Claude API code lives in its own package inside `harness_designer`, written to be used from more than one place -- the scraper assistant first, then **concentric twisting** (Claude works out how the bundle's layers should be arranged and is meant to LEARN what the user wants: questions asked of the user about wire positions are saved so Claude reasons better next time -- explicitly NOT being built yet). Read `CLAUDE_API_DESIGN.md` in full before touching anything under `claude_ai/` or adding any code that talks to Claude, and add new decisions THERE, not here (note: that doc, `AI_PLUGIN_DESIGN.md`, and several `MAP.md` files still say `harness_designer/claude/` in places -- not yet swept for the rename, don't trust the literal path in prose, check the actual directory). Standing rules: nothing outside `claude_ai/` imports `anthropic`; the user's own key lives only in the system credential store (service `HarnessDesigner`, name `anthropic_api_key`), never env vars/files/Config; a `Conversation` is APPEND-ONLY (model, tools, system prompt fixed at creation -- Opus 5.5 binds thinking blocks to the conversation, so editing history is a 400; later-learned facts go in via `note()`); saved user decisions will enter through a `ContextProvider` (rendered once at conversation start). Claude is the judgement layer and calls the packing solver as a tool -- it does not compute geometry (see "Wire bundle packing requirements"). Anything that exercises the key store must use an in-memory backend -- never the real Windows Credential Manager, which holds the user's actual key.

**Rename pitfall, found + fixed 2026-10-19 (see "PyInstaller collect_submodules..." below for the full story):** moving `claude/` two directories deeper (`plugins/plugins/claude_ai/`) left every relative import that reached *outside* the package (`from .. import check_types` at the `claude_ai/` level, `from ... import check_types`/`from ...ui...` at the `claude_ai/qt/` level) pointing 2 levels too shallow -- they resolved to `harness_designer.plugins.plugins` (or `.plugins`) instead of `harness_designer`. Imports *within* the package (`from . import X`, and `qt/`'s `from .. import <claude_ai sibling>`) were unaffected since the internal depth didn't change. Also left behind: three external callers still importing the module by its pre-move name -- `ui/editor_script/{assistant_panel,script_editor}.py` and `scraping/{assistant_tools,json_extract}.py` all had `from .. import claude` / `from ... import claude`. Whenever a package moves to a different depth under `harness_designer`, grep the whole tree for both patterns (relative imports *inside* the moved package that cross its old boundary, and any external `import <old name>`) rather than assuming the move is just a `git mv`.
