# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Qt side of the Claude package: run calls on a thread, let a tool ask
the user a question, and the shared key / settings dialog.

Import this only from code that already uses Qt. The dialog is not imported
here (it pulls in the application's dialog machinery); use
``from harness_designer.claude.qt import key_dialog`` when it is needed.
"""

from . import gui_call as _gui_call
from . import job as _job


ClaudeJob = _job.ClaudeJob
call_in_gui = _gui_call.call_in_gui
install = _gui_call.install


del _gui_call, _job
