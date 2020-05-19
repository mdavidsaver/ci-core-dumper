#!/usr/bin/env python

from setuptools import setup, Extension

setup(
    name='ci-core-dumper',
    version='0.0.0',
    description="Automatic capture and analysis of core dumps during CI runs",
    license='GPL-3',
    author='Michael Davidsaver',
    author_email='mdavidsaver@gmail.com',
    python_requires='>=2.7',
    packages=['ci_core_dumper'],
    ext_modules = [
        Extension('ci_core_dumper._crash', sources=['ci_core_dumper/crash.c']),
    ],
    install_requires = [],
    entry_points = {
        'console_scripts':['ci-core-dumper=ci_core_dumper:main'],
    },
    zip_safe = False,
)
