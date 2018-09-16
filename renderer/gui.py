#!/usr/bin/python

'''
gui.py

Makes the graphical application and runs the main systems
'''

import sys, os
import time
import numpy as np

from OpenGL.GL import *
from OpenGL.GLU import *

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import *

from rotpoint import Rot, Point
from assetloader import Asset, Mesh, Tex
from engine import Renderable, Model, Light, initEngine
from userenv import UserEnv
from remote import Remote
from saver import Saver

from math import ceil, pi
from time import gmtime, strftime
from copy import deepcopy
from PIL import Image

def cyclamp(x, R): # Like modulo, but based on cutom range
  a, b = R
  return (x-a)%(b-a) + a

def getTimestamp():
  return strftime("UTC %y-%m-%d %H:%M:%S", gmtime())

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
  for i in range(ql.count()):
    item = ql.item(i)
    citem = QListWidgetItem()
    citem.rend = item.rend
    citem.setText(item.text())
    cql.addItem(citem)
  return cql

class glWidget(QGLWidget):
  '''OpenGL+QT widget'''
  engine_initialised = False
  def __init__(self, parent):
    QGLWidget.__init__(self, parent)
    self.parent = parent
    self.dims = (100, 100)
    self.aspect = 1.0
    self.refresh_rate = 60
    self.refresh_period = ceil(1000/self.refresh_rate)
    self.timer = QTimer()
    self.timer.setInterval(self.refresh_period)
    self.timer.timeout.connect(self.onTick)
    self.heldKeys = set()
    self.lastt = time.time()
    self.dt = 0
    self.timer.start()
    self.setFocusPolicy(Qt.StrongFocus)

  def paintGL(self):
    if not glWidget.engine_initialised:
      glWidget.engine_initialised = True
      initEngine()
    self.parent.R.renderScene(aspect=self.aspect)

  def resizeGL(self, w, h):
    self.dims = w, h
    self.aspect = w/h
    self.parent.R.resizeViewport(w,h)
    QGLWidget.resizeGL(self, w, h)

  def keyPressEvent(self, event):
    self.heldKeys.add(event.key())

  def keyReleaseEvent(self, event):
    self.heldKeys.discard(event.key())

  def onTick(self): # custom: scheduled to call at regular intervals
    now = time.time()
    self.dt = now - self.lastt
    self.lastt = now
    self.handleHeldKeys()
    self.update()

  def handleHeldKeys(self):
    if len(self.heldKeys) == 0:
      return
    dt = self.dt
    for k, (drx, dry, drz) in ROT_DELTAS.items():
      if k in self.heldKeys:
        self.parent.R.changeCameraRot(dt*drx, dt*dry, dt*drz)

    for k, (dx, dy, dz) in POS_DELTAS.items():
      if k in self.heldKeys:
        dp = dt * self.parent.UE.camera.rot.get_transmat(invert=True) * Point(dx, dy, dz)
        self.parent.R.moveCamera(*dp)

    self.parent.update()

class AssetList(QListWidget):
  '''QT Widget: list of rends'''
  def __init__(self, parent=None):
    super().__init__(parent)
    self.parent = parent
    self.setSortingEnabled(True)
    self.setSelectionMode(3)
    self.itemClicked.connect(self.onItemClicked)

  def onItemClicked(self, item):
    self.parent.select(item.asset)

  def add(self, asset):
    new_item = QListWidgetItem()
    new_item.setText(asset.name)
    new_item.asset = asset
    self.addItem(new_item)
    return new_item

  def remove(self, item):
    self.parent.R.delAsset(item.asset)
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
    self.parent = parent
    self.setSortingEnabled(True)
    self.setSelectionMode(3)
    self.itemClicked.connect(self.onItemClicked)

  def onItemClicked(self, item):
    self.parent.R.setFocus(item.rend)
    self.parent.select(item.rend)

  def add(self, rend):
    new_item = QListWidgetItem()
    new_item.setText(rend.name)
    new_item.rend = rend
    self.addItem(new_item)
    return new_item

  def remove(self, item):
    self.parent.R.delRend(item.rend)
    self.takeItem(self.row(item))

  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Delete:
      for item in self.selectedItems():
        self.remove(item)

class Modal(QDialog):
  '''A dialog box that grabs focus until closed'''
  def __init__(self, *args, **kwargs):
    QDialog.__init__(self, *args, **kwargs)
    self.setModal(True)

class ResizableTabWidget(QTabWidget):
  '''A tab widget that resizes based on current widget'''
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.currentChanged.connect(self.onCurrentChanged)

  def sizeHint(self):
    return self.currentWidget().sizeHint()

  def minimumSizeHint(self):
    return self.currentWidget().minimumSizeHint()

  def onCurrentChanged(self, _):
    self.resize(self.currentWidget().sizeHint())

class ResizableStackedWidget(QStackedWidget):
  '''A stacked widget that resizes based on the current widget'''
  def __init__(self, *args, **kwargs):
    QStackedWidget.__init__(self, *args, **kwargs)
    self.currentChanged.connect(self.onCurrentChanged)
    
  def sizeHint(self):
    return self.currentWidget().sizeHint()

  def minimumSizeHint(self):
    return self.currentWidget().minimumSizeHint()

  def onCurrentChanged(self, i):
    self.resize(self.currentWidget().sizeHint())

class VerticalScrollArea(QScrollArea):
  '''A scroll area that scrolls vertically but acts normally horizontally'''
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

  def sizeHint(self):
    W = self.widget()
    if W:
      return QSize(W.sizeHint().width() + self.verticalScrollBar().width(), 0)
    return QSize(0, 0)

  def minimumSizeHint(self):
    W = self.widget()
    if W:
      return QSize(W.minimumSizeHint().width() + self.verticalScrollBar().width(), 0)
    return QSize(0, 0)

  

class MainApp(QMainWindow):
  '''Main Application, uses QT'''
  def __init__(self, parent=None):
    self.selected = None
    self.UE = UserEnv()
    self.R = Remote(self.UE)

    super().__init__(parent)
    self._make_widgets()
    self.resize(1000, 500)
    self.setWindowTitle("Renderer")
    self.show()
    self.S = Saver(self)

  def _make_widgets(self):
    '''Initialise all widgets'''
    layout = QHBoxLayout()
    self.setLayout(layout)
    
    bar = self.menuBar()
    file = bar.addMenu("File")
    file.addAction("New project", self.newProject)
    file.addAction("Open project", self.openProject)
    file.addAction("Save project", self.saveProject)
    file.addSeparator()
    file.addAction("Load meshes", self.loadMeshes)
    file.addAction("Load textures", self.loadTextures)
    file.addSeparator()
    file.addAction("Export image", self.exportImage)
    scene = bar.addMenu("Scene")
    scene.addAction("Make models", self.makeModels)
    scene.addAction("Make lights", self.makeLights)
    view = bar.addMenu("View")
    view.addAction("Show Environment", self.showEnv)
    view.addAction("Show Edit", self.showEdit)
    view.addAction("Show Log", self.showLog)

    self.gl = glWidget(self)
    self.setCentralWidget(self.gl)
    
    self.envPane = QDockWidget("Environment", self)
    self.envPane.setFeatures(QDockWidget.DockWidgetMovable|
                              QDockWidget.DockWidgetClosable)
    self.env = ResizableTabWidget()
    self.meshList = AssetList(self)
    self.texList = AssetList(self)
    self.modelList = RendList(self)
    self.lightList = RendList(self)
    self.env.addTab(self.meshList, "Meshes")
    self.env.addTab(self.texList, "Textures")
    self.env.addTab(self.modelList, "Models")
    self.env.addTab(self.lightList, "Lights")
    self.env.setTabEnabled(2, True)
    self.envPane.setWidget(self.env)
    self.envPane.setFloating(False)
    self.addDockWidget(Qt.LeftDockWidgetArea, self.envPane)

    self.editPane = QDockWidget("Edit", self)
    self.editPane.setFeatures(QDockWidget.DockWidgetMovable|
                              QDockWidget.DockWidgetClosable)
    self.edit = ResizableTabWidget()
    self.camEdit = QWidget()
    self.camScrollArea = VerticalScrollArea()
    self.selEdit = ResizableStackedWidget()
    self.selEdit.currentChanged.connect(lambda i: self.edit.onCurrentChanged(0))
    self.selScrollArea = VerticalScrollArea()
    self.edit.addTab(self.camScrollArea, "Camera")
    self.edit.addTab(self.selScrollArea, "Selected")
    self.editPane.setWidget(self.edit)
    self.initEditPane()
    self.camScrollArea.setWidget(self.camEdit)
    self.selScrollArea.setWidget(self.selEdit)
    self.addDockWidget(Qt.RightDockWidgetArea, self.editPane)

    self.logPane = QDockWidget("Log", self)
    self.logPane.setFeatures(QDockWidget.DockWidgetMovable|
                             QDockWidget.DockWidgetClosable)
    self.logModel = QStandardItemModel(0,3, self.logPane)
    self.logModel.setHorizontalHeaderLabels(["Type", "Info", "Timestamp"])
    self.log = QTableView()
##    self.log.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.log.setModel(self.logModel)
    self.log.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.log.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    self.logPane.setWidget(self.log)
    self.addDockWidget(Qt.BottomDockWidgetArea, self.logPane)
    self.logEntry("Info", "Welcome to Renderer 0.3.0")
    self.logEntry("Info", "Pssst...stalk me on GitHub: github.com/Lax125")
  
  def showEnv(self):
    '''Show environment pane'''
    self.envPane.show()

  def showEdit(self):
    '''Show edit pane'''
    self.editPane.show()

  def showLog(self):
    '''Show log pane'''
    self.logPane.show()

  def logEntry(self, entryType, entryText):
    '''Log an entry into the log pane'''
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

  def clearLists(self):
    '''Empty all QListWidget's'''
    self.meshList.clear()
    self.texList.clear()
    self.modelList.clear()
    self.lightList.clear()

  def addEnvObj(self, envobj):
    '''Adds environment object into appropriate QListWidget'''
    QListDict = {Mesh: self.meshList,
                 Tex: self.texList,
                 Model: self.modelList,
                 Light: self.lightList}
    L = QListDict[type(envobj)]
    item = L.add(envobj)
    
  def addAsset(self, asset):
    '''Adds Asset object into scene and QListWidget'''
    if self.R.addAsset(asset): # asset already in user environment
      return
    self.addEnvObj(asset)
      
  def addRend(self, rend):
    '''Adds Renderable object into userenv and QListWidget'''
    if self.R.addRend(rend): # renderable already in the scene
      return
    self.addEnvObj(rend)

  def newProject(self, silent=False):
    '''Clear user environment and QListWidgets'''
    self.clearLists()
    self.R.new()
    self.selected = None
    if not silent:
      self.logEntry("Success", "Initialised new project.")
    self.update()

  def saveProject(self): # TODO
    '''Prompt to save project'''
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptSave)
    fd.setFileMode(QFileDialog.AnyFile)
    fd.setNameFilters(["3-D Project (*.3dproj)"])
    if fd.exec_():
      fn = fd.selectedFiles()[0]
      self.S.save(fn)
      self.logEntry("Success", "Saved project to %s"%fn)

  def openProject(self): # TODO
    '''Prompt to open project'''
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFile)
    fd.setNameFilters(["3-D Project (*.3dproj)", "Any File (*.*)"])
    if fd.exec_():
      fn = fd.selectedFiles()[0]
      self.newProject(silent=True)
      try:
        self.S.load(fn)
      except IOError:
        self.logEntry("Error", "Unable to fully load from %s"%fn)
      else:
        self.logEntry("Success", "Fully loaded from %s"%fn)

  def loadMeshes(self):
    '''Prompt to load mesh files'''
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters([r"Wavefront Object files (*.obj)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        try:
          self.addAsset(self.R.loadMesh(fn))
        except:
          self.logEntry("Error", "Bad mesh file: %s"%fn)
        else:
          self.logEntry("Success", "Loaded mesh from %s"%fn)

  def loadTextures(self):
    '''Prompt to load texture files'''
    fd = QFileDialog()
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters(["Images (*.bmp;*.png;*.jpg)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        try:
          self.addAsset(self.R.loadTexture(fn))
        except:
          self.logEntry("Error", "Bad image file: %s"%fn)
        else:
          self.logEntry("Success", "Loaded texture from %s"%fn)

  def exportImage(self):
    '''Prompt to export image in a size'''
    M = Modal(self)
    M.setWindowTitle("Export Image")
    layout = QGridLayout()
    M.setLayout(layout)

    current_dims = self.gl.dims

    # DIMENSIONS GROUP BOX
    dimBox = QGroupBox("Dimensions")
    layout.addWidget(dimBox, 0,0, 1,1)
    dimLayout = QFormLayout()
    dimBox.setLayout(dimLayout)
    width = QSpinBox(minimum=1, maximum=10000)
    width.setValue(current_dims[0])
    height = QSpinBox(minimum=1, maximum=10000)
    height.setValue(current_dims[1])
    dimLayout.addRow("Width", width)
    dimLayout.addRow("Height", height)

    # CONFIRMATION BUTTON
    export = QPushButton(text="Export")
    layout.addWidget(export, 1,0, 1,1)

    def tryExport():
      w, h = width.value(), height.value()
      # Yes, resize the ACTUAL gl widget. This is the only way.
      self.gl.resize(w, h) # It won't show up anyway.
      self.gl.paintGL()
      pixels = glReadPixels(0,0, w,h, GL_RGBA, GL_UNSIGNED_BYTE)
      self.gl.resize(*current_dims)
      self.gl.paintGL()
      # left-to-right, bottom-to-top 2-D byte data
      # ---3--->
      # ---2--->
      # ---1--->
      # ---0--->
      # needs to be flipped top to bottom at the end to
      # conform to PIL's standard:
      # ---0--->
      # ---1--->
      # ---2--->
      # ---3--->

      im = Image.frombytes("RGBA", (w, h), pixels).transpose(Image.FLIP_TOP_BOTTOM)
      fd = QFileDialog()
      fd.setAcceptMode(QFileDialog.AcceptSave)
      fd.setFileMode(QFileDialog.AnyFile)
      fd.setNameFilters(["PNG Image (*.png)"])
      if fd.exec_():
        fn = fd.selectedFiles()[0]
        try:
          im.save(fn, "PNG")
        except:
          self.logEntry("Error", "Could not export image to %s"%fn)
        else:
          self.logEntry("Success", "Exported image to %s"%fn)

    export.clicked.connect(tryExport)
    M.exec_()

  def makeModels(self):
    '''Shows modal for making models'''
    M = Modal(self)
    M.setWindowTitle("Make Models")
    layout = QGridLayout()
    M.setLayout(layout)

    # ASSET GROUP BOX
    assetBox = QGroupBox("Assets")
    layout.addWidget(assetBox, 0,0, 2,1)
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    mList = copyAssetList(self.meshList)
    assetLayout.addRow("Mesh", mList)
    tList = copyAssetList(self.texList)
    assetLayout.addRow("Texture", tList)

    # POSE GROUP BOX
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

    # MATERIAL GROUP BOX
    matBox = QGroupBox("Material")
    layout.addWidget(matBox, 1,1, 1,1)
    matLayout = QFormLayout()
    matBox.setLayout(matLayout)
    shininess = QDoubleSpinBox(minimum=0, maximum=2147483647)
    matLayout.addRow("Shininess", shininess)

    # CUSTOMISATION GROUP BOX
    custBox = QGroupBox("Customization")
    layout.addWidget(custBox, 2,0, 1,1)
    custLayout = QFormLayout()
    custBox.setLayout(custLayout)
    name = QLineEdit(text="model0")
    custLayout.addRow("Name", name)

    def tryMakeModel(): # Attempt to construct Model from selected settings
      m = mList.selectedItems()
      t = tList.selectedItems()
      if not (len(m) and len(t)):
        self.logEntry("Error", "Please select a mesh and a texture.")
        return
      mesh = m[0].asset
      tex = t[0].asset
      pos = Point(x.value(), y.value(), z.value())
      rot = Rot(pi*rx.value()/180, pi*ry.value()/180, pi*rz.value()/180)
      model = Model(mesh, tex, shininess=shininess.value(),
                    pos=pos, rot=rot, scale=scale.value(),
                    name=name.text())
      self.addRend(model)
      self.logEntry("Success", "Made model.")

    make = QPushButton(text="Make Model")
    make.clicked.connect(tryMakeModel)
    layout.addWidget(make, 2,1, 1,1)

    def testValid(): # Update the button that constructs the model (enabled or disabled)
      # there should be at least one selected model and texture
      make.setEnabled(len(mList.selectedItems()) and len(tList.selectedItems()))

    mList.itemClicked.connect(testValid)
    tList.itemClicked.connect(testValid)
    testValid()
    M.resize(500, 500)
    M.exec_() # show the modal

  def makeLights(self):
    '''Shows modal for making lights--NOT IMPLEMENTED'''
    pass

  def initEditPane(self):
    '''Initialises the edit pane'''
    self.initCamEdit()
    self.initSelEdit()

  def initCamEdit(self):
    '''Initialises the camera tab on the edit pane'''
    L = self.camEditLayout = QVBoxLayout()
    self.camEdit.setLayout(L)

    x = self.camEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.camEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.camEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.camEdit_rx = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    ry = self.camEdit_ry = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    rz = self.camEdit_rz = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    fovy = self.camEdit_fovy = QDoubleSpinBox(minimum=0.01, maximum=179.99, value=60)
    zoom = self.camEdit_zoom = QDoubleSpinBox(minimum=0.01, maximum=2147483647, value=1)
    for setting in [x, y, z, rx, ry, rz, fovy, zoom]:
      setting.valueChanged.connect(self.camEditUpdate)

    poseBox = QGroupBox("Pose")
    L.addWidget(poseBox)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Pan", ry)
    poseLayout.addRow("Tilt", rx)
    poseLayout.addRow("Roll", rz)

    persBox = QGroupBox("Perspective")
    L.addWidget(persBox)
    persLayout = QFormLayout()
    persBox.setLayout(persLayout)
    persLayout.addRow("FOV", fovy)
    persLayout.addRow("Zoom", zoom)
    
    self.updateCamEdit()

  def initSelEdit(self):
    '''Initialises all layouts for the Selected tab of the Edit pane.'''
    #===NIL===
    L = QVBoxLayout()
    info = QLabel(text="No object selected.")
    L.addWidget(info)
    L.setAlignment(info, Qt.AlignCenter)
    W = self.nilEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===TEXTURE===
    L = QVBoxLayout()
    change = QPushButton(text="Change")
    delete = QPushButton(text="Delete")
    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(change)
    L.addWidget(delete)
    W = self.texEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===MESH===
    L = QVBoxLayout()
    change = QPushButton(text="Change")
    delete = QPushButton(text="Delete")
    cullbackface = self.meshEdit_cullbackface = QCheckBox(text="Watertight", tristate=False)
    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    cullbackface.stateChanged.connect(self.updateSelected)
    L.addWidget(change)
    L.addWidget(delete)
    L.addWidget(cullbackface)
    W = self.meshEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===MODEL===
    L = QVBoxLayout()
    
    change = QPushButton(text="Change")
    delete = QPushButton(text="Delete")
    x = self.modelEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.modelEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.modelEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.modelEdit_rx = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    ry = self.modelEdit_ry = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    rz = self.modelEdit_rz = QSlider(Qt.Horizontal, minimum=-180, maximum=180)
    scale = self.modelEdit_scale = QDoubleSpinBox(minimum=0, maximum=2147483647)
    shininess = self.modelEdit_shininess = QDoubleSpinBox(minimum=0, maximum=2147483647)

    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(change)
    L.addWidget(delete)

    poseBox = QGroupBox("Pose")
    L.addWidget(poseBox)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Yaw", ry)
    poseLayout.addRow("Pitch", rx)
    poseLayout.addRow("Roll", rz)
    poseLayout.addRow("Scale", scale)

    matBox = QGroupBox("Material")
    L.addWidget(matBox)
    matLayout = QFormLayout()
    matBox.setLayout(matLayout)
    matLayout.addRow("Shininess", shininess)

    for setting in [x,y,z, rx,ry,rz, scale, shininess]:
      setting.valueChanged.connect(self.updateSelected)

    W = self.modelEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===UPDATE===
    self.updateSelEdit()

  def updateCamEdit(self): # true settings -> displayed settings
    '''Updates the displayed settings for the camera'''
    x, y, z = self.UE.camera.pos
    rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in self.UE.camera.rot)
    fovy = self.UE.camera.fovy
    zoom = self.UE.camera.zoom
    for setting, var in [(self.camEdit_x, x),
                         (self.camEdit_y, y),
                         (self.camEdit_z, z),
                         (self.camEdit_rx, rx),
                         (self.camEdit_ry, ry),
                         (self.camEdit_rz, rz),
                         (self.camEdit_fovy, fovy),
                         (self.camEdit_zoom, zoom)]:
      setting.blockSignals(True)
      setting.setValue(var)
      setting.blockSignals(False)
    return

  def camEditUpdate(self): # displayed settings -> true settings
    '''Updates the camera variables from the displayed settings'''
    pos = Point(self.camEdit_x.value(),
                self.camEdit_y.value(),
                self.camEdit_z.value())
    rot = Rot(pi*self.camEdit_rx.value()/180,
              pi*self.camEdit_ry.value()/180,
              pi*self.camEdit_rz.value()/180)
    fovy = self.camEdit_fovy.value()
    zoom = self.camEdit_zoom.value()
    self.R.configCamera(pos=pos, rot=rot, fovy=fovy, zoom=zoom)

  def reinitSelected(self):
    '''Prompts user to reinitialise the selected object from different files/assets'''
    pass

  def deleteSelected(self):
    '''Deletes selected object'''
    listDict = {Mesh: self.meshList,
                Tex: self.texList,
                Model: self.modelList,
                Light: self.lightList}
    try:
      l = listDict[type(self.selected)]
    except KeyError:
      return
    for i in range(l.count()):
      item = l.item(i)
      if isinstance(l, AssetList) and item.asset is self.selected:
        l.remove(item)
        break
      elif isinstance(l, RendList) and item.rend is self.selected:
        l.remove(item)
        break
    self.selected = None
    self.update()

  def updateSelected(self):
    '''Updates selected object from displayed settings'''
    S = self.selected
    if type(self.selected) is Mesh:
      self.meshEdit_cullbackface.setTristate(False)
      S.cullbackface = self.meshEdit_cullbackface.isChecked()
      
    elif type(self.selected) is Model:
      S.pos = Point(self.modelEdit_x.value(),
                    self.modelEdit_y.value(),
                    self.modelEdit_z.value())
      S.rot = Rot(pi*self.modelEdit_rx.value()/180,
                  pi*self.modelEdit_ry.value()/180,
                  pi*self.modelEdit_rz.value()/180)
      S.scale = self.modelEdit_scale.value()
      S.shininess = self.modelEdit_shininess.value()

  def switchSelEdit(self, objType):
    '''Updates the stacked widget in the "Selected" tab of the edit pane'''
    widgetDict = {Mesh: self.meshEdit,
                  Tex: self.texEdit,
                  Model: self.modelEdit}
    if objType in widgetDict:
      self.selEdit.setCurrentWidget(widgetDict[objType])
    else:
      self.selEdit.setCurrentWidget(self.nilEdit)

  def updateSelEdit(self):
    '''Switch to relevent layout and put in correct settings to display'''
    S = self.selected
    self.switchSelEdit(type(S))
    if type(S) is Mesh:
      cullbackface = S.cullbackface
      self.meshEdit_cullbackface.setCheckState(cullbackface)
      self.meshEdit_cullbackface.setTristate(False)
      
    elif type(S) is Model:
      x, y, z = S.pos
      rx, ry, rz = S.rot
      rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in S.rot)
      scale = S.scale
      shininess = S.shininess
      for setting, var in [(self.modelEdit_x, x),
                           (self.modelEdit_y, y),
                           (self.modelEdit_z, z),
                           (self.modelEdit_rx, rx),
                           (self.modelEdit_ry, ry),
                           (self.modelEdit_rz, rz),
                           (self.modelEdit_scale, scale),
                           (self.modelEdit_shininess, shininess)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)
    self.selEdit.update()

  def select(self, obj):
    '''Selects an object for editing'''
    self.selected = obj
    self.updateSelEdit()

  def update(self):
    '''Overload: update to display correct features'''
    self.updateCamEdit()
    self.updateSelEdit()
    super().update()

  def closeEvent(self, event):
    self.S.update()
    print("Goodbye!")

if __name__ == "__main__":
  window = QApplication(sys.argv)
  app = MainApp()
  def tryexec():
    try:
      return window.exec_()
    except Exception as e:
      print(e)
      return 1
  sys.exit(tryexec())

