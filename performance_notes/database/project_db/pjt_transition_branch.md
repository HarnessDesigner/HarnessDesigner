# harness_designer/database/project_db/pjt_transition_branch.py

SQL calls in this module (AST count): 9.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTTransitionBranch.bundle`: cached after first read.
- `PJTTransitionBranch.concentric`: cached after first read.
- `PJTTransitionBranch.transition_id`: cached after first read.
- `PJTTransitionBranch.branch_id`: cached after first read.
- `PJTTransitionBranch.diameter`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
