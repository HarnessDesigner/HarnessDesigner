# harness_designer/plugins/ai/__init__.py

Facade for the provider-agnostic AI contract (`AIBase`, `Job`, `Session`, `CancelToken`). It imports no provider SDK and no Qt, so loading it is cheap; the `anthropic` package is only pulled in by the Claude plugin's client, when it is used. Keep it that way: importing `anthropic` costs hundreds of milliseconds.
