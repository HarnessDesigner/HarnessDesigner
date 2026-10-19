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
