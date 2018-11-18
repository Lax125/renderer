#!/usr/bin/env python
'''
This script imports all external modules
and defines a few constants for other scripts.
'''

def debug(msg):
    with open("debug.log", 'a') as f:
        f.write(msg+'\n')
import traceback # for debugging
import sys, os # for path operations
import shutil # for saving/loading
import shlex # for parsing homemade *.dat files
import zipfile # for saving/loading
import ctypes # for making OpenGL buffer objects
import numpy as np # for matrix and array math
import copy # for pythonic use of __copy__ and __deepcopy__
from math import sin, cos, tan, atan, atan2, pi, tau, degrees, radians, hypot, floor, ceil, sqrt # staple math functions
from itertools import chain # for chaining generators
from collections import defaultdict as ddict
from typing import Iterable # for type hints

# for logging
import time
from time import gmtime, strftime
import logging

# graphics library
import OpenGL
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLU import *
from OpenGL.GLUT import *

# Image handling and GUI
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import *

# constants
MAX_LIGHTS = 500
APPNAME = "ZEdit"
APPDATA_FOLDERNAME = "ZEdit"
