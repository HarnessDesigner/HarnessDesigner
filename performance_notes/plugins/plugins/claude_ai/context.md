# harness_designer/plugins/plugins/claude_ai/context.py

ContextProvider/ContextBlock/StaticContext — how outside knowledge gets rendered once into a conversation's frozen system prompt (the seam for what a future feature, e.g. concentric twisting, would feed the model).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `compose_system` (lines 68-90, depth 2).

Status: static read of the code only. Nothing here has been profiled.
