#!/usr/bin/python
'''
main.py
Entry point for main graphical application.

Made solely by Marcus Koh
'''

import sys, os
from PyQt5.QtWidgets import QApplication
from gui import MainApp
from assetloader import Obj, Tex

def main(*args, **kwargs):
  '''Runs the main graphical application.'''
  window = QApplication(sys.argv)
  app = MainApp()
  # for demo, add some models
  from assetloader import Obj, Tex
  from engine import Model, Light
  from rotpoint import Rot, Point
  icosObj = Obj("./assets/objects/texicosahedron.obj", name="20f solid")
  teapotObj = Obj("./assets/objects/teapot.obj", name="3-D Hello World")
  metalTex = Tex("./assets/textures/metal.jpg", name="metal")
  app.addAsset(icosObj)
  app.addAsset(teapotObj)
  app.addAsset(metalTex)
  icos = Model(icosObj, metalTex, pos=Point(0.0, 0.0, -5.0), name="Icosahedron")
  teapot = Model(teapotObj, metalTex, pos=Point(2, 0.0, -5.0), name="Teapot")
  app.addRend(icos)
  app.addRend(teapot)
  sys.exit(window.exec_())

if __name__ == "__main__":
  main()
