# harness_designer/__init__.py

Entry function only (`main`, builds `app.App(args)` and runs `MainLoop`). Importing the package has side effects that run once at startup (`Config.open()` in `config.py`, the logger singleton), so import time counts toward launch time. The `from . import app` import is done inside the function so that a plain `import harness_designer` (a plugin, a tool) does not pull the whole UI in. Keep it that way.
