# harness_designer/scraping/snippets.py

Snippet + the source-text actions (split_at_every, text_after, text_before, find_position, between, regex_capture, regex_all). A selection is document[start:end]; generated code must reproduce it when run. Markers grow until their FIRST occurrence is the selected one, and the snippet warns when it had to; Names hands out collision-free variable names.

Regular-expression calls with a string pattern inside a loop at line(s) 492, 575: Python caches compiled patterns (the cache holds 512), so this is cheap unless the pattern is built per call; compile once at module level if it is hot.

Status: static read of the code only. Nothing here has been profiled.
