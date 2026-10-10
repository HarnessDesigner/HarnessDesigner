# harness_designer/database/global_db/transition_branch.py

SQL calls in this module (AST count): 22.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `TransitionBranch.transition_id`: cached after first read.
- `TransitionBranch.idx`: cached after first read.
- `TransitionBranch.bulb_offset`: cached after first read.
- `TransitionBranch.bulb_length`: cached after first read.
- `TransitionBranch.min_dia`: cached after first read.
- `TransitionBranch.max_dia`: cached after first read.
- `TransitionBranch.length`: cached after first read.
- `TransitionBranch.angle`: cached after first read.
- `TransitionBranch.offset`: cached after first read.
- `TransitionBranch.flange_height`: cached after first read.
- `TransitionBranch.flange_width`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
