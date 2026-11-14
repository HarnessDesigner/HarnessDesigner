# harness_designer/scraping/assistant.py

The scraper assistant's logic — SYSTEM_PROMPT; AssistantContext (what the open page offers; ScraperInspector implements it); list_items()/assemble() (which context pieces can be sent and the exact message built from them, with a per-piece byte budget and a total cap); request_summary() (secret headers omitted, JSON digested for display); extract_code_blocks()/proposed_script()/unified_diff() for parsing Claude's reply.

Cold path (468 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
