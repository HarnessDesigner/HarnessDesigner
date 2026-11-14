# harness_designer/ui/prop_ctrls/bitmap_combobox_prop.py

BitmapComboBoxProperty -- a combobox property whose entries also carry an icon. No callers. Known, not fixed: it commits on every keystroke (currentTextChanged), and its SetItems/Clear use Qt's clear()/addItems(), so the completer gets no choices and the widget's own GetItems disagrees with what was set.

Cold path (158 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
