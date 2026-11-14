# harness_designer/plugins/plugins/claude_ai/conversation.py

Conversation — APPEND-ONLY: model, tools, and system prompt are fixed at creation; history only ever grows.

Cold path (286 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
