# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""AIBase -- the base an AI backend plugin subclasses. See AI_PLUGIN_DESIGN.md.

Deliberately does NOT inherit from plugins.plugin.Plugin. That metaclass
requires a start_registration() call immediately before every class
statement that uses it -- including an abstract intermediate base, which
AIBase is, never itself registered. A concrete backend combines both:

    _plugin.start_registration(_register.RegisterPlugin(
        name='Claude', plugin_type=_register.PLUGIN_TYPE_AI, ...,
    ))


    class ClaudePlugin(_ai_base.AIBase, _plugin.Plugin):
        ...

See plugins/PLUGIN_DESIGN.md for why that ordering matters. Not changed
here -- the registration mechanism is the user's to harden, not this
package's to work around.
"""

from . import cancel as _cancel
from . import job as _job
from . import session as _session
from ... import check_types as _check_types


class AIBase:
    """Owns Session creation, its thread, and Job dispatch for one AI backend.

    A concrete backend implements :meth:`_run`: given the Session, the Job
    it was handed, and a fresh CancelToken, make the real API call(s), run
    any tool loop, call ``job.on_progress``/``job.on_usage`` as it goes, and
    call ``job.on_complete(result)`` itself when done. ``_run`` must NEVER
    call ``job.on_error`` -- let the error propagate; :meth:`_session_loop`
    is the one place that calls it, so it is only ever called once.

    When the Session is steered ("Send now") while ``_run`` is in flight,
    ``cancel.raise_if_cancelled()`` (checked wherever ``_run`` would
    otherwise block or checkpoint) raises ``Cancelled(REASON_STEER)``.
    ``_run`` is then called again for the SAME Job with a fresh token --
    it should call ``session.take_steer_message()`` near its own start each
    time, so a retry picks up the folded-in message. Rate/concurrency
    policy (e.g. a free-tier backend serializing its own requests) is the
    concrete backend's own business, not this base class's.
    """

    @_check_types.do
    def create_session(self, *, name: str = '') -> _session.Session:
        session = _session.Session(name=name)
        session._start(self._session_loop)
        return session

    @_check_types.do
    def submit(self, session: _session.Session, job: _job.Job) -> None:
        """The only entry point a call site uses; never hand a plugin a Job
        any other way."""
        session._put(job)

    @_check_types.do
    def _session_loop(self, session: _session.Session) -> None:
        while True:
            item = session._get()

            if item is None:
                return

            job = item

            while True:
                token = session.current_cancel_token()

                try:
                    self._run(session, job, token)
                except _cancel.Cancelled as error:
                    if error.reason == _cancel.REASON_STEER:
                        continue

                    job.on_error(error)
                    return
                except Exception as error:
                    job.on_error(error)

                break

    @_check_types.do
    def _run(self, session: _session.Session, job: _job.Job, cancel: _cancel.CancelToken) -> None:
        raise NotImplementedError
