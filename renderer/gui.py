#!/usr/bin/python

'''
gui.py

Makes the graphical application
'''

import sys, os

from OpenGL.GL import *
from OpenGL.GLU import *

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import *

from rotpoint import Rot, Point
from assetloader import Obj, Tex
from engine import Model, Light
from userenv import UserEnv
from remote import Remote

from math import ceil

UE = UserEnv()
R = Remote(UE)

ROT_DELTAS = {Qt.Key_Left: (0, -1, 0),
              Qt.Key_Right: (0, 1, 0),
              Qt.Key_Down: (-1, 0, 0),
              Qt.Key_Up: (1, 0, 0),
              Qt.Key_Comma: (0, 0, -1),
              Qt.Key_Period: (0, 0, 1)}

POS_DELTAS = {Qt.Key_A: (-5, 0, 0),
              Qt.Key_D: (5, 0, 0),
              Qt.Key_S: (0, 0, 5),
              Qt.Key_W: (0, 0, -5),
              Qt.Key_F: (0, -5, 0),
              Qt.Key_R: (0, 5, 0)}

class glWidget(QGLWidget):
  '''OpenGL QT widget'''
  def __init__(self, parent):
    QGLWidget.__init__(self, parent)
    self.dims = (100, 100)
    self.aspect = 1.0
    self.refresh_rate = 60
    self.refresh_period = ceil(1000/self.refresh_rate)
    self.timer = QTimer()
    self.timer.setInterval(self.refresh_period)
    self.timer.timeout.connect(self.onTick)
    self.heldKeys = set()
    self.timer.start()
    self.setFocusPolicy(Qt.StrongFocus)

  def paintGL(self):
    R.renderScene(aspect=self.aspect)

  def resizeGL(self, w, h):
    self.dims = w, h
    self.aspect = w/h
    R.resizeViewport(w,h)
    QGLWidget.resizeGL(self, w, h)

  def keyPressEvent(self, event):
    self.heldKeys.add(event.key())

  def keyReleaseEvent(self, event):
    self.heldKeys.discard(event.key())

  def onTick(self): # custom: scheduled to call at regular intervals
    self.handleHeldKeys()
    self.update()

  def handleHeldKeys(self):
    if len(self.heldKeys) == 0:
      return
    dt = (self.refresh_period/1000)
    for k, (drx, dry, drz) in ROT_DELTAS.items():
      if k in self.heldKeys:
        R.changeCameraRot(dt*drx, dt*dry, dt*drz)

    for k, (dx, dy, dz) in POS_DELTAS.items():
      if k in self.heldKeys:
        rx, ry, rz = UE.camera.rot
        defacto_drot = Rot(rx, -ry, -rz)
        dp = dt * defacto_drot.get_transmat() * Point(dx, dy, dz)
        R.moveCamera(*dp)

class AssetList(QListWidget):
  '''QT Widget: list of rends'''
  def __init__(self, parent=None):
    super().__init__(parent)

  def add(self, asset):
    new_item = QListWidgetItem()
    new_item.setText(asset.name)
    new_item.asset = asset
    self.addItem(new_item)

  def remove(self, item):
    R.delAsset(item.asset)
    self.takeItem(self.row(item))

  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Delete:
      for item in self.selectedItems():
        self.remove(item)

class RendList(QListWidget):
  '''QT Widget: list of rends'''
  def __init__(self, parent=None):
    super().__init__(parent)

  def add(self, rend):
    new_item = QListWidgetItem()
    new_item.setText(rend.name)
    new_item.rend = rend
    self.addItem(new_item)

  def remove(self, item):
    R.delRend(item.rend)
    self.takeItem(self.row(item))

  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Delete:
      for item in self.selectedItems():
        self.remove(item)

class MainApp(QMainWindow):
  '''Main Application, uses QT'''
  def __init__(self, parent=None):
    super().__init__(parent)
    self._make_widgets()
    self.resize(800, 500)
    self.setWindowTitle("Renderer")
    self.show()

  def _make_widgets(self):
    layout = QHBoxLayout()
    self.setLayout(layout)
    
    bar = self.menuBar()
    file = bar.addMenu("File")
    file.addAction("Load project")
    file.addAction("Save project")
    
    self.itemPane = QDockWidget("Scene", self)
    self.itemPane.setFeatures(QDockWidget.DockWidgetMovable)
    self.itemTabs = QTabWidget()
    self.objectList = AssetList()
    self.textureList = AssetList()
    self.modelList = RendList()
    self.lightList = RendList()
    self.itemTabs.addTab(self.objectList, "Objects")
    self.itemTabs.addTab(self.textureList, "Textures")
    self.itemTabs.addTab(self.modelList, "Models")
    self.itemTabs.addTab(self.lightList, "Lights")
    self.itemPane.setWidget(self.itemTabs)
    self.itemPane.setFloating(False)
    self.setCentralWidget(glWidget(self))
    self.addDockWidget(Qt.LeftDockWidgetArea, self.itemPane)

    self.infoPane = QDockWidget("Info", self)
    self.infoPane.setFeatures(QDockWidget.DockWidgetMovable)
    self.infoContent = QTextEdit() # PLACEHOLDER
    self.infoContent.setText("Hello, World!")
    self.infoPane.setWidget(self.infoContent)
    self.addDockWidget(Qt.BottomDockWidgetArea, self.infoPane)
    
  def addAsset(self, asset):
    if R.addAsset(asset):
      return
    if isinstance(asset, Obj):
      self.objectList.add(asset)
    elif isinstance(asset, Tex):
      self.textureList.add(asset)
      
  def addRend(self, rend):
    if R.addRend(rend): # renderable already in the scene
      return
    if isinstance(rend, Model):
      self.modelList.add(rend)
    elif isinstance(rend, Light):
      self.lightList.add(rend)

if __name__ == "__main__":
  window = QApplication(sys.argv)
  app = MainApp()
  # for demo, add some models
  from assetloader import Obj, Tex
  from engine import Model, Light
  from rotpoint import Rot, Point
  teapotObj = Obj("./assets/objects/texicosahedron.obj")
  metalTex = Tex("./assets/textures/metal.jpg")
  app.addAsset(teapotObj)
  app.addAsset(metalTex)
  teapot = Model(teapotObj, metalTex, pos=Point(0.0, 0.0, -5.0), name="Icosahedron")
  teapot2 = Model(teapotObj, metalTex, pos=Point(2, 0.0, -5.0), name="Icosahedron")
  app.addRend(teapot)
  app.addRend(teapot2)
  sys.exit(window.exec_())

