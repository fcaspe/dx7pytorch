'''
setup.py

Nice info extracted from:
    https://godatadriven.com/blog/a-practical-guide-to-using-setup-py/
    https://stackoverflow.com/questions/45347685/run-makefile-on-pip-install
'''
#!/usr/bin/env python

import os
from sys import platform
from setuptools import setup
from setuptools.command.install import install
from distutils.command.build import build
from subprocess import call
from multiprocessing import cpu_count

BASEPATH = os.path.dirname(os.path.abspath(__file__))

class DX7Build(build):
    def run(self):
        # run original build code
        build.run(self)

        # build XCSoar
        build_path = os.path.abspath(self.build_temp)

        cmd = [
            'make',
            'OUT=' + build_path,
        ]

        try:
            cmd.append('-j%d' % cpu_count())
        except NotImplementedError:
            print('Unable to determine number of CPUs. Using single threaded make.')

        #options = [
        #    'DEBUG=n',
        #    'ENABLE_SDL=n',
        #]
        #cmd.extend(options)

        targets = ['all']
        cmd.extend(targets)

        target_files = [os.path.join(BASEPATH, 'dxcore.so')]

        def compile():
            call(cmd, cwd=BASEPATH)

        self.execute(compile, [], 'Compiling dx7pytorch')

        # copy resulting tool to library build folder
        self.mkpath(self.build_lib)

        if not self.dry_run:
            for target in target_files:
                self.copy_file(target, self.build_lib)


class DX7Install(install):
    def initialize_options(self):
        install.initialize_options(self)
        self.build_scripts = None

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        # run original install code
        install.run(self)

        # install executables
        self.copy_tree(self.build_lib, self.install_lib)


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='dx7pytorch',
    package_dir = {
        'dx7pytorch': 'dx7pytorch',
        'dx7pytorch.dxsynth': 'dx7pytorch/dxsynth',
        'dx7pytorch.dxdataset': 'dx7pytorch/dxdataset'},
    packages=['dx7pytorch', 'dx7pytorch.dxsynth',
              'dx7pytorch.dxdataset'],
    version='0.1',
    description='DX7 FM Synthesizer for deep learning in Pytorch.',
    author='Franco Caspe',
    author_email='francocaspe@hotmail.com',
    maintainer='Franco Caspe',
    maintainer_email='francocaspe@hotmail.com',
    license='GPLv2',
    url='',
    #long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: Unix',
        'Programming Language :: C++',
        'Topic :: Scientific/Engineering :: Information Analysis',
    ],
    install_requires=['numpy','torch'],
    cmdclass={
        'build': DX7Build,
        'install': DX7Install,
    }
)