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
from math import sin, cos, tan, atan, atan2, pi, tau, degrees, radians

# FOR BUFFER CALCULATION
import OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *

# CUSTOM SCRIPTS FOR:
#   - DESCRIBING POSITIONS IN 3-D AND ROTATIONAL ORIENTATION
#   - LOADING SHADERS
from rotpoint import Point, Rot
import shader

# FOR LOGGING
FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('engine')

class Camera:
  '''Describes a camera in 3-D position and rotation'''
  
  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), fovy=60, zoom=1.0, zRange=(0.1, 10000)):
    '''Initialise a Camera object in a position and rotation'''
    self.pos = pos
    self.rot = rot
    self.fovy = fovy # field of view in degrees in y axis
    self.zoom = zoom # true fovy == atan(tan(fovy/2)/zoom)*2
    self.zRange = zRange # visible slice of the scene

  def get_forward_vector(self):
    return self.rot.get_forward_vector()

  def get_upward_vector(self):
    return self.rot.get_upward_vector()

class Renderable:
  '''Base class for renderable objects: Models, Lights'''

  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), scale=1.0, visible=True, name="renderable0"):
    self.pos = pos
    self.rot = rot
    self.scale = scale
    self.visible = visible
    self.name = name

  def __str__(self):
    return self.name

  def glMat(self):
    # TRANSLATE
    glTranslatef(*self.pos)

    # ROTATE
    gluLookAt(0,0,0, *self.rot.get_forward_vector(), *self.rot.get_upward_vector())

    # SCALE
    glScalef(self.scale, self.scale, self.scale)

  def render(self): # overload with function that puts the renderable in the OpenGL environment
    pass

  def place(self):
    self.glMat()
    self.render()

class Model(Renderable):
  '''Describes polyhedron-like 3-D model in a position and orientation'''
  
  def __init__(self, mesh, tex, shininess=0.0, *args, **kwargs):
    '''Initialise 3-D model from loaded mesh and texture files with position pos, rotation rot, and scale scale'''
    self.mesh = mesh
    self.tex = tex
    self.shininess = shininess
    super().__init__(*args, **kwargs)

  def __repr__(self):
    reprtuple = (repr(self.mesh), repr(self.tex), repr(self.pos), repr(self.rot), repr(self.scale))
    return "Model(%s, %s, pos=%s, rot=%s, scale=%s)"%reprtuple

  def render(self):
    if self.visible:
      self.mesh.render(self.tex)

class Light(Renderable):
  pass #TODO


class Scene:
  '''Defines a list of renderable objects'''
  
  def __init__(self, rends=set()):
    self.rends = set()
    for rend in rends:
      self.add(rend)

  def __iter__(self):
    return self.rends.__iter__()

  def add(self, rend):
    self.rends.add(rend)

  def remove(self, rend):
    self.rends.remove(rend)

  def discard(self, rend):
    self.rends.discard(rend)

  def render(self, camera, aspect=None, mode="full", shader_name="basic"):
    glClearColor(0.0, 0.0, 0.1, 0.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    
    glMatrixMode(GL_MODELVIEW)

    ## SELECT SHADER
##    shader.use(shader_name)

    # Ambient lighting
##    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.5, 0.5, 0.5, 1.0])

    # You have a torch with you
##    glLightfv(GL_LIGHT0, GL_DIFFUSE, [10.0, 10.0, 10.0, 1.0])
##    glLightfv(GL_LIGHT0, GL_SPECULAR, [2.0, 2.0, 2.0, 1.0])
##    glLighti(GL_LIGHT0, GL_SPOT_CUTOFF, 30)
##    glLightfv(GL_LIGHT0, GL_POSITION, [*camera.pos, 1.0])
##    glLightfv(GL_LIGHT1, GL_POSITION, [0, 0, 0, 0])
##    glEnable(GL_LIGHT1)

    # Push camera position/perspective matrix onto stack
    glLoadIdentity()
    defacto_fovy = degrees(atan(tan(radians(camera.fovy)/2)/camera.zoom))*2
    gluPerspective(defacto_fovy, aspect, *camera.zRange)
    gluLookAt(0,0,0, *camera.rot.get_forward_vector(invert=True), *camera.rot.get_upward_vector(invert=True))
    glTranslatef(*-camera.pos)
    glPushMatrix()
    
    
    for rend in self.rends:
      if not rend.visible:
        continue
      
      # Copy camera matrix from stack onto working matrix
      glPopMatrix()
      glPushMatrix()

      rend.place()

    # Pop camera matrix from stack. Net change in stack: 0
    glPopMatrix()

def initEngine(): # only call once context has been established
  shader.init()

  # Enable wanted gl modes
  glEnable(GL_DEPTH_TEST)
  glEnable(GL_TEXTURE_2D)
  glEnable(GL_NORMALIZE)
  glEnable(GL_POLYGON_SMOOTH)
  glEnable(GL_DITHER)
  glEnable(GL_FOG)
  glFogi(GL_FOG_MODE, GL_EXP)
  glFogf(GL_FOG_END, 1000.0)
  glFogf(GL_FOG_DENSITY, 0.1)
    

if __name__ == "__main__":
  print("Hello, engine?")
  print("Engine BROKE.")
  print("Understandable, have a nice day.")
  print("...")
  print("To use engine.py, import it.")
  
