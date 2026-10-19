## FILES

#### AI_PLUGIN_DESIGN.md

The full design document for this package — vocabulary (Session/Job/steering), threading model, and the
"asking the user" pattern (which turned out to need no new tracked state once checked against
`../plugins/claude_ai/qt/gui_call.call_in_gui()` — see `../plugins/claude_ai/qt/MAP.md`; this path moved from
`../../claude/qt/` when that package was relocated under `plugins/plugins/claude_ai/`, see `../plugins/MAP.md`).
Read it, and `../PLUGIN_DESIGN.md`
for the generic registration mechanism it sits on top of (but is deliberately NOT inherited from directly —
see `base.py` below), before touching anything here.

#### __init__.py

Re-exports `AIBase`, `Job`, `Session`, `CancelToken`, `Cancelled`, `REASON_CLOSE`, `REASON_STEER` from
`base.py`/`job.py`/`session.py`/`cancel.py`.

#### base.py

`AIBase` — the base a concrete backend subclasses, *alongside* `Plugin` (never through it — see
`../plugin.py`'s `_PluginMeta` adjacency requirement, which an abstract intermediate base like this can't
satisfy; a concrete backend combines both via multiple inheritance, e.g. `class ClaudePlugin(AIBase,
Plugin): ...`, with `start_registration()` called immediately before that one class statement). Owns the
`Session`'s thread and `Job` dispatch (`_session_loop`); `_run(session, job, cancel)` is the abstract hook a
concrete backend implements: make the real API call(s), run any tool loop, call `job.on_progress`/
`job.on_usage` as it goes, and call `job.on_complete(result)` itself when done. **`_run` must NEVER call
`job.on_error`** — let the error propagate; `_session_loop` is the one place that calls it, so it's only ever
called once. When a Session is steered while `_run` is in flight, `cancel.raise_if_cancelled()` raises
`Cancelled(REASON_STEER)`; `_run` is then called again for the SAME `Job` with a fresh token, and should
call `session.take_steer_message()` near its own start so a retry picks up the folded-in message.

#### cancel.py

`CancelToken`/`Cancelled`, generalized from `../plugins/claude_ai/cancel.py`'s version (formerly
`../../claude/cancel.py` before that package's relocation) one layer up, with a *reason*
(`REASON_CLOSE` — the Session itself is shutting down, stop and do not re-send; `REASON_STEER` — "Send now",
discard the in-flight call and immediately re-send with the folded-in message, the Job keeps running). Plain
Python threads can't be killed from outside, so this cooperative check-then-raise pattern
(`raise_if_cancelled()`) is the only mechanism — a plugin with a real side effect must checkpoint rather than
assume a call runs to completion. A steering cancel must never be reported to a `Job` as an error — only
`_session_loop` calls `on_error`, and only for a genuine failure or a close teardown, never for steering.

#### job.py

`Job` — one instruction a call site hands to an AI `Session`; subclassed by the call site itself, never by a
plugin. `on_progress`/`on_usage` may fire any number of times; exactly one of `on_complete`/`on_error` fires
once, terminal. None of these run on the GUI thread — `call_after(fn, *args)` (forwards to `app.CallAfter`)
is the only sanctioned way a subclass touches a widget. Request-data shape is deliberately undefined here
(see `AI_PLUGIN_DESIGN.md` "Open questions") — a concrete `Job` subclass carries whatever its own call site
needs as plain attributes.

#### session.py

`Session` — one open-ended activity (named from its first message — mechanism not yet built); holds
history; runs `Job`s one at a time on its own plain `threading.Thread` (never `QThread`). Created by an
`AIBase.create_session()`, never directly; closed only when the user closes the owning dialog, never merely
because a `Job` completed. `steer(message)` is "Send now": cancels whatever call is in flight with
`REASON_STEER` and folds the new message into the SAME `Job` — a genuinely new `Job` only ever comes from an
explicit, distinct user action, never inferred from message content.

**Contract-only status** (applies to this whole package): `Job`/`Session`/`AIBase`/`CancelToken` are built
and logic-checked, but there is no concrete backend wired to this contract yet — don't assume a
Claude-via-`plugins.ai` or Gemini backend exists just because this package does. No Qt, no provider SDK is
imported anywhere in this package.
