#!/usr/bin/python
'''
main.py
Entry point for main graphical application.

Made solely by Marcus Koh
'''

import sys, os
import logging
import numpy as np
from math import sin, cos, tan, pi, tau

from rotpoint import Point, Rot
from objtex import Obj, load_texture

from engine import Camera, Model, Scene
from context import Context
from pygame.time import Clock

from OpenGL.GL import *

def main():
  c = Context("pygame", (800, 400), "Renderer")
  clock = Clock()
  obj0 = Obj(r"./assets/objects/tetrahedron.obj")
  obj1 = Obj(r"./assets/objects/halfcube.obj")
  obj2 = Obj(r"./assets/objects/octahedron.obj")
  obj3 = Obj(r"./assets/objects/dodecahedron.obj")
  obj4 = Obj(r"./assets/objects/texicosahedron.obj")
  obj5 = Obj(r"./assets/objects/teapot.obj")
  tex0 = load_texture(r"./assets/textures/_default.png")
  tex1 = load_texture(r"./assets/textures/metal.jpg")
  tex2 = load_texture(r"./assets/textures/abstract.jpg")
  tex3 = load_texture(r"./assets/textures/white.png")
  model0 = Model(obj0, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model1 = Model(obj1, tex0, pos=Point(-0.2, 0.0, 0.0), scale=0.8)
  model2 = Model(obj2, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model3 = Model(obj3, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model4 = Model(obj4, tex1, pos=Point(0.2, 0.0, 0.0), scale=0.8)
  model5 = Model(obj5, tex2, pos=Point(0.2, 0.0, 0.0), scale=0.4)
  camera = Camera(pos=Point(0.0, 0.0, 3.0), rot=Rot(0.0, pi, 0.0))
  scene = Scene({model1, model4})

  while True:
    clock.tick(60)
    c.idle()
    model0.rot += Rot(0.01, 0.02, 0.03)
    model1.rot += Rot(0.02, 0.03, 0.01)
    model2.rot += Rot(0.03, 0.01, 0.02)
    model3.rot += Rot(0.03, 0.02, 0.01)
    model4.rot += Rot(0.01, 0.03, 0.02)
    model5.rot += Rot(0.02, 0.01, 0.03)
    camera.pos = Point(0.0, 0.0, 3.0)
    camera.rot = Rot(0.0, pi, 0.0)
    X, Y = c.getres()
    glViewport(0,0, X, Y)
    scene.render(camera, aspect=X/Y, mode="full")
    c.dispbuffer()

if __name__ == "__main__":
  main()
