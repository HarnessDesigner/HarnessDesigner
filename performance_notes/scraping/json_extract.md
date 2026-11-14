# harness_designer/scraping/json_extract.py

JSON-path clicks → extraction code (generate_extraction_code, with every_item= for "this field from every element", plus suggest_name, snippet_for); describe() asks Claude (through ../plugins/plugins/claude_ai/, formerly ../claude/ before that package's relocation under plugins/plugins/) to describe a JSON structure in words.

Nested loops (cost grows with the product of the sizes; check the sizes are small): `_shared_array` (lines 202-220, depth 2).

Status: static read of the code only. Nothing here has been profiled.
