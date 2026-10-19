## FILES

#### __init__.py

Package init.

#### gui_call.py

`call_in_gui()` — lets a tool running on the worker thread ask the user something and block until the GUI answers, without the caller needing to manage threading itself.

#### job.py

`ClaudeJob` — one Claude call run on a background thread with results delivered back via Qt signals on the GUI thread; exposes `cancel()`.

#### key_dialog.py

`ApiKeyDialog` — the key/model/effort settings dialog, `BaseDialog`-based (see `ui/dialogs/MAP.md`'s dialog convention), with a Test button to verify the key/connection before saving.
