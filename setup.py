from setuptools import find_packages, setup
poop 
setup(
    name='py-stl',
    version='0.2',
    description='TODO',
    url='http://github.com/mvcisback/py-stl',
    author='Marcell Vazquez-Chanlatte',
    author_email='marcell.vc@eecs.berkeley.edu',
    license='MIT',
    install_requires=[
        'funcy',
        'parsimonious',
        'lenses',
        'sympy',
        'bitarray',
        'traces',
    ],
    packages=find_packages(),
)
