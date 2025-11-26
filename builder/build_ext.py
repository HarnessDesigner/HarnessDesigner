import os
import sys

from Cython.Build.Dependencies import cythonize
from setuptools.command.build_ext import build_ext as _build_ext


class build_ext(_build_ext):

    def finalize_options(self):
        build = self.distribution.get_command_obj('build')  # NOQA
        build.ensure_finalized()

        self.link_shared_object = self.static_object
        _build_ext.libtype = 'static'
        _build_ext.use_stubs = False

        self.parallel = False

        language_level = '3str'

        nthreads = os.cpu_count() - 1
        if nthreads == 0:
            nthreads = None

        self.distribution.ext_modules[:] = cythonize(self.distribution.ext_modules, nthreads=nthreads,
                                                     compiler_directives=dict(language_level=language_level),
                                                     emit_linenums=True, annotate=True)

        _build_ext.finalize_options(self)

    def run(self):
        _build_ext.run(self)
        self.run_command('build_stub')

    def get_ext_fullpath(self, name):
        path = _build_ext.get_ext_fullpath(self, name)

        path, file_name = os.path.split(path)

        file_name = file_name.split('.')
        file_name = '.'.join([file_name[0], file_name[-1]])

        return os.path.join(path, file_name)

    def build_extension(self, ext):
        ext_path = self.get_ext_fullpath(ext.name)

        if 'bdist_wheel' in sys.argv:
            if not os.path.exists(ext_path):
                _build_ext.build_extension(self, ext)
        else:
            _build_ext.build_extension(self, ext)

    def shared_object(self, objects, output_libname, output_dir=None, libraries=None,
                      library_dirs=None, runtime_library_dirs=None, export_symbols=None,
                      debug=0, extra_preargs=None, extra_postargs=None, build_temp=None,
                      target_lang=None):

        self.link(self.SHARED_LIBRARY, objects, output_libname, output_dir, libraries,
                  library_dirs, runtime_library_dirs, export_symbols, debug, extra_preargs,
                  extra_postargs, build_temp, target_lang)

    def static_object(self, objects, output_libname, output_dir=None, libraries=None,
                      library_dirs=None, runtime_library_dirs=None, export_symbols=None,
                      debug=0, extra_preargs=None, extra_postargs=None, build_temp=None,
                      target_lang=None):

        # XXX we need to either disallow these attrs on Library instances,
        # or warn/abort here if set, or something...
        # libraries=None, library_dirs=None, runtime_library_dirs=None,
        # export_symbols=None, extra_preargs=None, extra_postargs=None,
        # build_temp=None

        assert output_dir is None  # distutils build_ext doesn't pass this
        output_dir, filename = os.path.split(output_libname)
        basename, ext = os.path.splitext(filename)

        if self.library_filename("x").startswith('lib'):  # NOQA
            # strip 'lib' prefix; this is kludgy if some platform uses
            # a different prefix
            basename = basename[3:]

        self.create_static_lib(objects, basename, output_dir, debug, target_lang)
