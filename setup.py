import setuptools

with open("README.md", 'r') as fh:
  long_description = fh.read()

setuptools.setup(
  name="ZEdit",
  version="1.0.9",
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
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent",
  ],
)
