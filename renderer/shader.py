#!/usr/bin/python
'''
shader.py

describes how lighting should interact with drawn elements.
"Let there be light," said God.
However, his words had no effect.
He forgot to add a shader.
'''

from OpenGL.GL import *
from OpenGL.GL import shaders

VSHADER_BASIC = open("vshader_basic.cpp").read()
FSHADER_BASIC = open("fshader_basic.cpp").read()

def load_pair(vscode, fscode):
  VS = shaders.compileShader(vscode, GL_VERTEX_SHADER)
  FS = shaders.compileShader(fscode, GL_FRAGMENT_SHADER)
  return shaders.compileProgram(VS, FS)

shaderDict = {"basic": (VSHADER_BASIC, FSHADER_BASIC),
             }

def init():
  global shaderDict
  shaderDict = {name: load_pair(vscode, fscode) for name, (vscode, fscode) in shaderDict.items()}

def use(shader_name):
  shaders.glUseProgram(shaderDict[shader_name])

if __name__ == "__main__":
  import pygame
  from pygame import *
  pygame.display.set_mode((100, 100), OPENGL)
  use("basic")
 
