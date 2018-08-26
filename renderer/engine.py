#!usr/bin/python
'''
engine.py
describes 3-D scenes and it's rendering process
with the help of OpenGL
'''

import logging
from rotpoint import Point, Rot
import numpy as np
import OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('engine')

class Camera:
  '''Describes a camera in 3-D position and rotation'''
  
  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), fovy=60, zRange=(1, 10000)):
    '''Initialise a Camera object in a position and rotation'''
    self.pos = pos
    self.rot = rot
    self.fovy = fovy # field of view in degrees in y axis
    self.zRange = zRange # visible slice of the scene

class Model:
  '''Describes polyhedron-like 3-D model in a position and orientation'''
  
  def __init__(self, objfn, mtlfn, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), scale=1.0):
    '''Initialise 3-D model from obj and mtl files with position pos, rotation rot, and scale scale'''
    self.objfn = objfn
    self.mtlfn = mtlfn
    self.pos = pos
    self.rot = rot
    self.scale = scale
    self._load()

  def _load(self):
    pass # TODO: load with OpenGL

  def _update(self):
    pass # TODO: position, orient, and scale with OpenGL


class Scene:
  '''Defines a list of Model objects and background'''
  def __init__(self, bg_mtlfn, models=set()):
    self.bg_mtlfn = bgmtlfn
    self.models = models

  
