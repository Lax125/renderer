#!/usr/bin/python
'''
engine.py
describes 3-D scenes and it's rendering process
with the help of OpenGL
'''

# BASIC IMPORTS
import sys, os
import logging
import numpy as np
from math import sin, cos, tan, pi, tau

# FOR BUFFER CALCULATION
import OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *

# CUSTOM SCRIPTS FOR:
#   - DESCRIBING POSITIONS IN 3-D AND ROTATIONAL ORIENTATION
#   - LOADING *.obj AND IMAGE FILES AS TEXTURES
from rotpoint import Point, Rot
from objtex import Obj, load_texture

# FOR LOGGING
FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('engine')

class Camera:
  '''Describes a camera in 3-D position and rotation'''
  
  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), fovy=60, zRange=(0.1, 10000)):
    '''Initialise a Camera object in a position and rotation'''
    self.pos = pos
    self.rot = rot
    self.fovy = fovy # field of view in degrees in y axis
    self.zRange = zRange # visible slice of the scene

  def get_forward_vector(self):
    return self.rot.get_forward_vector()

  def get_upward_vector(self):
    return self.rot.get_upward_vector()

class Model:
  '''Describes polyhedron-like 3-D model in a position and orientation'''
  
  def __init__(self, obj, tex, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), scale=1.0):
    '''Initialise 3-D model from loaded obj and texture files with position pos, rotation rot, and scale scale'''
    self.obj = obj
    self.tex = tex
    self.pos = pos
    self.rot = rot
    self.scale = scale

  def from_files(objfn, texfn, *args, **kwargs):
    obj = Obj(objfn)
    tex = load_texture(texfn)
    return Model(obj, tex, *args, **kwargs)

  def __repr__(self):
    reprtuple = (repr(self.obj), repr(self.tex), repr(self.pos), repr(self.rot), repr(self.scale))
    return "Model(%s, %s, pos=%s, rot=%s, scale=%s)"%reprtuple

  def render(self):
    self.obj.render(self.tex)

  def get_forward_vector(self):
    return self.rot.get_forward_vector()

  def get_upward_vector(self):
    return self.rot.get_upward_vector()


class Scene:
  '''Defines a list of Model objects and background texture'''
  
  def __init__(self, models=set()):
    self.models = set()
    for model in models:
      self.add(model)

  def add(self, model):
    self.models.add(model)

  def remove(self, model):
    self.models.remove(model)

  def render(self, camera, aspect=1.0, mode="full"):
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)

    ## SELECT SHADER
    pass # TODO

    ## PLACEHOLDER LIGHTING
    # Ambient lighting
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])

    # Positioned light
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [2, 2, 2, 1])
    glLightfv(GL_LIGHT1, GL_POSITION, [4, 8, 1, 1])
    
    for model in self.models:
      glLoadIdentity() # loads identity matrix
      # 1 0 0 0
      # 0 1 0 0
      # 0 0 1 0
      # 0 0 0 1
      gluPerspective(camera.fovy, aspect, *camera.zRange)
      #print(glGetFloatv(GL_MODELVIEW_MATRIX))

      # CAMERA POSITION AND ORIENTATION
      gluLookAt(0,0,0, *camera.get_forward_vector(), *camera.get_upward_vector())
      glTranslatef(*-camera.pos)

      # TRANSLATE
      glTranslatef(*model.pos)

      # ROTATE
      gluLookAt(0,0,0, *model.get_forward_vector(), *model.get_upward_vector())

      # SCALE
      glScalef(model.scale, model.scale, model.scale)

      #print(glGetFloatv(GL_MODELVIEW_MATRIX))

      # RENDER WITH CURRENT MATRIX
      model.render()
    
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_DEPTH_TEST)
    

if __name__ == "__main__":
  print("Hello, engine?")
  print("Engine BROKE.")
  print("Understandable, have a nice day.")
  print("...")
  print("To use engine.py, import it.")
  
