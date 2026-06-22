# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

MODULE_NAMES = '''\
ipython_pygments_lexers
trianglesolver
typing_extensions
decorator
six
harness_designer
lib3mf
pyassimp
OpenGL_accelerate
OpenGL
numpy
PIL
pyparsing
packaging
kiwisolver
fontTools
cycler
svgelements
cadquery_ocp_proxy
mpmath
webcolors
isodate
lark
mdurl
pygments
traitlets
pure_eval
asttokens
executing
wcwidth
parso
colorama
anytree
ezdxf
jedi
matplotlib_inline
prompt_toolkit
stack_data
contourpy
scipy
sympy
shapely
markdown_it
cv2
pyfqmr
dateutil
ocp_gordon
rich
requests
meshio
svgwrite
svgpathtools
IPython
matplotlib
vtk
vtkmodules
cadquery_ocp
ocpsvg
build123d'''


def get_modules():
    res = []
    for name in MODULE_NAMES.split('\n'):
        try:
            mod = __import__(name)
        except ModuleNotFoundError:
            print('MODULE NOT FOUND:', name)
            continue

        if mod.__file__ is None:
            cmd = [f'--hidden-import={name}']
        elif '__init__' in mod.__file__:
            cmd = [f'--collect-all={name}']
        else:
            cmd = [f'--hidden-import={name}']

        res.extend(cmd)

    return res
