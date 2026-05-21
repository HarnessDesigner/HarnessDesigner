import sys

if sys.platform.startswith('win'):
    from . import win as module

run = module.run
