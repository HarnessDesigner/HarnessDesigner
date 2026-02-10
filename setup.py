import os
import sys


if __name__ == '__main__':
    def iter_remove(p):
        for file in os.listdir(p):
            file = os.path.join(p, file)

            if os.path.isdir(file):
                iter_remove(file)
            elif file.endswith('.c') or file.endswith('.pyd'):
                os.remove(file)
                print(file)


    iter_remove('harness_designer')

    raise RuntimeError

    if sys.platform.startswith('win'):
        import pyMSVC

        environment = pyMSVC.setup_environment()
        print(environment)

    from Cython.Build import Cythonize

    def iter_file(p):
        res = []
        for file in os.listdir(p):

            if file.endswith('bak'):
                continue

            file = os.path.join(p, file)

            if os.path.isdir(file):
                res.extend(iter_file(file))
            elif file.endswith('.py') and '__init__' not in file:
                res.append(file)

        return res

    files = iter_file('harness_designer')
    for item in files:
        print(item)
    print()

    Cythonize.main(['-3', '--build', '--parallel=16', '--inplace'] + files)


    '''
    PyOpenGL-accelerate==3.1.10
    PyOpenGL==3.1.10
    PyMuPDF==1.26.7
    mysql-connector-python==9.5.0
    numpy==2.2.6
    pyparsing==3.3.1
    six==1.17.0
    pillow==12.1.0
    packaging==25.0
    kiwisolver==1.4.9
    fonttools==4.61.1
    cycler==0.12.1
    svgelements==1.9.6
    cadquery-ocp-proxy==7.9.3.0
    trianglesolver==1.2
    mpmath==1.3.0
    webcolors==24.8.0
    isodate==0.7.2
    lark==1.3.1
    typing_extensions==4.15.0
    mdurl==0.1.2
    Pygments==2.19.2
    lib3mf==2.4.1.post1
    traitlets==5.14.3
    pure_eval==0.2.3
    asttokens==3.0.1
    executing==2.2.1
    wcwidth==0.2.14
    parso==0.8.5
    decorator==5.2.1
    colorama==0.4.6
    anytree==2.13.0
    ezdxf==1.4.3
    ipython_pygments_lexers==1.1.1
    jedi==0.19.2
    matplotlib-inline==0.2.1
    prompt_toolkit==3.0.52
    stack-data==0.6.3
    contourpy==1.3.3
    scipy==1.17.0
    sympy==1.14.0
    shapely==2.1.2
    markdown-it-py==4.0.0
    wxPython==4.2.4
    opencv-python==4.12.0.88
    pyfqmr==0.5.0
    python-dateutil==2.9.0.post0
    ocp_gordon==0.2.0
    rich==14.2.0
    meshio==5.3.5
    ifcopenshell==0.8.4.post1
    svgwrite==1.4.3
    svgpathtools==1.7.2
    ipython==9.9.0
    matplotlib==3.10.8
    vtk==9.3.1
    cadquery-ocp==7.8.1.1
    ocpsvg==0.5.0
    build123d==0.10.0
    "wxOpenGL @ file:///" + os.path.join(base_path, 'libs/wxOpenGL')
    '''
