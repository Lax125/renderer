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
from engine import Model, Light, initEngine
from userenv import UserEnv
from remote import Remote

from math import ceil
from time import gmtime, strftime
from copy import deepcopy

def getTimestamp():
  return strftime("UTC %y-%m-%d %H:%M:%S", gmtime())

UE = UserEnv()
R = Remote(UE)

ROT_DELTAS = {Qt.Key_Left: (0, -2, 0),
              Qt.Key_Right: (0, 2, 0),
              Qt.Key_Down: (-2, 0, 0),
              Qt.Key_Up: (2, 0, 0),
              Qt.Key_Comma: (0, 0, -2),
              Qt.Key_Period: (0, 0, 2)}

POS_DELTAS = {Qt.Key_A: (-5, 0, 0),
              Qt.Key_D: (5, 0, 0),
              Qt.Key_S: (0, 0, 5),
              Qt.Key_W: (0, 0, -5),
              Qt.Key_F: (0, -5, 0),
              Qt.Key_R: (0, 5, 0)}

def copyAssetList(ql):
  # makes copy of ql
  cql = QListWidget()
  for i in range(ql.count()):
    item = ql.item(i)
    citem = QListWidgetItem()
    citem.asset = item.asset
    citem.setText(item.text())
    cql.addItem(citem)
  return cql

def copyRendList(ql):
  # makes copy of ql
  cql = QListWidget()
  print(ql.count())
  for i in range(ql.count()):
    item = ql.item(i)
    citem = QListWidgetItem()
    citem.rend = item.rend
    citem.setText(item.text())
    cql.addItem(citem)
  return cql

class glWidget(QGLWidget):
  '''OpenGL QT widget'''
  engine_initialised = False
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
    if not glWidget.engine_initialised:
      glWidget.engine_initialised = True
      initEngine()
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
    self.setSortingEnabled(True)
    self.setSelectionMode(3)

  def add(self, asset):
    new_item = QListWidgetItem()
    new_item.setText(asset.name)
    new_item.asset = asset
    self.addItem(new_item)
    return new_item

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
    self.setSortingEnabled(True)
    self.setSelectionMode(3)
    self.itemClicked.connect(self.onItemClicked)

  def onItemClicked(self, item):
    R.setFocus(item.rend)

  def add(self, rend):
    new_item = QListWidgetItem()
    new_item.setText(rend.name)
    new_item.rend = rend
    self.addItem(new_item)
    return new_item

  def remove(self, item):
    R.delRend(item.rend)
    self.takeItem(self.row(item))

  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Delete:
      for item in self.selectedItems():
        self.remove(item)

class Modal(QDialog):
  def __init__(self, *args, **kwargs):
    QDialog.__init__(self, *args, **kwargs)
    self.setModal(True)

class MainApp(QMainWindow):
  '''Main Application, uses QT'''
  def __init__(self, parent=None):
    super().__init__(parent)
    self._make_widgets()
    self.resize(1000, 500)
    self.setWindowTitle("Renderer")
    self.show()

  def _make_widgets(self):
    layout = QHBoxLayout()
    self.setLayout(layout)
    
    bar = self.menuBar()
    file = bar.addMenu("File")
    file.addAction("Load project", self.loadProject)
    file.addAction("Save project", self.saveProject)
    file.addAction("Load objects", self.loadObjects)
    file.addAction("Load textures", self.loadTextures)
    scene = bar.addMenu("Scene")
    scene.addAction("Make models", self.makeModels)
    scene.addAction("Make lights", self.makeLights)
    view = bar.addMenu("View")
    view.addAction("Show Environment", self.showEnv)
    view.addAction("Show Edit", self.showEdit)
    view.addAction("Show Log", self.showLog)
    
    self.envPane = QDockWidget("Environment", self)
    self.envPane.setFeatures(QDockWidget.DockWidgetMovable|
                              QDockWidget.DockWidgetClosable)
    self.env = QTabWidget()
    self.objectList = AssetList()
    self.textureList = AssetList()
    self.modelList = RendList()
    self.lightList = RendList()
    self.env.addTab(self.objectList, "Objects")
    self.env.addTab(self.textureList, "Textures")
    self.env.addTab(self.modelList, "Models")
    self.env.addTab(self.lightList, "Lights")
    self.env.setTabEnabled(2, True)
    self.envPane.setWidget(self.env)
    self.envPane.setFloating(False)
    self.setCentralWidget(glWidget(self))
    self.addDockWidget(Qt.LeftDockWidgetArea, self.envPane)

    self.editPane = QDockWidget("Edit", self)
    self.editPane.setFeatures(QDockWidget.DockWidgetMovable|
                              QDockWidget.DockWidgetClosable)
    self.edit = QTextEdit() # PLACEHOLDER
    self.edit.setText("===PLACEHOLDER===\n"+open("./assets/text/beemovie.txt").read())
    self.editPane.setWidget(self.edit)
    self.addDockWidget(Qt.RightDockWidgetArea, self.editPane)

    self.logPane = QDockWidget("Log", self)
    self.logPane.setFeatures(QDockWidget.DockWidgetMovable|
                             QDockWidget.DockWidgetClosable)
    self.logModel = QStandardItemModel(0,3, self.logPane)
    self.logModel.setHorizontalHeaderLabels(["Type", "Info", "Timestamp"])
    self.log = QTableView()
    self.log.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.log.setModel(self.logModel)
    self.log.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.log.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    self.logPane.setWidget(self.log)
    self.addDockWidget(Qt.BottomDockWidgetArea, self.logPane)
    self.logEntry("Info", "Welcome to Renderer 0.3.0")
    self.logEntry("Info", "Pssst...stalk me on GitHub: github.com/Lax125")
  
  def showEnv(self):
    self.envPane.show()

  def showEdit(self):
    self.editPane.show()

  def showLog(self):
    self.logPane.show()

  def logEntry(self, entryType, entryText):
    assert entryType in ["Info",
                         "Success",
                         "Warning",
                         "Error"]
    etype = QStandardItem(entryType)
    info = QStandardItem(entryText)
    timestamp = QStandardItem(getTimestamp())
    self.logModel.insertRow(0, [etype, info, timestamp])
    if self.logModel.rowCount() > 100:
      self.logModel.removeRows(100, 1)

  def addEnvObj(self, envobj):
    QListDict = {Obj: self.objectList,
                 Tex: self.textureList,
                 Model: self.modelList,
                 Light: self.lightList}
    L = QListDict[type(envobj)]
    item = L.add(envobj)
    
  def addAsset(self, asset):
    if R.addAsset(asset):
      return
    self.addEnvObj(asset)
      
  def addRend(self, rend):
    if R.addRend(rend): # renderable already in the scene
      return
    self.addEnvObj(rend)

  def saveProject(self):
    pass

  def loadProject(self):
    pass

  def loadObjects(self):
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters([r"Wavefront Object files (*.obj)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        try:
          self.addAsset(Obj(fn))
        except:
          self.logEntry("Error", "Bad object file: %s"%fn)
        else:
          self.logEntry("Success", "Loaded object from %s"%fn)

  def loadTextures(self):
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters(["Images (*.bmp;*.png;*.jpg)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        try:
          self.addAsset(Tex(fn))
        except:
          self.logEntry("Error", "Bad image file: %s"%fn)
        else:
          self.logEntry("Success", "Loaded texture from %s"%fn)

  def makeModels(self):
    '''Instantiates and returns modal for making models'''
    M = Modal(self)
    M.setWindowTitle("Make Models")
    layout = QGridLayout()
    M.setLayout(layout)
    
    assetBox = QGroupBox("Assets")
    layout.addWidget(assetBox, 0,0, 2,1)
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    oList = copyAssetList(self.objectList)
    assetLayout.addRow("Object", oList)
    tList = copyAssetList(self.textureList)
    assetLayout.addRow("Texture", tList)
    
    poseBox = QGroupBox("Pose")
    layout.addWidget(poseBox, 0,1, 1,1)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    ry = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    rz = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    scale = QDoubleSpinBox(minimum=0, maximum=2147483647, value=1)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Yaw", ry)
    poseLayout.addRow("Pitch", rx)
    poseLayout.addRow("Roll", rz)
    poseLayout.addRow("scale", scale)

    matBox = QGroupBox("Material")
    layout.addWidget(matBox, 1,1, 1,1)
    matLayout = QFormLayout()
    matBox.setLayout(matLayout)
    shininess = QDoubleSpinBox(minimum=0, maximum=2147483647)
    matLayout.addRow("Shininess", shininess)

    custBox = QGroupBox("Customisation")
    layout.addWidget(custBox, 2,0, 1,1)
    custLayout = QFormLayout()
    custBox.setLayout(custLayout)
    name = QLineEdit(text="model0")
    custLayout.addRow("Name", name)

    def tryMakeModel():
      o = oList.selectedItems()
      t = tList.selectedItems()
      if not (len(o) and len(t)):
        self.logEntry("Error", "Please select an object and a texture.")
        return
      obj = o[0].asset
      tex = t[0].asset
      pos = Point(x.value(), y.value(), z.value())
      rot = Rot(rx.value(), ry.value(), rz.value())
      model = Model(obj, tex, shininess=shininess.value(),
                    pos=pos, rot=rot, scale=scale.value(),
                    name=name.text())
      self.addRend(model)
      self.logEntry("Success", "Made model.")

    make = QPushButton(text="Make Model")
    make.clicked.connect(tryMakeModel)
    layout.addWidget(make, 2,1, 1,1)

    def testValid():
      
      make.setEnabled(len(oList.selectedItems()) and len(tList.selectedItems()))

    oList.itemClicked.connect(testValid)
    tList.itemClicked.connect(testValid)
    testValid()
    M.resize(500, 500)
    M.exec_()

  def makeLights(self):
    # prompt user to make lights from position, diffuse part, specular part, direction, and angle of effect
    pass

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

