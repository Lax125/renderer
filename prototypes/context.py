#!/usr/bin/python
## DEPRECATED
'''
context.py

describes window context for OpenGL buffer swap.
"Alright, draw me cube, OpenGL."
"Done."
"I don't see it..."
"You didn't tell me where to display it."
"Oh for crying out loud..."
'''

import sys, os, time

from OpenGL.GLUT import * # basically everything here begins with GLUT
import pygame
from pygame.locals import *


def setup_glut(res, name):
  glutInit(sys.argv)
  glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
  glutInitWindowSize(*res)
  glutCreateWindow(name)
  global resolution
  resolution = res
def setup_pygame(res, name):
  pygame.display.init()
  pygame.display.set_mode(res, RESIZABLE|DOUBLEBUF|OPENGL)
  pygame.display.set_caption(name)

def idle_glut():
  pass
def idle_pygame():
  pygame.event.pump()
  # the following lines should not be in the final product.
  # the graphical part of the application should not
  # control exit points.
  for event in pygame.event.get():
    if event.type is pygame.QUIT:
      pygame.quit()
      sys.exit()
    elif event.type is pygame.KEYDOWN and event.key is pygame.K_ESCAPE:
      pygame.quit()
      sys.exit()
    elif event.type is pygame.VIDEORESIZE:
      global resolution
      resolution = (event.w, event.h)

def dispbuffer_glut():
  glutSwapBuffers()
def dispbuffer_pygame():
  pygame.display.flip()

def getres_glut():
  return resolution
def getres_pygame():
  return resolution

setup = {"glut": setup_glut,
           "pygame": setup_pygame,
           }
idle = {"glut": idle_glut,
        "pygame": idle_pygame,
        }
dispbuffer = {"glut": dispbuffer_glut,
              "pygame": dispbuffer_pygame,
              }
getres = {"glut": getres_glut,
          "pygame": getres_pygame,
          }

class Context:
  def __init__(self, method, res=(600, 600), name="window0"):
    assert method in ["glut", "pygame"]
    self.method = method
    self.setup(res, name)

  def setup(self, res, name):
    setup[self.method](res, name)

  def idle(self):
    idle[self.method]()

  def dispbuffer(self):
    dispbuffer[self.method]()

  def getres(self):
    return getres[self.method]()

  
if __name__ == "__main__":
  c = Context("pygame")
  while True:
    time.sleep(0.02)
    c.idle()
    
