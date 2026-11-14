# harness_designer/plugins/plugins/claude_ai/client.py

ClaudeClient — owns the SDK client built from the stored key. ask() (one question), conversation() (start a Conversation), check_connection(), derive(). Always streams (nothing times out; calls can be cancelled); translates SDK errors into this package's own ClaudeError subclasses; keeps a running usage total. warm_up() pre-imports the SDK on a background thread (the first import takes ~3s).

Starts threads or workers at line 40 (`Thread`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).

Status: static read of the code only. Nothing here has been profiled.
