# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# PEP 517 build backend for harness_designer — no setuptools anywhere. See
# builder/wheel_build.py for the actual wheel/sdist assembly and
# builder/compiler.py for the per-platform compile/link recipes.
#
# Toggle: pip install . --config-settings cythonize=false builds a fast,
# uncompiled dev wheel (plain .py for the auto-discovered modules; bvh/culling
# always compile — they have no plain-Python fallback).

from . import wheel_build


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_sdist(config_settings=None):
    return []


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    return wheel_build.build_wheel(wheel_directory, config_settings)


def build_sdist(sdist_directory, config_settings=None):
    return wheel_build.build_sdist(sdist_directory, config_settings)
