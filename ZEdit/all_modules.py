#!/usr/bin/env python
def debug(msg):
    with open("debug.log", 'a') as f:
        f.write(msg+'\n')
import traceback
import sys, os
import shutil
import shlex
import zipfile
import ctypes
import numpy as np
import copy
from math import sin, cos, tan, atan, atan2, pi, tau, degrees, radians, hypot, floor, ceil, sqrt
from itertools import chain
from collections import defaultdict as ddict
from typing import Iterable

import time
from time import gmtime, strftime
import logging

import OpenGL
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLU import *
from OpenGL.GLUT import *

from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import *

MAX_LIGHTS = 500

APPNAME = "ZEdit"
APPDATA_FOLDERNAME = "ZEdit"
