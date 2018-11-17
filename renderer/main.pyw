#!/usr/bin/env python
'''
main.py
Entry point for main graphical application.

Made solely by Marcus Koh
'''
import os

##os.chdir(os.path.dirname(os.path.realpath(__file__)))

def start_debug():
    open("debug.log", "w").close()
def debug(msg):
    with open("debug.log", 'a') as f:
        f.write(msg+'\n')

def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

start_debug()

debug("uhh")
from all_modules import *
debug("Modules imported.")
from mainapp import MainApp

##def demo(app):
##  # for demo, add some models
##  from assetloader import Mesh, Tex
##  from engine import Model, Light
##  from rotpoint import Rot, Point
##  app.newProject()
##  icosMesh = app.R.loadMesh("./assets/meshes/texicosahedron.obj", name="20f solid")
##  cubeMesh = app.R.loadMesh("./assets/meshes/cube.obj", name="6f solid")
##  teapotMesh = app.R.loadMesh("./assets/meshes/teapot.obj", name="3-D Hello World")
##  abstractTex = app.R.loadTexture("./assets/textures/abstract.jpg", name="abstract")
##  metalTex = app.R.loadTexture("./assets/textures/metal.jpg", name="metal")
##  app.addAsset(icosMesh)
##  app.addAsset(cubeMesh)
##  app.addAsset(teapotMesh)
##  app.addAsset(abstractTex)
##  app.addAsset(metalTex)
##  icos = Model(icosMesh, abstractTex, pos=Point(0.0, 0.0, -5.0), name="Icosahedron")
##  floor = Model(cubeMesh, metalTex, pos=Point(0.0, -10, 0.0), scale=18, name="Floor")
##  teapot = Model(teapotMesh, metalTex, pos=Point(2, 0.0, -5.0), name="Teapot")
##  app.addRend(icos)
##  app.addRend(floor)
##  app.addRend(teapot)
##  app.logEntry("Info", "Focus on display and use WASDRF and arrows to control camera.")
##  app.logEntry("Info", "Both images and .obj files are loadable as meshed and textures respectively.")
##  app.logEntry("Info", "All environment objects are deletable (hotkey Delete) and editable.")
##  app.logEntry("Info", "Please report all bugs to https://github.com/Lax125/renderer/issues")
##  app.logEntry("Warning", "Please don't tamper with AppData/Roaming/Renderer. This kills the app.")

def main(*args, **kwargs):
    '''Runs the main graphical application.'''
    sys.except_hook = except_hook
    window = QApplication(sys.argv)
    QCoreApplication.setApplicationName(APPNAME)
    app = MainApp()
    app.restoreProject()
    sys.exit(window.exec_())
##  QCoreApplication.exit(window.exec_())

if __name__ == "__main__": # MAIN ENTRY POINT
    debug("Entry point entered.")
    main()
