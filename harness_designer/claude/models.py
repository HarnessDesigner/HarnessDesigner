# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Claude models the application offers, and what each one supports.

Prices are US dollars per million tokens, from Anthropic's published rates
at the time of writing. They are only used for the cost *estimate* shown to
the user; a wrong price here changes a number on screen, never a request.
"""

from dataclasses import dataclass

from .. import check_types as _check_types

DEFAULT_MODEL = 'claude-opus-5-5'

# output_config.effort values, lowest to highest.
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
DEFAULT_EFFORT = 'medium'


@dataclass(frozen=True)
class ModelInfo:
    """One model.

    :ivar id: The exact API model id (never with a date suffix).
    :ivar name: What the user sees.
    :ivar input_price: Dollars per million input tokens.
    :ivar output_price: Dollars per million output tokens.
    :ivar cache_read_price: Dollars per million cached input tokens read.
    :ivar supports_fallback: Accepts the server-side refusal fallback. (Haiku
        5.5 has none: sending the parameter is a 400.)
    :ivar note: One line shown beside the model in the settings.
    """

    id: str
    name: str
    input_price: float
    output_price: float
    cache_read_price: float
    supports_fallback: bool
    note: str


MODELS = (
    ModelInfo('claude-opus-5-5', 'Claude Opus 5.5', 4.00, 20.00, 0.20, True,
              'The default: best balance of capability and cost for reasoning and code.'),
    ModelInfo('claude-sonnet-5-5', 'Claude Sonnet 5.5', 2.00, 10.00, 0.20, True,
              'Faster and about half the price; good for routine code generation.'),
    ModelInfo('claude-haiku-5-5', 'Claude Haiku 5.5', 0.10, 0.50, 0.01, False,
              'Cheapest and quickest; for simple, high-volume requests.'),
    ModelInfo('claude-fable-5-1', 'Claude Fable 5.1', 10.00, 50.00, 0.25, True,
              'Most capable and most expensive; needs 30-day data retention on the account.'),
)

# Writing the cache-write price: Anthropic charges 1.25x the input price to
# write a cached prefix (5 minute lifetime).
CACHE_WRITE_FACTOR = 1.25


@_check_types.do
def model_info(model_id: str) -> ModelInfo | None:
    """The :class:`ModelInfo` for *model_id*, or ``None`` for a model this
    package does not know (it can still be used; it just gets no price
    estimate and no refusal fallback)."""
    for info in MODELS:
        if info.id == model_id:
            return info

    return None
