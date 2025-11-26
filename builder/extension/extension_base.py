import os
import setuptools.extension


class Extension(setuptools.extension.Extension):

    def __init__(
        self,
        name,
        extra_objects,
        sources,
        include_dirs,
        define_macros,
        libraries,
        extra_compile_args,
        extra_link_args=[],  # NOQA
        undef_macros=[],  # NOQA
        library_dirs=[],  # NOQA
        runtime_library_dirs=[],  # NOQA
        export_symbols=[],  # NOQA
        swig_opts=[],  # NOQA
    ):
        define_macros += [  # NOQA
            ('CYTHON_FAST_PYCCALL', 1),
            ('PY_SSIZE_T_CLEAN', 1)
        ]

        # if you look at the contents of the method you will see that it
        # sets all of the various build settings that are common to all of
        # the OS's it also handles the backend type being cpp or cython. I
        # know there was code added for pybind i have not been able to
        # locate where it is actually used.
        language = 'py'

        define_macros += [
            ('_MT', 1),
            ('_DLL', 1)
        ]

        setuptools.extension.Extension.__init__(
            self,
            name=name,
            language=language,
            extra_objects=extra_objects,
            sources=sources,
            include_dirs=include_dirs,
            define_macros=define_macros,
            libraries=libraries,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            undef_macros=undef_macros,
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
            export_symbols=export_symbols,
            swig_opts=swig_opts
        )

        # this is a nasty hack because Cython uses the __class__ of the
        # instance passed to it to create a new extension
        def __new__init__(*args, **kwargs):
            setuptools.extension.Extension.__init__(*args, **kwargs)

        self.__class__.__init__ = __new__init__
