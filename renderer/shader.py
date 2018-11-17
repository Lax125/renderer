#!/usr/bin/env python
'''
shader.py

describes how lighting should interact with drawn elements.

"Let there be light," said God.
However, his words had no effect.
He forgot to add a shader.
'''

from all_modules import *

SHADER_FILENAME_PAIRS = dict()
for shader_name in ["plain", "flat", "phong"]:
  SHADER_FILENAME_PAIRS[shader_name] = ("./shaders/%s/vshader.glsl"%shader_name, "./shaders/%s/fshader.glsl"%shader_name)

class Shader:
  current = None
  def __init__(self, vsfn, fsfn):
    try:
      self.vertShader = shaders.compileShader(open(vsfn).read(), GL_VERTEX_SHADER)
      self.fragShader = shaders.compileShader(open(fsfn).read(), GL_FRAGMENT_SHADER)
      self.program = shaders.compileProgram(self.vertShader, self.fragShader)
    except:
      traceback.print_exc()
      sys.exit(1)
    self.uniformLocs = {"texture": glGetUniformLocation(self.program, "texture"),
                        "ambientColorPower": glGetUniformLocation(self.program, "ambientColorPower"),
                        "diffuse": glGetUniformLocation(self.program, "diffuse"),
                        "specular": glGetUniformLocation(self.program, "specular"),
                        "fresnel": glGetUniformLocation(self.program, "fresnel"),
                        "shininess": glGetUniformLocation(self.program, "shininess"),
                        "lCount": glGetUniformLocation(self.program, "lCount"),
                        "lData": glGetUniformLocation(self.program, "lData"),
                        "lPositions": glGetUniformLocation(self.program, "lPositions"),
                        "lColorPowers": glGetUniformLocation(self.program, "lColorPowers"),
##                        "lDirections": glGetUniformLocation(self.program, "lDirections"),
##                        "lAOEs": glGetUniformLocation(self.program, "lAOEs"),
                        }

  def use(self):
    Shader.current = self
    shaders.glUseProgram(self.program)
 
