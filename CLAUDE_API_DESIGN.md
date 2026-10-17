# Claude API package design

`harness_designer/claude/` is the ONE place the application talks to the Claude API. Anything that wants Claude
(the scraper assistant today, concentric twisting later, whatever comes after) imports this package; nothing else
imports `anthropic`. Add new decisions about it HERE, not in MEMORY.md.

Status (2026-10-17): built, and checked against a fake Messages API server and a headless Qt while the tests existed
(see "Testing"; there are no unit tests now).
NOT yet exercised against the live API (no key was used). Callers so far: `scraping/json_extract.describe()` and the
scraper assistant (`ui/editor_script/assistant_panel.py`, SCRAPER_DESIGN.md "Phase 3 as built" -- the first real
consumer: a tool-using, streamed conversation run through `ClaudeJob`); concentric twisting is the next. Only the
assistant panel's settings button opens the key / model dialog (no menu entry elsewhere yet), and nothing calls
`claude.set_settings_backend()` yet, so settings are in-memory until the app wires them to Config.

## What the user asked for (2026-10-17)

- The Claude API code lives in its own package inside `harness_designer`, written so it can be used from more
  than one place.
- First other use: **concentric twisting** -- have Claude work out how the layers of a bundle should be
  arranged. That feature is meant to *learn what the user wants*: when it has to ask the user something about
  the positions of wires in a bundle, the decision is **saved** so Claude can reason better next time.
- "We aren't doing that at the moment." The learning/decision-memory part is NOT built. This package only
  provides the seams it will plug into (see "Concentric twisting: what is built, what is not").

## Package layout

```
harness_designer/claude/              no Qt, no UI; importable from a worker process or a test
    __init__.py       the public surface (everything a caller needs is re-exported here)
    errors.py         ClaudeError and subclasses, each with a message fit to show the user
    keys.py           ApiKeyStore -- the user's own key, in the system credential store (keyring)
    models.py         the models the app offers, their prices, what each supports; defaults
    settings.py       ClaudeSettings (model, effort, max_tokens, fallback, retries, timeout) + persistence hook
    cancel.py         CancelToken -- stop a call that is in flight
    messages.py       Tool, Usage, Response
    context.py        ContextProvider / ContextBlock -- how outside knowledge is fed into a conversation
    conversation.py   Conversation -- an append-only exchange; streaming, tools, structured output
    client.py         ClaudeClient -- owns the SDK client; ask() for one-shot calls, conversation() for the rest;
                      check_connection(), derive() (same client, other key/settings), warm_up() (pre-import the SDK)
    wire.py           reads SDK messages (text, usage, tool calls, fallback cleaning): the only code that knows their shape
    qt/               the Qt layer; importing the package above never imports Qt
        job.py        ClaudeJob -- run a call on a thread, signals back on the GUI thread, cancel()
        gui_call.py   call_in_gui() -- let a tool running on the worker thread ask the user something
        key_dialog.py ApiKeyDialog -- enter / test / clear the key, pick model and effort
```

## Decisions

- **The official `anthropic` SDK**, through `ClaudeClient` only. The key is the user's own, in `keyring`
  (service `HarnessDesigner`, name `anthropic_api_key`, the same slot the earlier scraper client used).
  It is never read from environment variables and never written to a file: no key means `NoApiKeyError`, not
  a quiet fallback.
- **Default model `claude-opus-5-5`**, `output_config.effort` explicit (`medium`, the model's own default,
  written out so it cannot drift). Sonnet 5.5 / Haiku 5.5 / Fable 5.1 are selectable. The package never sends
  `temperature` / `top_p` / `top_k` / `thinking` / `budget_tokens` / forced `tool_choice` (all 400 on these
  models); thinking is always on and its depth is the effort setting.
- **Always streams.** Even `ask()` streams internally and reads the final message, so a long answer cannot hit a
  request timeout, `max_tokens` can stay generous (64000 default; it is a cap, not a charge), and a call can be
  cancelled mid-flight.
- **Refusal fallback on by default** (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`, the beta
  endpoint), as Anthropic recommends for these models; a setting turns it off, and Haiku 5.5 never gets it (no
  such fallback exists there). If the user's organisation cannot use that beta the API answers 400 about the
  `anthropic-beta` header; that surfaces as `BetaNotAvailable` with the instruction to switch the setting off.
  It is NOT retried behind the user's back (no fallback paths). When a fallback model served a turn, the
  assistant content is cleaned before it is sent back (`Conversation` handles it).
- **Errors:** every SDK exception is translated, most specific first, into one of our own (`RateLimited`,
  `AuthenticationFailed`, `ServiceUnavailable`, `BadRequest`, `BetaNotAvailable`, `Refused`, `Truncated`,
  `Cancelled`, ...). Callers catch `ClaudeError` and show `.user_message`. A `max_tokens` stop is `Truncated`
  (a cut-off answer or half a tool input is never returned as if it were whole); a refusal is `Refused`.
- **Cost visibility:** `Response.usage` (and a running total on the client) with an estimated price from the
  model table. The user pays, so callers can show what a request cost.
- **Tools** are client-side `Tool(name, description, input_schema, handler)`. The loop is written by hand (not the
  SDK's beta tool runner) so it can be cancelled, can ask the user, and can report progress. `strict` is opt-in
  per tool (it requires a closed schema). Eager input streaming is NOT used: it removes the server's schema
  validation and obliges the client to validate partial JSON; these tools take small inputs, so it buys nothing.
  A tool that raises is reported to the model as an error result; the loop goes on.
- **Structured output** is a raw JSON Schema (`output_config.format`); the reply is parsed into `Response.data`.
  No Pydantic dependency.

## The rule that shapes `Conversation`: append-only

On Claude Opus 5.5 (and Fable 5.1 / Sonnet 5.5) a thinking block is bound to the conversation that produced it.
Changing the system prompt, the tool list, the model, or any earlier message and replaying the thinking blocks is
a 400 ("bound to a different conversation"), and a changed prefix also throws away the prompt cache. So:

- a `Conversation` fixes its **model, tools and system prompt when it is created** and never edits them;
- history only ever grows; assistant content is stored exactly as received (thinking blocks included);
- outside knowledge (`ContextProvider`s) is rendered **once, when the conversation starts**, into the frozen
  system prompt;
- anything learned *during* the conversation -- a decision the user just made, new facts -- is appended as a
  `role: "system"` **note** after the user's next message (`Conversation.note()`), which does not disturb the
  prefix. (Supported on Opus 5.5 / Fable 5.1 / Sonnet 5.5 with no beta header.)
- there is deliberately no "edit message" or "replace system prompt" API. A caller that wants different
  instructions starts a new conversation.

## Using it

```python
from harness_designer import claude

client = claude.ClaudeClient()                       # key from the credential store, settings from ClaudeSettings

# one question, one answer
reply = client.ask('Write a regex for AWG sizes.', system='You write Python.')
print(reply.text, reply.usage.estimated_cost)

# a conversation with a tool and cancellation
tool = claude.Tool('check_layout', 'Run the packing solver on a layout.', schema, handler=run_solver)
chat = client.conversation(system=RULES, tools=[tool], context=[my_provider])
reply = chat.send('Arrange these 19 wires.', on_text=show, cancel=token)

# structured answer
reply = client.ask('Classify this wire.', output_schema=SCHEMA)
reply.data['layer']
```

From the GUI use `claude.qt.ClaudeJob` (signals: `textDelta`, `toolCalled`, `finished`, `failed`, `cancelled`) so the
GUI thread never waits on the network. A tool that needs the user (a question dialog) calls
`claude.qt.call_in_gui(fn)` from its handler; it blocks the worker thread, not the GUI.

## Concentric twisting: what is built, what is not

Built here (seams only):

- `ContextProvider.blocks(topic)` -> `ContextBlock`s that are rendered into a conversation's frozen system prompt.
  This is where saved user decisions will come in.
- Tools that can block on the user (`call_in_gui`), so "ask the user which wire goes in the centre" is a tool the
  model calls and the answer returns as the tool result.
- `Conversation.note()` for decisions made mid-conversation.

Not built (user: "we aren't doing that at the moment"): the decision log itself and the concentric feature. Notes
for whoever builds it, so the intent survives:

1. **What "learn" means.** Not training. Each time the feature has to ask the user a question about where wires
   sit in a bundle, the situation, the options offered, the answer (and any reason the user typed) are stored. The
   next time, the relevant past decisions are put in front of Claude as context. A `ContextProvider` does that
   retrieval; the feature decides what "relevant" means (wire count, sizes, types, the question asked).
2. **Division of labour** (MEMORY.md, "Wire bundle packing requirements"): the numeric packing solver does the
   geometry; Claude is the judgement layer that chooses between arrangements, explains the trade-offs, and calls
   the solver as a tool to check what it proposes. Claude is not asked to compute coordinates.
3. **Visible and editable.** The user must be able to see what has been learned, correct it, and delete it; a
   preference that is silently wrong forever is worse than none. Plan a small viewer next to the log.
4. **Open questions** for that day: where the log lives (user-level database so it follows the person, or the
   project database so it follows the harness -- probably both, with project overriding user); how a decision is
   keyed so "similar situation" can be found; how many past decisions fit in the prompt (and a cap); whether to
   let Claude call a `recall_decisions` tool instead of always injecting; how to tell whether the learning helps
   (a few recorded cases replayed with and without it).
5. Decisions made *before* a conversation go in the frozen system prompt; decisions made *during* it go in as
   notes. Never rewrite the system prompt mid-conversation (see the append-only rule).

## Found while building it

- A **streamed** final message has no `_request_id` (only non-streamed responses do); the id is read from the
  stream's `request-id` response header and returned with the message.
- The SDK's **first import takes about 3 seconds**. On the worker thread that does not freeze the GUI, but the
  first answer would start late, so `claude.warm_up()` imports it in the background: call it when an assistant
  panel or the settings dialog is opened.
- The SDK's beta stream accepts the refusal-fallback parameters and parses `fallback` content blocks and
  `usage.iterations` (verified against the fake server; the live API is still unverified). When a fallback model
  finished a turn, the cleaned content (`wire.echo_content`) is what is kept and sent back.
- Code that waits with `QTest.qWait` starves other Python threads (it does not release the GIL), so a worker doing
  its first SDK import never finishes; wait with `processEvents()` + `time.sleep()`. The real event loop releases
  the GIL while idle, so the app is not affected.
- The real credential store on this machine is Windows Credential Manager (it holds the user's actual key). Anything
  that exercises the key store must inject an in-memory backend (`ApiKeyStore(backend=...)` exists for that).

## Testing

There are no unit tests (user, 2026-10-17). While `tests/claude/` existed (it is in git history) it ran the real SDK
against a local fake of the Messages API (`fake_api.py`): scripted SSE streams and error responses, every request
recorded so what was sent (model, effort, system, tools, betas, cache control, message history) could be asserted.
What that could not show is that the live API accepts the request shapes; the first real call from the app is the
first real proof. A manual smoke test would be `ClaudeClient().ask('Say OK.', max_tokens=512)` with a real key
stored.
