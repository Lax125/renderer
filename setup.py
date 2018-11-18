#!/usr/bin/env python
'''
setup.py
Makes a distribution for PyPi
To make distribution:
  $ python setup.py sdist bdist-wheel
'''
# the current standard for making
# distributions of Python 3.x modules
# is setuptools.
import setuptools

# load long description from README.md
with open("README.md", 'r') as fh:
  long_description = fh.read()

# make distribution for submission to PyPi
setuptools.setup(
  name="ZEdit",
  version="1.1.1",
  author="Marcus Koh",
  author_email="marcuskoh29@gmail.com",
  description="A simple 3-D rendering engine and editor",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/Lax125/renderer",
  packages=setuptools.find_packages(),
  package_data={
    "ZEdit": ["*.txt", "*.obj", "*.png", "*.qss", "*.glsl"]
  },
  python_requires=">=3",
  install_requires=["numpy",
                    "Pillow",
                    "PyOpenGL",
                    "PyQt5",
                    "PyQt5-sip"],
  classifiers=[
    "Programming Language :: Python :: 3",
    # License is GPLv3 because I'm using PyQt5
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    # All modules I are cross-compatible.
    "Operating System :: OS Independent",
  ],
)
