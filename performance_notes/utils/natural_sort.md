# harness_designer/utils/natural_sort.py

## Line 8-22 (`natural_sort_key`) — a regex split per name
Splits each name into digit and text chunks with a precompiled pattern. Called once per name when a list is sorted, so a sort of N names costs N splits. Fine for list sizes in this app.
