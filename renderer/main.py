#!/usr/bin/python
'''
main.py
Entry point for main graphical application.

Made solely by Marcus Koh
'''

import sys, os
from PyQt5.QtWidgets import QApplication
from gui import MainApp

def demo(app):
  # for demo, add some models
  from assetloader import Mesh, Tex
  from engine import Model, Light
  from rotpoint import Rot, Point
  icosMesh = Mesh("./assets/meshes/texicosahedron.obj", name="20f solid")
  cubeMesh = Mesh("./assets/meshes/cube.obj", name="6f solid")
  teapotMesh = Mesh("./assets/meshes/teapot.obj", name="3-D Hello World")
  abstractTex = Tex("./assets/textures/abstract.jpg", name="abstract")
  metalTex = Tex("./assets/textures/metal.jpg", name="metal")
  app.addAsset(icosMesh)
  app.addAsset(cubeMesh)
  app.addAsset(teapotMesh)
  app.addAsset(abstractTex)
  app.addAsset(metalTex)
  icos = Model(icosMesh, abstractTex, pos=Point(0.0, 0.0, -5.0), name="Icosahedron")
  floor = Model(cubeMesh, metalTex, pos=Point(0.0, -10, 0.0), scale=18, name="Floor")
  teapot = Model(teapotMesh, metalTex, pos=Point(2, 0.0, -5.0), name="Teapot")
  app.addRend(icos)
  app.addRend(floor)
  app.addRend(teapot)

def main(*args, **kwargs):
  '''Runs the main graphical application.'''
  window = QApplication(sys.argv)
  app = MainApp()
  demo(app)
  sys.exit(window.exec_())

if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    print("ERROR:", e)
