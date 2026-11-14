# harness_designer/scraping/script_builder.py

snippet_block() (turns warnings into # NOTE: comments) and import_text()/import_position() (where new imports go in generated code, never duplicated).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `snippet_block` (lines 23-37, depth 2), `_skip_header` (lines 105-133, depth 2).

Status: static read of the code only. Nothing here has been profiled.
