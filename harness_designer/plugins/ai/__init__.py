# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The provider-agnostic AI plugin contract -- Job/Session/AIBase.

    from harness_designer.plugins import ai

    class MyJob(ai.Job):
        def on_complete(self, result):
            ...

        def on_error(self, error):
            ...

See AI_PLUGIN_DESIGN.md (this folder) for how it works and why. Importing
this package imports no provider SDK and no Qt; a Job subclass that needs
the GUI thread uses ``call_after``, forwarding to ``app.CallAfter``.
"""

from . import base as _base
from . import cancel as _cancel
from . import job as _job
from . import session as _session


AIBase = _base.AIBase

Job = _job.Job

Session = _session.Session

CancelToken = _cancel.CancelToken
Cancelled = _cancel.Cancelled
REASON_CLOSE = _cancel.REASON_CLOSE
REASON_STEER = _cancel.REASON_STEER


del _base, _cancel, _job, _session
