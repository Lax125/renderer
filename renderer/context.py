#!/usr/bin/python
'''
context.py

describes window context for OpenGL buffer swap.
"Alright, draw me cube, OpenGL."
"Done."
"I don't see it..."
"You didn't tell me where to display it."
"Oh for crying out loud..."
'''

import sys, os

from OpenGL.GLUT import * # basically everything here begins with GLUT
import pygame
from pygame.locals import *

from collections import deque

event_queue = deque()

EXIT = 0
SAVE_SCENE = 1
LOAD_SCENE = 2
EXPORT_IMAGE = 3
NEW_TEXTURE = 4
SELECT_TEXTURE = 5
DELETE_TEXTURE = 6
MAKE_MODEL = 7
SELECT_MODEL = 8
DELETE_MODEL = 9
MOD_MODEL = 10
# TODO: other command ids

def setup_glut(res, name):
  glutInit(sys.argv)
  glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
  glutInitWindowSize(*res)
  glutCreateWindow(name)
def setup_pygame(res, name):
  pygame.init()
  pygame.display.set_mode(res, DOUBLEBUF|OPENGL)
  pygame.display.set_caption(name)

def idle_glut():
  glutMainLoopEvent()
def idle_pygame():
  for event in pygame.event.get():
    if event.type is pygame.QUIT:
      global event_queue
      event_queue.append((EXIT, dict()))

      # because I haven't completed the event handler in userenv.py:
      pygame.quit()
      sys.exit()

def dispbuffer_glut():
  glutSwapBuffers()
def dispbuffer_pygame():
  pygame.display.flip()

def getres_glut():
  return (glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT))
def getres_pygame():
  s = pygame.display.get_surface()
  return (s.get_width(), s.get_height())

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

  
    
    
