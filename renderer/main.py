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
from sceneelement import Obj, Tex

from engine import Camera, Model, Scene, init_engine
from context import Context
from pygame.time import Clock

from OpenGL.GL import *
import pygame

def main():
  c = Context("pygame", (800, 400), "Renderer")
  init_engine()
  clock = Clock()
  obj0 = Obj(r"./assets/objects/tetrahedron.obj")
  obj1 = Obj(r"./assets/objects/halfcube.obj")
  obj2 = Obj(r"./assets/objects/octahedron.obj")
  obj3 = Obj(r"./assets/objects/dodecahedron.obj")
  obj4 = Obj(r"./assets/objects/texicosahedron.obj")
  obj5 = Obj(r"./assets/objects/pointer.obj")
  tex0 = Tex(r"./assets/textures/_default.png")
  tex1 = Tex(r"./assets/textures/metal.jpg")
  tex2 = Tex(r"./assets/textures/abstract.jpg")
  tex3 = Tex(r"./assets/textures/white.png")
  model0 = Model(obj0, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model1 = Model(obj1, tex2, pos=Point(-1.5, 0.0, 0.0), scale=0.8)
  model2 = Model(obj2, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model3 = Model(obj3, tex0, pos=Point(0.0, 0.0, 0.0), scale=0.8)
  model4 = Model(obj4, tex1, pos=Point(3.0, 2.0, 1.0), scale=0.8)
  model5 = Model(obj5, tex1, pos=Point(0.0, 0.0, 0.0), scale=2.0)
  camera = Camera(pos=Point(0.0, 0.0, 0.0), rot=Rot(0.0, 0.0, 0.0))
  scene = Scene({model1, model4, model5})

  camera_rotdeltas = {pygame.K_LEFT: Rot(0.0, -0.02, 0.0),
                      pygame.K_RIGHT: Rot(0.0, 0.02, 0.0),
                      pygame.K_DOWN: Rot(-0.02, 0.0, 0.0),
                      pygame.K_UP: Rot(0.02, 0.0, 0.0),
                      pygame.K_COMMA: Rot(0.0, 0.0, -0.02),
                      pygame.K_PERIOD: Rot(0.0, 0.0, 0.02)
                      }

  camera_posdeltas = {pygame.K_a: Point(-0.1, 0.0, 0.0),
                      pygame.K_d: Point(0.1, 0.0, 0.0),
                      pygame.K_s: Point(0.0, 0.0, 0.1),
                      pygame.K_w: Point(0.0, 0.0, -0.1),
                      pygame.K_f: Point(0.0, -0.1, 0.0),
                      pygame.K_r: Point(0.0, 0.1, 0.0)
                      }

  while True:
    clock.tick(60)
    c.idle()
    model0.rot += Rot(0.01, 0.02, 0.03)
    model1.rot += Rot(0.02, 0.03, 0.01)
    model2.rot += Rot(0.03, 0.01, 0.02)
    model3.rot += Rot(0.03, 0.02, 0.01)
    model4.rot += Rot(0.01, 0.03, 0.02)
    model5.rot += Rot(0.0, 0.0, 0.0)
    # rotate camera from keyboard inputs
    pygame.event.pump()
    pressed_keys = pygame.key.get_pressed()
    for k in camera_rotdeltas:
      if pressed_keys[k]:
        camera.rot += camera_rotdeltas[k]
        print(camera.rot)
    rx, ry, rz = camera.rot
    defacto_rot = Rot(rx, -ry, -rz)
    for k in camera_posdeltas:
      if pressed_keys[k]:
        camera.pos += defacto_rot.get_transmat() * camera_posdeltas[k]
        print(camera.pos)
    X, Y = c.getres()
    glViewport(0,0, X,Y)
    scene.render(camera, aspect=X/Y, mode="full")
    c.dispbuffer()

    

if __name__ == "__main__":
  main()
