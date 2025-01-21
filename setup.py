#!/usr/bin/env python

import os
import platform
from sys import platform as sys_platform
from setuptools import setup
from setuptools.command.install import install
from distutils.command.build import build
from subprocess import call
from multiprocessing import cpu_count

BASEPATH = os.path.dirname(os.path.abspath(__file__))

class DX7Build(build):
    def run(self):
        build.run(self)  # Run the original build code

        # Detect platform
        system = platform.system().lower()
        build_path = os.path.abspath(self.build_temp)
        
        cmd = ['make', 'OUT=' + build_path]

        # Add platform-specific options
        if system == 'darwin':  # macOS
            cmd.append('PLATFORM=macos')
        elif system == 'windows':  # Windows
            cmd.append('PLATFORM=windows')
        else:  # Default to Linux
            cmd.append('PLATFORM=linux')

        try:
            cmd.append('-j%d' % cpu_count())
        except NotImplementedError:
            print('Unable to determine number of CPUs. Using single-threaded make.')

        targets = ['all']
        cmd.extend(targets)

        # Adjust target files based on platform
        target_files = {
            'linux': os.path.join(BASEPATH, 'dxcore.so'),
            'darwin': os.path.join(BASEPATH, 'dxcore.dylib'),
            'windows': os.path.join(BASEPATH, 'dxcore.dll')
        }
        target_file = target_files.get(system, 'dxcore.so')  # Default to .so for unknown systems

        def compile():
            call(cmd, cwd=BASEPATH)

        self.execute(compile, [], 'Compiling dx7pytorch')

        # Copy the resulting files to the build directory
        self.mkpath(self.build_lib)
        if not self.dry_run:
            self.copy_file(target_file, self.build_lib)


class DX7Install(install):
    def initialize_options(self):
        install.initialize_options(self)
        self.build_scripts = None

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        install.run(self)  # Run the original install code
        self.copy_tree(self.build_lib, self.install_lib)  # Copy the built libraries


setup(
    name='dx7pytorch',
    package_dir={
        'dx7pytorch': 'dx7pytorch',
        'dx7pytorch.dxsynth': 'dx7pytorch/dxsynth',
        'dx7pytorch.dxdataset': 'dx7pytorch/dxdataset',
    },
    packages=['dx7pytorch', 'dx7pytorch.dxsynth', 'dx7pytorch.dxdataset'],
    version='0.1',
    description='DX7 FM Synthesizer for deep learning in PyTorch.',
    author='Franco Caspe',
    author_email='francocaspe@hotmail.com',
    maintainer='Franco Caspe',
    maintainer_email='francocaspe@hotmail.com',
    license='GPLv2',
    url='',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: C++',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Information Analysis',
    ],
    install_requires=['numpy', 'torch'],
    cmdclass={
        'build': DX7Build,
        'install': DX7Install,
    }
)
