
MODULE_NAMES = '''\
ipython_pygments_lexers
trianglesolver
typing_extensions
decorator
six
pyassimp
harness_designer
lib3mf
pyassimp
OpenGL_accelerate
OpenGL
pymupdf
wx
mysql
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
ifcopenshell
svgwrite
svgpathtools
IPython
matplotlib
vtk
vtkmodules
cadquery_ocp
ocpsvg
build123d
harness_designer'''


def get_modules():
    res = []
    for name in MODULE_NAMES.split('\n'):
        mod = __import__(name)
        if mod.__file__ is None:
            cmd = [f'--hidden-import={name}']
        elif '__init__' in mod.__file__:
            cmd = [f'--collect-all={name}']
        else:
            cmd = [f'--hidden-import={name}']

        res.extend(cmd)

    return res
