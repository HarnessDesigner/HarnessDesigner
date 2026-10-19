# AI plugin design

`harness_designer/plugins/ai/` is the provider-agnostic contract that any AI backend (Claude,
Google AI/Gemini, ...) plugs into. The app and its two current AI consumers (the scraper
assistant, concentric-twisting bundle organization) talk only to this contract, never to a
specific provider's SDK — the same rule `CLAUDE_API_DESIGN.md` already applies one level down
("nothing outside `claude/` imports `anthropic`") extended one level up: nothing outside a
provider's own plugin module imports that provider's SDK. Add new decisions about this contract
HERE, not in `plugins/PLUGIN_DESIGN.md` (the generic registration mechanism this builds on) and
not in `MEMORY.md`.

Status (2026-10-18): contract only, designed in conversation, not yet implemented against a real
provider. `harness_designer/claude/` (see `CLAUDE_API_DESIGN.md`) is the first real AI backend and
predates this contract; it is NOT yet wrapped as an `AIBase` plugin. That migration — a thin
`ClaudePlugin(AIBase)` adapter over the existing `ClaudeClient`/`Conversation`/`CancelToken` — is
future work, done once this contract has been exercised by at least one concrete plugin. A Google
AI (Gemini) plugin is the second intended backend: free tier, user supplies their own API key same
as Claude, request-rate-capped (RPM/TPM/RPD) rather than concurrency-capped.

## Why a second layer above `claude/`

The user wants more than one AI backend available (Claude today, Google AI next, possibly more
later), selectable per-user because Google AI's free tier means "no separate subscription cost"
matters to some users while others will happily keep paying for Claude. The app's two call sites
(scraper assistant, concentric twisting) should not need to know or care which backend is active —
they talk to `Job`/`Session`, and whichever `AIBase` subclass is the active plugin does the actual
work.

## Vocabulary

- **Session** — one open-ended activity, created when the user starts a new "thing wanting to be
  done" (open the assistant panel, start organizing a bundle) and closed when the user closes that
  AI dialog. Holds the full conversation history for everything done in it. Named from its first
  message (the AI generates the name, mirroring how Claude Code names its own sessions) — naming
  mechanism not yet built. Maps directly onto each provider's own native concept: `claude.
  Conversation` today, Google AI's `ChatSession` (`model.start_chat()`) for a Gemini plugin —
  `Session` is this app's shared name for that same thing, not a new concept either provider
  invented for.
- **Job** — one instruction the user hands to a Session. May take several actual API round-trips
  under the hood (tool-call loops), but is one unit of work from the app's point of view, ending in
  exactly one of two outcomes: **complete** or **error**. A Session can run many Jobs over its
  life; finishing one does not close the Session — the user can immediately hand it another,
  related Job.
- **Steering** — anything the user sends that continues the *current* Job rather than starting a
  new one. Two cases, both folding into the same Job, neither ever creating a new one:
  1. Answering a tool's request for input (see "Asking the user" below).
  2. "Send now" — interrupting a Job that is actively working (not waiting on the user) to deliver
     a new message immediately rather than queuing it. This cancels whatever call is currently in
     flight and re-sends with the new message folded into history; the model decides for itself,
     with full context of what it was already doing, whether to keep pursuing the original plan or
     change course. The app never tries to classify the message to decide — that decision is the
     model's, informed by context, not the plumbing's, inferred from text.
- **A genuinely new, unrelated Job** is only ever created by an explicit, distinct user action
  (a different control than "send"/"Send now", or starting a fresh Session) — never inferred from
  what the user typed. This was a deliberate choice over the alternative (a dedicated tool the
  model calls to signal "this is a pivot, not a continuation") because it keeps the boundary
  explicit instead of guessed, consistent with how "asking the user" below is also tool-call-driven
  rather than text-sniffed.

## Asking the user: not a tracked state, a blocking call

Earlier drafts of this design treated "the AI needs to ask the user something" as a third Job
outcome (`complete` / `error` / `request_input`) that the app would need to track and resume.
Building this doc against what `harness_designer/claude/qt/gui_call.py` already does for the
scraper assistant showed that's unnecessary: `call_in_gui(fn, cancel)` already lets a tool handler
block its own worker thread (not the GUI thread) while a modal question is answered, then returns
the answer and the tool loop just continues. Nothing about that needs to surface to the Job's
caller as a distinct state — the Job is still "running" the whole time, from the app's point of
view. The generic contract formalizes this instead of re-inventing it: any plugin's tool handler
that needs to ask the user calls the Session's equivalent of `call_in_gui` and blocks until
answered. `Job.on_progress`/`Job.on_usage` (see below) are how the app sees that something is
still happening in the meantime.

## Threading and cancellation

- **One plain Python `threading.Thread` per Session**, spun up by `AIBase` when the Session is
  created, joined/torn down when the Session closes. Not a `QThread` — nothing under
  `plugins/ai/` imports Qt, matching `claude/`'s own "no Qt below `qt/`" rule, just one level up.
  A concrete plugin's execution code (HTTP calls, tool loops) runs entirely on that thread.
- **Cooperative cancellation**, the same shape as `claude/cancel.py`'s existing `CancelToken`
  (`is_cancelled()` / `cancel()` / `raise_if_cancelled()`) generalized to this layer. Plain Python
  threads cannot be safely killed from outside, so this is the only mechanism — a tool with a real
  side effect must checkpoint (check-then-act) rather than assume it will run to completion.
- `cancel()` carries a reason so the Session can tell "Send now" (steer: discard the in-flight
  call, immediately re-send with the new message) apart from closing the dialog (teardown: stop
  the thread, do not re-send). A `Job`'s `on_error` must never fire for a steering cancel — only
  for a genuine failure or a close-triggered teardown the caller actually needs to know about.
- **`CallAfter`/`CallAfterStart`** (`app.py`) is the only sanctioned way anything on the Session
  thread touches a Qt widget, and it is always the `Job` subclass's own call, never something the
  base classes or the plugin do on the subclass's behalf. Everything else a Job's callback does
  (parsing a response, writing to a DB, computing a diff) can and should run inline on the worker
  thread rather than being forced onto the GUI thread.

## The `Job` contract

A `Job` is created and subclassed by the app's call site (the assistant panel, the bundle
organizer) — never by a plugin. A plugin reads request data off the `Job` it was handed and calls
back into it; it never knows what the overridden methods do, and today that's exactly two call
sites, though more may exist later.

- Request data (instruction text, tools, context, model/effort hints) — provider-agnostic shape,
  still being settled; `claude.Tool(name, description, input_schema, handler)` is already
  provider-agnostic-looking (JSON Schema is universal across Claude's tool-use and Gemini's
  function-calling) and is a reasonable starting point rather than inventing a parallel shape.
- `on_progress(current, total)` / `on_usage(tokens_used, tokens_limit)` — called zero or more
  times while the Job runs; this is also how a shared status-bar display gets its numbers (see
  "Status display" below). Default implementation does nothing; a subclass that cares overrides
  it and is responsible for any `CallAfter` it needs.
- `on_complete(result)` / `on_error(error)` — called exactly once, terminal. Not implemented by the
  base class (`NotImplementedError`) — every real Job subclass must decide what "done" means for
  it.
- A `call_after(fn, *args)` convenience forwarding to `app.CallAfter`, so a subclass doesn't need
  its own import of `app` for the one GUI hop it needs.

## The `AIBase` contract

`AIBase(Plugin)` (registered with `PLUGIN_TYPE_AI`, see `plugins/PLUGIN_DESIGN.md`) is what a
concrete provider (Claude, Google AI) subclasses. It owns:

- Session creation and the thread lifecycle behind it.
- `submit(session, job)` — the only entry point a call site uses; the plugin never sees a `Job`
  any other way.
- The `CancelToken`-equivalent per Session, and translating "Send now"/close into the right
  cancel reason.
- Rate/concurrency policy is the concrete plugin's own business, not the base class's — Claude can
  run several Jobs in parallel; a free-tier Google AI plugin should serialize its own requests
  internally (one in flight, queue the rest) to respect RPM/TPM/RPD, entirely invisible to the
  call site either way.

What a concrete plugin must implement is the actual per-provider execution: given a `Session` and
a `Job`, make the real API call(s), run any tool loop, report progress/usage, and call exactly one
of `job.on_complete(...)` / `job.on_error(...)` when done.

## Status display

Multiple Jobs (today: at most the two call sites; more could exist later) may be running
concurrently and reporting progress/usage to one shared status-bar area. Because `CallAfter` posts
onto the main thread's queue, concurrent updates from different Session threads are naturally
serialized with no locking needed — the display just flips between whichever Job last reported.
Open question, not yet settled: whether that shared area needs a Job/Session label alongside the
numbers so a user watching it isn't confused by which Job is currently showing, or whether the
simple flip is enough as built. Decide this once the status-bar widget itself is being built, not
before.

## Open questions

- Exact provider-agnostic request-data shape for `Job` (see above).
- Whether a single Session can ever have more than one Job genuinely in flight at once, or whether
  "multiple Jobs running" only ever means multiple different Sessions. Current assumption: at most
  one active Job per Session; steering always folds into it rather than running alongside it.
- Session/Job auto-naming from the first message — mechanism (which model call, when, cost) not
  decided.
- Where the settings-panel base class (in progress separately, see `plugins/PLUGIN_DESIGN.md`)
  intersects with an AI plugin's own settings (API key entry currently lives in
  `claude/qt/key_dialog.py`; a generic version needs the same scoped-config-database access every
  other plugin's settings page gets).
