# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The application's one doorway to the Claude API.

    from harness_designer import claude

    client = claude.ClaudeClient()
    reply = client.ask('Write a regex for AWG sizes.')

See CLAUDE_API_DESIGN.md (repo root) for how it works and why. Importing
this package imports neither Qt nor the Anthropic SDK; the Qt helpers are in
``harness_designer.claude.qt``.
"""

from . import cancel as _cancel
from . import client as _client
from . import context as _context
from . import conversation as _conversation
from . import errors as _errors
from . import keys as _keys
from . import messages as _messages
from . import models as _models
from . import settings as _settings


ClaudeClient = _client.ClaudeClient
warm_up = _client.warm_up
Conversation = _conversation.Conversation

Tool = _messages.Tool
Response = _messages.Response
Usage = _messages.Usage

ContextProvider = _context.ContextProvider
ContextBlock = _context.ContextBlock
StaticContext = _context.StaticContext

CancelToken = _cancel.CancelToken
ApiKeyStore = _keys.ApiKeyStore
MemoryKeyring = _keys.MemoryKeyring

ClaudeSettings = _settings.ClaudeSettings
SettingsBackend = _settings.SettingsBackend
current_settings = _settings.current
update_settings = _settings.update
set_settings_backend = _settings.set_backend

MODELS = _models.MODELS
EFFORTS = _models.EFFORTS
DEFAULT_MODEL = _models.DEFAULT_MODEL
model_info = _models.model_info

ClaudeError = _errors.ClaudeError
NoApiKeyError = _errors.NoApiKeyError
KeyStoreError = _errors.KeyStoreError
AuthenticationFailed = _errors.AuthenticationFailed
RateLimited = _errors.RateLimited
ServiceUnavailable = _errors.ServiceUnavailable
BadRequest = _errors.BadRequest
BetaNotAvailable = _errors.BetaNotAvailable
Refused = _errors.Refused
Truncated = _errors.Truncated
Cancelled = _errors.Cancelled
InvalidStructuredReply = _errors.InvalidStructuredReply
ToolLoopLimit = _errors.ToolLoopLimit


del _cancel, _client, _context, _conversation, _errors, _keys, _messages, _models, _settings
