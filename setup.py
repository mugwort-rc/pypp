#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name="pypp",
    version="1.0.0",
    description="libclang boost.python generator",
    url="https://github.com/mugwort-rc/pypp",
    license="GPL3",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPL",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Software Development :: Compilers"
    ],
    keywords=["clang", "libclang", "python3", "boost"],
    author="mugwort_rc",
    author_email="mugwort [dot] rc [at] gmail [dot] com",
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
)
