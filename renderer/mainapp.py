#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
gui.py

Makes the graphical application and runs the main systems
'''

from all_modules import *

from rotpoint import Rot, Point
from asset import id_gen, Asset, Mesh, Tex, Bulb
from engine import Renderable, Model, Lamp, Directory, Link, initEngine, TreeError
import engine
from userenv import UserEnv
from remote import Remote
from saver import Saver

def basePosRot(truePos, trueRot, sel):
  if not isinstance(sel, Renderable):
    return truePos, trueRot
  elif isinstance(sel, Directory):
    return sel.getBasePos(truePos), sel.getBaseRot(trueRot)
  else:
    return sel.getDirBasePos(truePos), sel.getDirBaseRot(trueRot)

def shortfn(fn):
  return os.path.split(fn)[1]

def cyclamp(x, R): # Like modulo, but based on custom range
  a, b = R
  return (x-a)%(b-a) + a

def rrggbb(r,g,b):
  '''Takes r,g,b floats and returns color code in #rrggbb format'''
  rr = "%02x"%int(r*255)
  gg = "%02x"%int(g*255)
  bb = "%02x"%int(b*255)
  return "#%s%s%s"%(rr,gg,bb)

def getTimestamp():
  return strftime("UTC %y-%m-%d %H:%M:%S", gmtime())

ROT_DELTAS = {Qt.Key_Left: (0, -2, 0),
              Qt.Key_Right: (0, 2, 0),
              Qt.Key_Down: (-2, 0, 0),
              Qt.Key_Up: (2, 0, 0),
              Qt.Key_Comma: (0, 0, -2),
              Qt.Key_Period: (0, 0, 2),
              Qt.Key_Less: (0, 0, -2),
              Qt.Key_Greater: (0, 0, 2)}

POS_DELTAS = {Qt.Key_A: (-5, 0, 0),
              Qt.Key_D: (5, 0, 0),
              Qt.Key_S: (0, 0, 5),
              Qt.Key_W: (0, 0, -5),
              Qt.Key_F: (0, -5, 0),
              Qt.Key_R: (0, 5, 0)}

def keyModFlags():
  return QCoreApplication.instance().keyboardModifiers()

def copyObjList(ql):
  cql = QListWidget()
  for i in range(ql.count()):
    item = ql.item(i)
    citem = QListWidgetItem()
    citem.obj = item.obj
    citem.setIcon(item.icon())
    citem.setBackground(item.background())
    citem.setText(item.text())
    cql.addItem(citem)
  cql.find = ql.find
  return cql

def loadQTable(qtable, arr):
  qtable.clear()
  qtable.setRowCount(len(arr))
  qtable.setColumnCount(max([len(row) for row in arr]))
  for rn, row in enumerate(arr):
    for cn, element in enumerate(row):
      item = QTableWidgetItem(str(element))
      qtable.setItem(rn, cn, item)

class BetterSlider(QWidget):
  valueChanged = pyqtSignal()
  
  def __init__(self, slider, suffix=""):
    super().__init__()
    self.blocking = False
    spinner = QSpinBox(minimum=slider.minimum(), maximum=slider.maximum(), value=slider.value(), suffix=suffix)
    def setValue(n):
      slider.blockSignals(True)
      spinner.blockSignals(True)
      slider.setValue(n)
      spinner.setValue(n)
      slider.blockSignals(False)
      spinner.blockSignals(False)
      if not self.blocking:
        self.valueChanged.emit()
    slider.valueChanged.connect(setValue)
    spinner.valueChanged.connect(setValue)
    L = QHBoxLayout()
    L.setContentsMargins(0, 0, 0, 0)
    self.setLayout(L)
    L.addWidget(slider)
    L.addWidget(spinner)
    self.setValue = slider.setValue
    self.value = slider.value

  def blockSignals(self, doBlock):
    self.blocking = doBlock

class glWidget(QGLWidget):
  '''OpenGL+QT widget'''
  def __init__(self, *args, **kwargs):
    QGLWidget.__init__(self, *args, **kwargs)
    self.parent = self.parentWidget()
    self.dims = (100, 100)
    self.aspect = 1.0
    self.refresh_rate = 30
    self.refresh_period = ceil(1000/self.refresh_rate)
    self.timer = QTimer()
    self.timer.setInterval(self.refresh_period)
    self.timer.timeout.connect(self.onTick)
    self.heldKeys = set()
    self.lastt = time.time()
    self.dt = 0
    self.timer.start()
    self.setFocusPolicy(Qt.StrongFocus)
    self.setMouseTracking(True)

    self.sel_dv = None # dxyz's for camera to each selected rend
    self.sel_dr = None # distance from camera to monoselected
    self.mousePos = None
    self.dragging = False
    self.cam_rot = None

  def initializeGL(self):
    initEngine()

  def paintGL(self):
    self.parent.R.renderScene(aspect=self.aspect)

  def resizeGL(self, w, h):
    self.dims = w, h
    self.aspect = w/h
    self.parent.R.resizeViewport(w,h)
    super().resizeGL(w, h)

  def keyPressEvent(self, event):
    if event.key() == Qt.Key_Escape:
      self.parent.select(None)
    elif (event.key() == Qt.Key_Shift):
      if isinstance(engine.monoselected, Renderable):
        self.parent.R.lookAt(engine.monoselected)
      else:
        self.parent.R.lookAt(Point(0, 0, 0)) # look at origin
      self.update()
    self.heldKeys.add(event.key())

  def keyReleaseEvent(self, event):
    self.heldKeys.discard(event.key())

  def onTick(self): # custom: scheduled to call at regular intervals
    now = time.time()
    self.dt = now - self.lastt
    self.lastt = now
    if self.handleHeldKeys():
      self.update()
      self.parent.updateCamEdit()
      self.parent.updateSelEdit()
      self.parent.updateSelected()

  def handleHeldKeys(self):
    cam = self.parent.UE.camera
    sel = engine.monoselected
    selRends = [obj for obj in engine.selected if isinstance(obj, Renderable)]
    
    count = 0
    dt = self.dt

    dr = [0.0, 0.0, 0.0]
    rotated = False
    for k, (drx, dry, drz) in ROT_DELTAS.items():
      if k in self.heldKeys:
        rotated = True
        count += 1
        dr[0] += drx
        dr[1] += dry
        dr[2] += drz

    if rotated:
      drx, dry, drz = dr
      if selRends and (keyModFlags() & Qt.ShiftModifier):
        self.parent.R.changeRendRot(engine.monoselected, dt*drx, dt*dry, dt*drz)
      else:
        self.parent.R.changeCameraRot(dt*drx, dt*dry, dt*drz)

    dxyz = [0.0, 0.0, 0.0]
    moved = False
    for k, (dx, dy, dz) in POS_DELTAS.items():
      if k in self.heldKeys:
        moved = True
        count += 1
        dxyz[0] += dx
        dxyz[1] += dy
        dxyz[2] += dz
        
    if moved:
      dv = Point(*dxyz)
      dp = dt * cam.rot.get_transmat(invert=True) * dv
      if selRends and (keyModFlags() & Qt.ShiftModifier):
        if self.sel_dv is None:
          self.parent.R.lookAt(engine.monoselected)
          self.sel_dv = dict()
          for rend in selRends:
            selpos = rend.getTruePos()
            self.sel_dv[rend] = selpos - cam.pos
        cam.pos += dp
        for rend in selRends:
          new_selpos = cam.pos + self.sel_dv[rend]
          self.parent.R.moveRendTo(rend, *new_selpos)
      else:
        cam.pos += dp
        
    if not moved:
      self.sel_dv = None

    return count

  def wheelEvent(self, event):
    self.setFocus()
    cam = self.parent.UE.camera
    sel = engine.monoselected
    if keyModFlags() & Qt.ShiftModifier:
      if isinstance(sel, Renderable):
        selpos = sel.getTruePos()
      else:
        selpos = Point(0, 0, 0)
      dx0, dy0, dz0 = cam.pos - selpos
      dist0 = (dx0**2+dy0**2+dz0**2)**0.5
      dist = min(max(0.1, dist0*10**(-event.angleDelta().y()/(360*10))), 2147483647.0)
      cam.pos = selpos - (cam.rot.get_forward_vector(invert=True)*dist)
      self.sel_dr = dist
    else:
      cam.zoom *= 10**(event.angleDelta().y()/(360*10))
      cam.zoom = min(max(1.0, cam.zoom), 1000.0)
    self.parent.updateCamEdit()
    self.update()

  def mousePressEvent(self, event):
    self.mousePos = event.x(), event.y()
    self.cam_rot = self.parent.UE.camera.rot
    self.dragging = True

  def mouseMoveEvent(self, event):
    cam = self.parent.UE.camera
    sel = engine.monoselected
    if self.dragging:
      if keyModFlags() & Qt.ShiftModifier:
        if isinstance(sel, Renderable):
          selpos = sel.getTruePos()
        else:
          selpos = Point(0.0, 0.0, 0.0)
        if False: # TODO: if mousePos is close to center, rotate monoselected instead of the camera around the monoselected
          pass
        else:
          if self.sel_dr is None:
            self.parent.R.lookAt(selpos)
            self.sel_dr = sum(dn**2 for dn in selpos - cam.pos)**0.5
          # shift the angle appropriately
          X, Y = self.mousePos
          dX, dY = event.x() - X, event.y() - Y
          cam.rot = Rot(-dY/100, dX/100, 0)*self.cam_rot
          # position the camera such that it remains at the same distance
          cam.pos = selpos - cam.rot.get_transmat(invert=True)*Point(0, 0, -self.sel_dr)
          
      else:
        X, Y = self.mousePos
        dX, dY = event.x() - X, event.y() - Y
        cam.rot = Rot(dY/100, -dX/100, 0)*self.cam_rot
        
      self.parent.R.rectifyCamera()
      self.update()

  def mouseReleaseEvent(self, event):
    self.dragging = False
    self.sel_dr = None
    

class ObjList(QListWidget):
  '''QListWidget of environment objects (Mesh, Tex, Model, Lamp)'''
  iconDict = dict() # obj type --> icon
  bgDict = dict() # obj type --> bg brush
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.parent = self.parentWidget()
    self.setSortingEnabled(True)
    self.setSelectionMode(3)
    self.itemClicked.connect(self.onItemClicked)
    self.itemDoubleClicked.connect(self.onItemDoubleClicked)
    self.itemSelectionChanged.connect(self.onItemSelectionChanged)

  def onItemClicked(self, item):
    if isinstance(item.obj, Renderable):
      item.obj.visible = item.checkState()==2
    self.onItemSelectionChanged()

  def onItemDoubleClicked(self, item):
    if isinstance(item.obj, Renderable):
      self.parent.R.lookAt(item.obj)

  def onItemSelectionChanged(self):
    items = self.selectedItems()
    engine.selected = set([item.obj for item in items])
    if items:
      self.parent.select(items[0].obj)
    else:
      self.parent.select(None)

  def add(self, obj):
    new_item = QListWidgetItem(obj.name)
    new_item.obj = obj
    if type(obj) in self.iconDict:
      new_item.setIcon(self.iconDict[type(obj)])
##    if type(obj) in self.bgDict:
##      new_item.setBackground(self.bgDict[type(obj)])
    self.addItem(new_item)
    if isinstance(obj, Renderable):
      flags = new_item.flags()|Qt.ItemIsUserCheckable
      if type(obj) in [Model, Lamp, Link]:
        flags |= Qt.ItemNeverHasChildren
      if isinstance(obj, Directory):
        flags |= Qt.ShowIndicator
      new_item.setFlags(flags)
      new_item.setCheckState(obj.visible*2)
    return new_item

  def keyPressEvent(self, event):
    k = event.key()
    if k == Qt.Key_Delete:
      for item in self.selectedItems():
        self.parent.delete(item.obj)
      self.parent.update()

  def update(self):
    for i in range(self.count()):
      item = self.item(i)
      item.setText(item.obj.name)
      if isinstance(item.obj, Renderable):
        item.setCheckState(item.obj.visible*2)

  def find(self, obj):
    for i in range(self.count()):
      item = self.item(i)
      if item.obj is obj:
        return i

  def take(self, obj):
    return self.takeItem(self.find(obj))

class ObjNode(QTreeWidgetItem):
  objTypenameDict = {Mesh: "Mesh",
                     Tex: "Texture",
                     Bulb: "Bulb",
                     Model: "Model",
                     Lamp: "Lamp",
                     Directory: "GROUP",
                     Link: "SYMLINK"}
  iconDict = dict()
  def __init__(self, obj, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
    self.obj = obj
    self.setText(0, obj.name)
    self.setText(1, self.objTypenameDict[type(obj)])
    if type(obj) in self.iconDict:
      self.setIcon(0, self.iconDict[type(obj)])
##    if type(obj) in self.fgDict:
##      self.setForeground(0, self.fgDict[type(obj)])
    if isinstance(obj, Renderable):
      self.setFlags(self.flags()|Qt.ItemIsUserCheckable)
      self.setCheckState(2, obj.visible*2)
    if isinstance(obj, Directory):
      self.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

  def __lt__(self, node, typeOrder=[Directory, Link, Lamp, Model, Tex, Mesh]):
    column = self.treeWidget().sortColumn()
    if column == 1:
      return typeOrder.index(type(self.obj)) < typeOrder.index(type(node.obj))
    elif column == 2:
      return (isinstance(self.obj, Renderable)
          and isinstance(node.obj, Renderable)
          and self.obj.visible < node.obj.visible)
    else:
      return self.obj.name < node.obj.name
    
  def find(self, obj):
    for i in range(self.childCount()):
      child = self.child(i)
      if child.obj is obj:
        return i

  def take(self, obj):
    i = self.find(obj)
    return self.takeChild(i)

  def update(self):
    self.setText(0, self.obj.name)
    if isinstance(self.obj, Renderable):
      self.setCheckState(2, self.obj.visible*2)
    for i in range(self.childCount()):
      self.child(i).update()

class ObjTree(QTreeWidget):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setSelectionMode(QAbstractItemView.SingleSelection)
    self.setDragEnabled(True)
    self.viewport().setAcceptDrops(True)
    self.setDropIndicatorShown(False)
    self.setDragDropMode(QAbstractItemView.InternalMove)
    self.parent = self.parentWidget()
    self.objNodeDict = dict() # asset/renderable --> node
    self.groupNums = id_gen()
    self.itemClicked.connect(self.onItemClicked)
    self.itemSelectionChanged.connect(self.onItemSelectionChanged)
    self.setSortingEnabled(True)
    
  def add(self, obj, directory=None):
    '''Adds ObjNode to a directory'''
    node = self.new(obj, directory)
    if isinstance(obj, Directory):
      for child in obj.rends:
        self.add(child, directory=obj)
    return node

  def find(self, obj):
    '''Returns index of top level item that matches obj'''
    for i in range(self.topLevelItemCount()):
      item = self.topLevelItem(i)
      if item.obj is obj:
        return i

  def take(self, obj):
    node = self.objNodeDict[obj]
    parent = node.parent()
    if parent is None: # this node is top level
      node = self.takeTopLevelItem(self.find(obj))
    else:
      node = parent.take(obj)
    return node

  def delete(self, obj):
    self.take(obj)
    del self.objNodeDict[obj]

  def new(self, obj, directory):
    node = self.objNodeDict[obj] = ObjNode(obj)
    if directory is None:
      self.addTopLevelItem(node)
    else:
      self.objNodeDict[directory].addChild(node)
    self.update()
    return node

  def move(self, obj, directory):
    '''Moves obj to directory'''
    node = self.take(obj)
    if directory is None:
      self.addTopLevelItem(node)
    else:
      self.objNodeDict[directory].addChild(node)
    self.update()
    return node

  def update(self):
    for i in range(self.topLevelItemCount()):
      self.topLevelItem(i).update()

  def select(self, obj):
    self.blockSignals(True)
    self.selectionModel().clearSelection()
    if obj in self.objNodeDict:
      self.objNodeDict[obj].setSelected(True)
      self.showObj(obj)
    self.blockSignals(False)

  def showObj(self, obj):
    node = self.objNodeDict[obj].parent()
    while node is not None:
      node.setExpanded(True)
      node = node.parent()

  def getCurrentDir(self):
    selItems = self.selectedItems()
    if selItems:
      sel = selItems[0].obj
      if isinstance(sel, Directory):
        return sel
      parentItem = self.objNodeDict[sel].parent()
      if parentItem is None:
        return None
      return parentItem.obj
    return None

  def onItemClicked(self, item):
    if isinstance(item.obj, Renderable):
      item.obj.visible = item.checkState(2)==2
      self.parent.update()

  def onItemSelectionChanged(self):
    selItems = self.selectedItems()
    if selItems:
      self.parent.select(selItems[0].obj)
      if isinstance(selItems[0].obj, Renderable):
        self.parent.R.lookAt(selItems[0].obj)

  def keyPressEvent(self, event):
    cam = self.parent.UE.camera
    selItems = self.selectedItems()
    if selItems:
      selItem = selItems[0]
      sel = selItem.obj
    else:
      selItem = None
      sel = None
    k = event.key()
    if k == Qt.Key_Escape:
      self.parent.select(None)
    elif k == Qt.Key_Return:
      selItems = self.selectedItems()
      if selItems:
        selItems[0].setExpanded(not selItems[0].isExpanded())
    elif k == Qt.Key_Left:
      self.parent.selectParent()
    elif k == Qt.Key_Right:
      self.parent.selectFirstChild()
    elif k == Qt.Key_Up:
      self.parent.selectPrevSibling()
    elif k == Qt.Key_Down:
      self.parent.selectNextSibling()

  def focusOutEvent(self, event):
    self.itemDragged = None

  def mousePressEvent(self, event):
    index = self.indexAt(event.pos())
    if (index.row() == -1):
      self.parent.select(None)
    else:
      self.itemDragged = self.itemAt(event.pos())
      super().mousePressEvent(event)

  def mouseReleaseEvent(self, event):
    self.itemDragged = None
    super().mouseReleaseEvent(event)

  def dropEvent(self, event):
    index = self.indexAt(event.pos())
    if (index.row() == -1):
      return
    item = self.itemAt(event.pos())
    if isinstance(item.obj, Directory) or self.itemDragged is None:
      self.parent.move(self.itemDragged.obj, item.obj)
    else:
      self.parent.move(self.itemDragged.obj, item.obj.parent)
  
class Modal(QDialog):
  '''A dialog box that grabs focus until closed'''
  def __init__(self, *args, **kwargs):
    QDialog.__init__(self, *args, **kwargs)
    self.setModal(True)

def YNPrompt(parent, title="YN", text="Do action?", factory=QMessageBox.question):
  reply = factory(parent, title, text,
                  QMessageBox.Yes|QMessageBox.No, QMessageBox.Yes)
  return reply == QMessageBox.Yes

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

  def update(self):
    self.resize(self.currentWidget().sizeHint())

class VerticalScrollArea(QScrollArea):
  '''A scroll area that scrolls vertically but acts normally horizontally'''
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
##    self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

  def sizeHint(self):
    W = self.widget()
    if W:
      return QSize(W.sizeHint().width() + self.verticalScrollBar().width()+5, 0)
    return QSize(0, 0)

  def minimumSizeHint(self):
    W = self.widget()
    if W:
      return QSize(W.sizeHint().width() + self.verticalScrollBar().width()+5, 0)
    return QSize(0, 0)

def CBrush(hexcolor):
  qc = QColor()
  qc.setNamedColor(hexcolor)
  return QBrush(qc)

class MainApp(QMainWindow):
  '''Main Application, uses QT'''
  def __init__(self, parent=None):
    self.UE = UserEnv()
    self.R = Remote(self.UE)

    super().__init__(parent)
    self._init_style()
    self._load_assets()
    self._make_widgets()
    self._init_hotkeys()
    self.resize(1000, 500)
    self.setWindowIcon(self.icons["Model"])
    self.setWindowTitle(APPNAME)
    self.show()
    self.newProject(silent=True, base=True)
    self.S = Saver(self)
    
    self.setAcceptDrops(True)
  
  def _init_style(self):
    self.setStyleSheet(open("./style.qss").read())

  def _load_assets(self):
    self.icons = dict()
    for name, stdicon in [("Info", QStyle.SP_MessageBoxInformation),
                          ("Success", QStyle.SP_DialogApplyButton),
                          ("Warning", QStyle.SP_MessageBoxWarning),
                          ("Error", QStyle.SP_MessageBoxCritical),
                          ("Question", QStyle.SP_MessageBoxQuestion),
                          ("Save", QStyle.SP_DialogSaveButton),
                          ("Open", QStyle.SP_DialogOpenButton),
                          ("New", QStyle.SP_DialogResetButton),
                          ("Delete", QStyle.SP_DialogDiscardButton),
                          ("Import", QStyle.SP_ArrowDown),
                          ("Export", QStyle.SP_ArrowUp),
                          ("Ok", QStyle.SP_DialogOkButton),
                          ("Form", QStyle.SP_FileDialogDetailedView),
                          ("File", QStyle.SP_FileIcon),
                          ("List", QStyle.SP_FileDialogListView),
                          ("Folder", QStyle.SP_DirIcon),
                          ("Window", QStyle.SP_TitleBarNormalButton)]:
      self.icons[name] = self.style().standardIcon(stdicon)

    for name, fn in [("Mesh", r"./assets/icons/mesh.png"),
                     ("Texture", r"./assets/icons/texture.png"),
                     ("Bulb", r"./assets/icons/bulb.png"),
                     ("Model", r"./assets/icons/model.png"),
                     ("Lamp", r"./assets/icons/lamp.png"),
                     ("Object Group", r"./assets/icons/objectgroup.png"),
                     ("Link", r"./assets/icons/link.png"),
                     ("3D Scene", r"./assets/icons/3dscene.png"),
                     ("Scene", r"./assets/icons/scene.png"),
                     ("Edit", r"./assets/icons/edit.png"),
                     ("Camera", r"./assets/icons/camera.png"),
                     ("Selected", r"./assets/icons/selected.png"),
                     ("Image File", r"./assets/icons/imagefile.png"),
                     ("Color", r"./assets/icons/color.png")]:
      self.icons[name] = QIcon(fn)

    self.fonts = dict()
    self.fonts["heading"] = QFont("Calibri", 16, QFont.Bold)

    iconDict = {Mesh: self.icons["Mesh"],
                Tex: self.icons["Texture"],
                Bulb: self.icons["Bulb"],
                Model: self.icons["Model"],
                Lamp: self.icons["Lamp"],
                Directory: self.icons["Object Group"],
                Link: self.icons["Link"]}
    
    colorDict = {Mesh: CBrush("#e2ffd9"), # light green
                 Tex: CBrush("#eadcff"), # light blue
                 Model: CBrush("#b2fffd"), # light cyan
                 Lamp: CBrush("#ffffc5") # light yellow
                 }

    ObjList.iconDict = ObjNode.iconDict = iconDict
    ObjList.bgDict = ObjNode.fgDict = colorDict

  def _make_widgets(self):
    '''Initialise all widgets'''
    layout = QHBoxLayout()
    self.setLayout(layout)
    
    bar = self.menuBar()
    file = bar.addMenu("&File")
    self.fileMenu_new = QAction(self.icons["New"], "&New")
    self.fileMenu_open = QAction(self.icons["Open"], "&Open...")
    self.fileMenu_openhere = QAction(self.icons["Open"], "Open &here...")
    self.fileMenu_save = QAction(self.icons["Save"], "&Save")
    self.fileMenu_saveas = QAction(self.icons["Save"], "Save &as...")
    self.fileMenu_exportimage = QAction(self.icons["Image File"], "&Export Image")
    self.fileMenu_loadmeshes = QAction(self.icons["Mesh"], "Load &Meshes")
    self.fileMenu_loadtextures = QAction(self.icons["Texture"], "Load &Textures")
    file.addAction(self.fileMenu_new)
    file.addAction(self.fileMenu_open)
    file.addAction(self.fileMenu_openhere)
    file.addSeparator()
    file.addAction(self.fileMenu_save)
    file.addAction(self.fileMenu_saveas)
    file.addSeparator()
    file.addAction(self.fileMenu_loadmeshes)
    file.addAction(self.fileMenu_loadtextures)
    file.addSeparator()
    file.addAction(self.fileMenu_exportimage)
    asset = bar.addMenu("&Asset")
    self.assetMenu_makebulb = QAction(self.icons["Bulb"], "Make &Bulb")
    asset.addAction(self.assetMenu_makebulb)
    scene = bar.addMenu("&Scene")
    self.sceneMenu_makemodels = QAction(self.icons["Model"], "Make &Models")
    self.sceneMenu_makelamps = QAction(self.icons["Lamp"], "Make &Lamps")
    self.sceneMenu_makegroups = QAction(self.icons["Object Group"], "Make &Groups")
    self.sceneMenu_quickgroup = QAction(self.icons["Object Group"], "Make Group &Here")
    scene.addAction(self.sceneMenu_makemodels)
    scene.addAction(self.sceneMenu_makelamps)
    scene.addAction(self.sceneMenu_makegroups)
    scene.addAction(self.sceneMenu_quickgroup)
    view = bar.addMenu("&View")
    self.viewMenu_env = QAction(self.icons["Scene"], "E&nvironment", checkable=True)
    self.viewMenu_edit = QAction(self.icons["Edit"], "&Edit", checkable=True)
    self.viewMenu_log = QAction(self.icons["Info"], "&Log", checkable=True)
    view.addAction(self.viewMenu_env)
    view.addAction(self.viewMenu_edit)
    view.addAction(self.viewMenu_log)
    helpMenu = bar.addMenu("&Help")
    self.helpMenu_help = QAction(self.icons["Question"], "&Help")
    helpMenu.addAction(self.helpMenu_help)

    self.gl = glWidget(self)
    self.setCentralWidget(self.gl)
    
    self.envPane = QDockWidget("Environment", self)
    self.env = ResizableTabWidget(movable=True, tabPosition=QTabWidget.North)
    self.env.setProperty("class", "BigTabs")
    self.meshList = ObjList(self)
    self.texList = ObjList(self)
    self.bulbList = ObjList(self)
    self.modelList = ObjList(self)
    self.lampList = ObjList(self)
    self.rendTree = ObjTree(self)
    self.rendTree.setHeaderLabels(["Name", "Type", "Visible?"])
    self.env.addTab(self.meshList, self.icons["Mesh"], "")
    self.env.addTab(self.texList, self.icons["Texture"], "")
    self.env.addTab(self.bulbList, self.icons["Bulb"], "")
    self.modelList.hide()
    self.lampList.hide()
##    self.env.addTab(self.modelList, self.icons["Model"], "")
##    self.env.addTab(self.lampList, self.icons["Lamp"], "")
    self.env.addTab(self.rendTree, self.icons["3D Scene"], "")
    self.envPane.setWidget(self.env)
    self.envPane.setFloating(False)
    self.addDockWidget(Qt.LeftDockWidgetArea, self.envPane)

    self.editPane = QDockWidget("Edit", self)
    self.edit = ResizableTabWidget(movable=True, tabPosition=QTabWidget.North)
    self.edit.setProperty("class", "BigTabs")
    self.camEdit = QWidget()
    self.camScrollArea = VerticalScrollArea()
    self.selEdit = ResizableStackedWidget()
    self.selEdit.currentChanged.connect(lambda i: self.edit.onCurrentChanged(0))
    self.selScrollArea = VerticalScrollArea()
    self.edit.addTab(self.camScrollArea, self.icons["Camera"], "")
    self.edit.addTab(self.selScrollArea, self.icons["Selected"], "")
    self.editPane.setWidget(self.edit)
    self.initEditPane()
    self.camScrollArea.setWidget(self.camEdit)
    self.selScrollArea.setWidget(self.selEdit)
    self.camScrollArea.setAlignment(Qt.AlignHCenter)
    self.selScrollArea.setAlignment(Qt.AlignHCenter)
    self.addDockWidget(Qt.RightDockWidgetArea, self.editPane)

    self.logPane = QDockWidget("Log", self)
    self.logModel = QStandardItemModel(0,3, self.logPane)
    self.logModel.setHorizontalHeaderLabels(["Type", "Info", "Timestamp"])
    self.log = QTableView()
    self.log.setModel(self.logModel)
    self.log.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.log.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    self.logPane.setWidget(self.log)
    self.addDockWidget(Qt.BottomDockWidgetArea, self.logPane)
    self.logEntry("Info", "Welcome to %s (beta version)"%APPNAME)
    self.logEntry("Info", "Pssst...stalk me on GitHub: github.com/Lax125")

    self.helpPane = QDockWidget("Help", self)
    self.help = QTextEdit(readOnly=True)
    self.help.setFontFamily("Consolas")
    self.help.setText(open("./assets/text/help.txt").read())
    self.helpPane.setWidget(self.help)
    self.addDockWidget(Qt.BottomDockWidgetArea, self.helpPane)
    self.helpPane.setFloating(True)
    self.helpPane.hide()

    self.fileMenu_new.triggered.connect(lambda: self.newProject(base=True))
    self.fileMenu_open.triggered.connect(self.openProject)
    self.fileMenu_openhere.triggered.connect(self.openhereProject)
    self.fileMenu_save.triggered.connect(self.saveProject)
    self.fileMenu_saveas.triggered.connect(self.saveasProject)
    self.fileMenu_exportimage.triggered.connect(self.exportImage)
    self.fileMenu_loadmeshes.triggered.connect(self.loadMeshes)
    self.fileMenu_loadtextures.triggered.connect(self.loadTextures)
    self.assetMenu_makebulb.triggered.connect(self.makeBulb)
    self.sceneMenu_makemodels.triggered.connect(self.makeModels)
    self.sceneMenu_makelamps.triggered.connect(self.makeLamps)
    self.sceneMenu_makegroups.triggered.connect(self.makeGroups)
    self.sceneMenu_quickgroup.triggered.connect(self.quickGroup)
    self.viewMenu_env.triggered.connect(self.curryTogglePane(self.envPane))
    self.viewMenu_edit.triggered.connect(self.curryTogglePane(self.editPane))
    self.viewMenu_log.triggered.connect(self.curryTogglePane(self.logPane))
    self.envPane.visibilityChanged.connect(self.updateMenu)
    self.editPane.visibilityChanged.connect(self.updateMenu)
    self.logPane.visibilityChanged.connect(self.updateMenu)
    self.helpMenu_help.triggered.connect(self.showHelp)

  def _init_hotkeys(self):
    def quickShortcut(keySeq, qaction):
      qaction.setShortcut(QKeySequence(keySeq))
    quickShortcut("Ctrl+N", self.fileMenu_new)
    quickShortcut("Ctrl+O", self.fileMenu_open)
    quickShortcut("Ctrl+Shift+O", self.fileMenu_openhere)
    quickShortcut("Ctrl+S", self.fileMenu_save)
    quickShortcut("Ctrl+Shift+S", self.fileMenu_saveas)
    quickShortcut("Ctrl+E", self.fileMenu_exportimage)
    quickShortcut("Ctrl+M", self.fileMenu_loadmeshes)
    quickShortcut("Ctrl+T", self.fileMenu_loadtextures)
    quickShortcut("Ctrl+B", self.assetMenu_makebulb)

    quickShortcut("Ctrl+Shift+M", self.sceneMenu_makemodels)
    quickShortcut("Ctrl+Shift+L", self.sceneMenu_makelamps)
    quickShortcut("Ctrl+Shift+G", self.sceneMenu_makegroups)
    quickShortcut("Ctrl+G", self.sceneMenu_quickgroup)

    quickShortcut("F1", self.helpMenu_help)

    def quickKeybind(keySeq, func):
      shortcut = QShortcut(QKeySequence(keySeq), self)
      shortcut.activated.connect(func)
    self.keyBind_selectparent = quickKeybind("Alt+Left", self.selectParent)
    self.keyBind_selectfirstchild = quickKeybind("Alt+Right", self.selectFirstChild)
    self.keyBind_selectprevsibling = quickKeybind("Alt+Up", self.selectPrevSibling)
    self.keyBind_selectnextsibling = quickKeybind("Alt+Down", self.selectNextSibling)
    self.keyBind_copyselected = quickKeybind("Ctrl+C", self.copySelected)
    self.keyBind_cutselected = quickKeybind("Ctrl+X", self.cutSelected)
    self.keyBind_deeppasteclipboard = quickKeybind("Ctrl+V", self.deepPasteClipboard)
    self.keyBind_deeppasteselected = quickKeybind("Shift+;", self.deepPasteSelected) # used when moving with Shift
    self.keyBind_shallowpasteclipboard = quickKeybind("Ctrl+Shift+V", self.shallowPasteClipboard)
    self.keyBind_shallowpasteselected = quickKeybind("Shift+'", self.shallowPasteSelected) # used when moving wih Shift
    self.keyBind_deleteselected = quickKeybind("Delete", self.deleteSelected)
    self.keyBind_focuscenter = quickKeybind("/", self.focusCenter)

  def showHelp(self):
    self.helpPane.show()
    self.helpPane.activateWindow()
    self.helpPane.setFocus()

  def focusCenter(self):
    self.activateWindow()
    self.centralWidget().setFocus()

  def updateMenu(self):
    self.viewMenu_env.setChecked(self.envPane.isVisible())
    self.viewMenu_edit.setChecked(self.editPane.isVisible())
    self.viewMenu_log.setChecked(self.logPane.isVisible())

  def curryTogglePane(self, pane):
    def togglePane():
      v = pane.isVisible()
      pane.setVisible(not v)
      self.updateMenu()
    return togglePane

  def logEntry(self, entryType, entryText):
    '''Log an entry into the log pane'''
    assert entryType in ["Info",
                         "Success",
                         "Warning",
                         "Error"]
    etype = QStandardItem(entryType)
    icon = self.icons[entryType]
    etype.setIcon(icon)
    info = QStandardItem(entryText)
    timestamp = QStandardItem(getTimestamp())
    self.logModel.insertRow(0, [etype, info, timestamp])
    if self.logModel.rowCount() > 100:
      self.logModel.removeRows(100, 1)

    self.log.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    self.log.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    self.repaint()

  def clearLists(self):
    '''Empty all QListWidget's'''
    self.meshList.clear()
    self.texList.clear()
    self.modelList.clear()
    self.lampList.clear()
    self.rendTree.clear()

  def addEnvObj(self, envobj, directory=None):
    '''Adds environment object into appropriate QListWidget'''
    if isinstance(envobj, Renderable):
      self.rendTree.add(envobj, directory)
    QListDict = {Mesh: self.meshList,
                 Tex: self.texList,
                 Bulb: self.bulbList,
                 Model: self.modelList,
                 Lamp: self.lampList}
    if type(envobj) in QListDict:
      L = QListDict[type(envobj)]
      L.add(envobj)

  def add(self, obj, directory=None):
    if directory is None:
      directory = self.rendTree.getCurrentDir()
    if self.R.add(obj, directory):
      return
    self.addEnvObj(obj, directory)
##    self.UE.scene.debug_tree()

  def setCurrentFilename(self, fn, silent=False):
    self.filename = fn
    if silent:
      return
    if self.filename is None:
      self.setWindowTitle("*New Project*")
    else:
      self.setWindowTitle(fn)

  def newProject(self, silent=False, base=False):
    '''Clear user environment and QListWidgets'''
    if not silent and not YNPrompt(self, "New", "Make new project? All unsaved changed will be lost.", factory=QMessageBox.warning):
      return
    self.clearLists()
    self.R.new()
    if base:
      B = Bulb(name="Main Bulb")
      self.add(Lamp(B, name="Main Lamp"))
      self.add(Directory(name="Main"))
    self.select(None)
    engine.monoselected = None
    if not silent:
      self.logEntry("Success", "Initialised new project.")
    self.setCurrentFilename(None, silent=silent)
    self.update()

  def saveProject(self):
    '''Try to save from last filename, else prompt to save project'''
    if self.filename is None:
      self.saveasProject()
      return
    
    try:
      self.S.save(self.filename)
    except:
      self.logEntry("Warning", "Could not save to %s; manually select filename"%shortfn(self.filename))
      self.saveasProject()
    else:
      self.logEntry("Success", "Saved project to %s"%self.filename)

  def saveasProject(self):
    '''Prompt to save project'''
    fd = QFileDialog()
    fd.setWindowTitle("Save As")
    fd.setAcceptMode(QFileDialog.AcceptSave)
    fd.setFileMode(QFileDialog.AnyFile)
    fd.setNameFilters(["3-D Project (*.3dproj)"])
    if fd.exec_():
      fn = fd.selectedFiles()[0]
      try:
        self.S.save(fn)
      except:
        self.logEntry("Error", "Could not save project to %s"%shortfn(fn))
      else:
        self.setCurrentFilename(fn)
        self.logEntry("Success", "Saved project to %s"%shortfn(fn))

  def openProject(self):
    '''Prompt to open project'''
    fd = QFileDialog()
    fd.setWindowTitle("Open")
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFile)
    fd.setNameFilters(["3-D Project (*.3dproj)", "Any File (*.*)"])
    if fd.exec_():
      fn = fd.selectedFiles()[0]
      self.newProject(silent=True)
      self.load(fn)

  def openhereProject(self):
    '''Prompt to add project to current working group'''
    fd = QFileDialog()
    fd.setWindowTitle("Open Here")
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFile)
    fd.setNameFilters(["3-D Project (*.3dproj)", "Any File (*.*)"])
    if fd.exec_():
      fn = fd.selectedFiles()[0]
      G = Directory(name=shortfn(fn))
      self.add(G)
      self.select(G)
      self.load(fn)

  def load(self, fn):
    '''Load project from filename fn'''
    try:
      self.S.load(fn)
    except IOError as e:
      self.logEntry("Error", "Unable to fully load from %s"%shortfn(fn))
      print(e)
    else:
      self.setCurrentFilename(fn)
      self.logEntry("Success", "Fully loaded from %s"%shortfn(fn))
    finally:
      self.update()

  def restoreProject(self):
    '''Attempt to restore project from previous session'''
    if self.S.canRestore() and YNPrompt(self, "Restore", "Restore previous session?"):
      try:
        self.newProject(silent=True)
        self.S.load_appdata()
##        R = Bulb(color=(1.0, 0.0, 0.0), power=10.0)
##        self.add(R)
##        G = Bulb(color=(0.0, 1.0, 0.0), power=10.0)
##        self.add(G)
##        B = Bulb(color=(0.0, 0.0, 1.0), power=10.0)
##        self.add(B)
##        self.add(Lamp(R, pos=Point(0.0, 0.0, 0.0)))
##        self.add(Lamp(G, pos=Point(-1.0, 0.0, 0.0)))
##        self.add(Lamp(B, pos=Point(-0.5, 0.0, sqrt(3)/2)))
      except:
        self.logEntry("Error", "Unable to restore previous session.")
      else:
        self.logEntry("Success", "Previous session restored.")
    self.update()

  def loadMeshes(self):
    '''Prompt to load mesh files'''
    fd = QFileDialog()
    fd.setWindowTitle("Load Meshes")
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters([r"Wavefront Object files (*.obj)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        self.loadAssetFile(fn)

  def loadTextures(self):
    '''Prompt to load texture files'''
    fd = QFileDialog()
    fd.setWindowTitle("Load Textures")
    fd.setAcceptMode(QFileDialog.AcceptOpen)
    fd.setFileMode(QFileDialog.ExistingFiles)
    fd.setNameFilters(["Images (*.bmp;*.png;*.jpg;*.jpeg)"])
    if fd.exec_():
      for fn in fd.selectedFiles():
        self.loadAssetFile(fn)

  def makeBulb(self):
    B = Bulb()
    # Modify bulb with modal: TODO
    self.add(B)
    self.logEntry("Success", "Made bulb.")

  def loadAssetFile(self, fn):
    ext = os.path.splitext(fn)[1]
    if ext in [".bmp", ".png", ".jpg", ".jpeg"]:
      try:
        self.add(Tex(fn))
      except:
        self.logEntry("Error", "Bad texture file: %s"%shortfn(fn))
      else:
        self.logEntry("Success", "Loaded texture from %s"%shortfn(fn))
    elif ext in [".obj"]:
      try:
        self.add(Mesh(fn))
      except:
        self.logEntry("Error", "Bad mesh file: %s"%shortfn(fn))
      else:
        self.logEntry("Success", "Loaded mesh from %s"%shortfn(fn))

  def exportImage(self):
    '''Prompt to export image in a size'''
    self.select(None)
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
    width = QSpinBox(minimum=1, maximum=10000, value=current_dims[0])
    height = QSpinBox(minimum=1, maximum=10000, value=current_dims[1])
    dimLayout.addRow("Width", width)
    dimLayout.addRow("Height", height)

    # CONFIRMATION BUTTON
    export = QPushButton(text="Export", icon=self.icons["Export"])
    layout.addWidget(export, 1,0, 1,1)

    def tryExport():
      w, h = width.value(), height.value()
      # Yes, resize the ACTUAL gl widget. This is the only way.
      self.gl.resize(w, h) # It won't show up anyway.
      self.gl.paintGL()
      pixels = glReadPixels(0,0, w,h, GL_RGBA, GL_UNSIGNED_BYTE)
      im = self.gl.grabFrameBuffer()
      self.gl.resize(*current_dims)
      self.gl.paintGL()
      
      fd = QFileDialog()
      fd.setAcceptMode(QFileDialog.AcceptSave)
      fd.setFileMode(QFileDialog.AnyFile)
      fd.setNameFilters(["PNG Image (*.png)"])
      if fd.exec_():
        fn = fd.selectedFiles()[0]
        try:
          im.save(fn, "PNG")
        except:
          self.logEntry("Error", "Could not export image to %s"%shortfn(fn))
        else:
          self.logEntry("Success", "Exported image to %s"%shortfn(fn))

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
    mList = copyObjList(self.meshList)
    assetLayout.addRow("Mesh", mList)
    tList = copyObjList(self.texList)
    assetLayout.addRow("Texture", tList)

    # POSE GROUP BOX
    poseBox = QGroupBox("Pose")
    layout.addWidget(poseBox, 0,1, 1,1)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    basepos, baserot = basePosRot(self.UE.camera.pos, self.UE.camera.rot, engine.monoselected)
    basex, basey, basez = basepos
    baserx, basery, baserz = [cyclamp(r*180/pi, (-180, 180)) for r in baserot]
    x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basex)
    y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basey)
    z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basez)
    rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserx), suffix="°")
    ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=basery), suffix="°")
    rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserz), suffix="°")
    scale = QDoubleSpinBox(minimum=0.05, maximum=2147483647, value=1, singleStep=0.05)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Yaw", ry)
    poseLayout.addRow("Pitch", rx)
    poseLayout.addRow("Roll", rz)
    poseLayout.addRow("scale", scale)

    # CUSTOMISATION GROUP BOX
    custBox = QGroupBox("Customization")
    layout.addWidget(custBox, 1,1, 1,1)
    custLayout = QFormLayout()
    custBox.setLayout(custLayout)
    name = QLineEdit(text="model0")
    custLayout.addRow("Name", name)

    lastx = x.value()
    lasty = y.value()
    lastz = z.value()

    def tryMakeModel(): # Attempt to construct Model from selected settings
      nonlocal lastx, lasty, lastz # allows access to lastx, lasty, lastz declared in the outer function
      m = mList.selectedItems()
      t = tList.selectedItems()
      if not (len(m) and len(t)):
        self.logEntry("Error", "Please select a mesh and a texture.")
        return
      mesh = m[0].obj
      tex = t[0].obj
      xv, yv, zv = x.value(), y.value(), z.value()
      pos = Point(xv, yv, zv)
      rot = Rot(pi*rx.value()/180, pi*ry.value()/180, pi*rz.value()/180)
      model = Model(mesh, tex,
                    pos=pos, rot=rot, scale=scale.value(),
                    name=name.text())
      self.add(model)
      self.select(model)
      dx = xv - lastx
      dy = yv - lasty
      dz = zv - lastz
      x.setValue(xv+dx)
      y.setValue(yv+dy)
      z.setValue(zv+dz)
      lastx, lasty, lastz = xv, yv, zv
      self.logEntry("Success", "Made model.")

    make = QPushButton(text="Make Model", icon=self.icons["Ok"])
    make.clicked.connect(tryMakeModel)
    layout.addWidget(make, 2,0, 1,2)

    def testValid(): # Update the button that constructs the model (enabled or disabled)
      # there should be at least one selected model and texture
      make.setEnabled(len(mList.selectedItems()) and len(tList.selectedItems()))

    mList.itemClicked.connect(testValid)
    tList.itemClicked.connect(testValid)
    testValid()
    M.exec_() # show the modal

  def makeLamps(self):
    '''Shows modal for making lamps'''
    M = Modal(self)
    M.setWindowTitle("Make Lamps")
    layout = QGridLayout()
    M.setLayout(layout)

    assetBox = QGroupBox("Assets")
    layout.addWidget(assetBox, 0,0, 2,1)
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    bList = copyObjList(self.bulbList)
    assetLayout.addRow("Bulb", bList)

    poseBox = QGroupBox("Pose")
    layout.addWidget(poseBox, 0,1, 1,1)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    basepos, _ = basePosRot(self.UE.camera.pos, self.UE.camera.rot, engine.monoselected)
    basex, basey, basez = basepos
    x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basex)
    y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basey)
    z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basez)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)

    custBox = QGroupBox("Customization")
    layout.addWidget(custBox, 1,1, 1,1)
    custLayout = QFormLayout()
    custBox.setLayout(custLayout)
    name = QLineEdit(text="lamp0")
    custLayout.addRow("Name", name)

    lastx = x.value()
    lasty = y.value()
    lastz = z.value()

    def tryMakeLamp():
      nonlocal lastx, lasty, lastz
      b = bList.selectedItems()
      if not len(b):
        return
      bulb = b[0].obj
      xv, yv, zv = x.value(), y.value(), z.value()
      lamp = Lamp(bulb, pos=Point(xv, yv, zv), name=name.text())
      self.add(lamp)
      self.select(lamp)
      dx = xv - lastx
      dy = yv - lasty
      dz = zv - lastz
      x.setValue(xv+dx)
      y.setValue(yv+dy)
      z.setValue(zv+dz)
      lastx, lasty, lastz = xv, yv, zv
      self.logEntry("Success", "Made lamp.")

    make = QPushButton("Make Lamp", icon=self.icons["Ok"])
    make.clicked.connect(tryMakeLamp)
    layout.addWidget(make, 2,0, 1,2)
    
    def testValid():
      make.setEnabled(len(bList.selectedItems()))

    bList.itemClicked.connect(testValid)
    testValid()
    M.exec_()

  def makeGroups(self):
    '''Shows modal for making groups'''
    M = Modal(self)
    M.setWindowTitle("Make Groups")
    layout = QGridLayout()
    M.setLayout(layout)

    # POSE GROUP BOX
    poseBox = QGroupBox("Pose")
    layout.addWidget(poseBox, 0,0, 1,1)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    basepos, baserot = basePosRot(self.UE.camera.pos, self.UE.camera.rot, engine.monoselected)
    basex, basey, basez = basepos
    baserx, basery, baserz = [cyclamp(r*180/pi, (-180, 180)) for r in baserot]
    x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basex)
    y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basey)
    z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647, value=basez)
    rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserx), suffix="°")
    ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=basery), suffix="°")
    rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserz), suffix="°")
    scale = QDoubleSpinBox(minimum=0.05, maximum=2147483647, value=1, singleStep=0.05)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Yaw", ry)
    poseLayout.addRow("Pitch", rx)
    poseLayout.addRow("Roll", rz)
    poseLayout.addRow("scale", scale)

    # CUSTOMISATION GROUP BOX
    custBox = QGroupBox("Customization")
    layout.addWidget(custBox, 1,0, 1,1)
    custLayout = QFormLayout()
    custBox.setLayout(custLayout)
    name = QLineEdit(text="group0")
    custLayout.addRow("Name", name)

    lastx = x.value()
    lasty = y.value()
    lastz = z.value()

    def tryMakeGroup(): # Attempt to construct Group from selected settings
      nonlocal lastx, lasty, lastz # allows access to lastx, lasty, lastz declared in the outer function
      xv, yv, zv = x.value(), y.value(), z.value()
      pos = Point(xv, yv, zv)
      rot = Rot(pi*rx.value()/180, pi*ry.value()/180, pi*rz.value()/180)
      group = Directory(pos=pos, rot=rot, scale=scale.value(),
                        name=name.text())
      self.add(group)
      dx = xv - lastx
      dy = yv - lasty
      dz = zv - lastz
      x.setValue(xv+dx)
      y.setValue(yv+dy)
      z.setValue(zv+dz)
      lastx, lasty, lastz = xv, yv, zv
      self.logEntry("Success", "Made model.")

    make = QPushButton(text="Make Group", icon=self.icons["Ok"])
    make.clicked.connect(tryMakeGroup)
    layout.addWidget(make, 2,0, 1,1)
    M.exec_() # show the modal

  def quickGroup(self):
    cam = self.UE.camera
    directory = Directory()
    directory.pos, directory.rot = basePosRot(cam.pos, cam.rot, engine.monoselected)
    directory.name = "My Group"
    self.add(directory)
    self.select(directory)

  def initEditPane(self):
    '''Initialises the edit pane'''
    self.initCamEdit()
    self.initSelEdit()

  def initCamEdit(self):
    '''Initialises the camera tab on the edit pane'''
    L = self.camEditLayout = QVBoxLayout()
    self.camEdit.setLayout(L)

    heading = QLabel("Camera", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    x = self.camEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.camEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.camEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.camEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.camEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.camEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    fovy = self.camEdit_fovy = QDoubleSpinBox(minimum=0.05, maximum=179.95, value=60, singleStep=0.05)
    zoom = self.camEdit_zoom = QDoubleSpinBox(minimum=1.0, maximum=1000.0, value=1, singleStep=0.05)
    for setting in [x, y, z, rx, ry, rz, fovy, zoom]:
      setting.valueChanged.connect(self.camEditUpdate)
    L.addWidget(heading)

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
    info = QLabel("No object selected.")
    L.addWidget(info)
    L.setAlignment(info, Qt.AlignCenter)
    W = self.nilEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===TEXTURE===
    L = QVBoxLayout()
    heading = QLabel("Texture", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    name = self.texEdit_name = QLineEdit()
    thumbnail = self.texEdit_thumbnail = QLabel()
    thumbnail.setAlignment(Qt.AlignCenter)
    diffuse = self.texEdit_diffuse = BetterSlider(QSlider(Qt.Horizontal, minimum=0, maximum=100))
    specular = self.texEdit_specular = BetterSlider(QSlider(Qt.Horizontal, minimum=0, maximum=100))
    fresnel = self.texEdit_fresnel = BetterSlider(QSlider(Qt.Horizontal, minimum=0, maximum=100))
    shininess = self.texEdit_shininess = QDoubleSpinBox(minimum=1, maximum=2147483647)
    for setting in diffuse, specular, fresnel, shininess:
      setting.valueChanged.connect(self.updateSelected)
    change = QPushButton(text="Change Image", icon=self.icons["File"])
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    name.textChanged.connect(self.updateSelected)
    
    matBox = QGroupBox("Material")
    matLayout = QFormLayout()
    matBox.setLayout(matLayout)
    matLayout.addRow("Diffuse", diffuse)
    matLayout.addRow("Specular", specular)
    matLayout.addRow("Fresnel", fresnel)
    matLayout.addRow("Shininess", shininess)
    
    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(heading)
    L.addWidget(name)
    L.addWidget(thumbnail)
    L.addWidget(matBox)
    L.addWidget(change)
    L.addWidget(delete)
    W = self.texEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===BULB===
    L = QVBoxLayout()
    heading = QLabel("Bulb", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    name = self.bulbEdit_name = QLineEdit()
    color = self.bulbEdit_color = QLineEdit(readOnly=True)
    power = self.bulbEdit_power = QDoubleSpinBox(minimum=0, maximum=2147483647)
    change = QPushButton(text="Change Color", icon=self.icons["Color"])
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    name.textChanged.connect(self.updateSelected)
    power.valueChanged.connect(self.updateSelected)
    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)

    filamentBox = QGroupBox("Filament")
    filamentLayout = QFormLayout()
    filamentBox.setLayout(filamentLayout)
    filamentLayout.addRow("Color", color)
    filamentLayout.addRow("Power", power)
    
    L.addWidget(heading)
    L.addWidget(name)
    L.addWidget(filamentBox)
    L.addWidget(change)
    L.addWidget(delete)
    W = self.bulbEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===MESH===
    L = QVBoxLayout()
    heading = QLabel("Mesh", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    name = self.meshEdit_name = QLineEdit()
    info = self.meshEdit_info = QTableWidget()
    info.verticalHeader().setVisible(False)
    info.horizontalHeader().setVisible(False)
    info.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
    info.verticalHeader().setDefaultSectionSize(24)
    infoBox = self.meshEdit_infoBox = QGroupBox("Info")
    infoLayout = QGridLayout()
    infoBox.setLayout(infoLayout)
    infoLayout.addWidget(info, 0,0, 1,1)
    change = QPushButton(text="Change Meshfile", icon=self.icons["File"])
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    cullbackface = self.meshEdit_cullbackface = QCheckBox(text="Watertight", tristate=False)
    renderBox = QGroupBox("Rendering")
    renderLayout = QFormLayout()
    renderBox.setLayout(renderLayout)
    renderLayout.addWidget(cullbackface)
    name.textChanged.connect(self.updateSelected)
    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    cullbackface.stateChanged.connect(self.updateSelected)
    L.addWidget(heading)
    L.addWidget(name)
    L.addWidget(renderBox)
    L.addWidget(infoBox)
    L.addWidget(change)
    L.addWidget(delete)
    W = self.meshEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===MODEL===
    L = QVBoxLayout()

    heading = QLabel("Model", font=self.fonts["heading"], alignment=Qt.AlignCenter)

    name = self.modelEdit_name = QLineEdit()
    change = QPushButton(text="Change Assets", icon=self.icons["Form"])
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.modelEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.modelEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.modelEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.modelEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.modelEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.modelEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    scale = self.modelEdit_scale = QDoubleSpinBox(minimum=0.05, maximum=2147483647, singleStep=0.05)
    visible = self.modelEdit_visible = QCheckBox(text="Visible", tristate=False)
    mesh = self.modelEdit_mesh = QLineEdit(readOnly=True)
    tex = self.modelEdit_tex = QLineEdit(readOnly=True)
    
    L.addWidget(heading)
    
    name.textChanged.connect(self.updateSelected)
    L.addWidget(name)

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

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)

    assetBox = QGroupBox("Assets")
    L.addWidget(assetBox)
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    assetLayout.addRow("Mesh", mesh)
    assetLayout.addRow("Texture", tex)

    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(change)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, scale]:
      setting.valueChanged.connect(self.updateSelected)

    visible.stateChanged.connect(self.updateSelected)

    W = self.modelEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===LAMP===
    L = QVBoxLayout()
    heading = QLabel("Lamp", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    name = self.lampEdit_name = QLineEdit()
    change = self.lampEdit_change = QPushButton(text="Change Bulb", icon=self.icons["Bulb"])
    delete = self.lampEdit_delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.lampEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.lampEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.lampEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    visible = self.lampEdit_visible = QCheckBox(text="Visible", tristate=False)
    bulb = self.lampEdit_bulb = QLineEdit(readOnly=True)

    poseBox = QGroupBox("Pose")
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)

    sceneBox = QGroupBox("Scene")
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)

    assetBox = QGroupBox("Assets")
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    assetLayout.addRow("Bulb", bulb)

    L.addWidget(heading)
    L.addWidget(name)
    L.addWidget(poseBox)
    L.addWidget(sceneBox)
    L.addWidget(assetBox)
    L.addWidget(change)
    L.addWidget(delete)

    name.textChanged.connect(self.updateSelected)
    for setting in x, y, z:
      setting.valueChanged.connect(self.updateSelected)
    visible.stateChanged.connect(self.updateSelected)

    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)

    W = self.lampEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===DIRECTORY===
    L = QVBoxLayout()

    heading = QLabel("Group", font=self.fonts["heading"], alignment=Qt.AlignCenter)

    name = self.dirEdit_name = QLineEdit()
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.dirEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.dirEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.dirEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.dirEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.dirEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.dirEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    scale = self.dirEdit_scale = QDoubleSpinBox(minimum=0.05, maximum=2147483647, singleStep=0.05)
    visible = self.dirEdit_visible = QCheckBox(text="Visible", tristate=False)
    
    L.addWidget(heading)
    
    name.textChanged.connect(self.updateSelected)
    L.addWidget(name)

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

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)
    
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, scale]:
      setting.valueChanged.connect(self.updateSelected)

    visible.stateChanged.connect(self.updateSelected)

    W = self.dirEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===LINK===
    L = QVBoxLayout()

    heading = QLabel("Symlink", font=self.fonts["heading"], alignment=Qt.AlignCenter)

    name = self.linkEdit_name = QLineEdit()
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.linkEdit_x = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    y = self.linkEdit_y = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    z = self.linkEdit_z = QDoubleSpinBox(minimum=-2147483648, maximum=2147483647)
    rx = self.linkEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.linkEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.linkEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    scale = self.linkEdit_scale = QDoubleSpinBox(minimum=0.05, maximum=2147483647, singleStep=0.05)
    visible = self.linkEdit_visible = QCheckBox(text="Visible", tristate=False)
    
    L.addWidget(heading)
    
    name.textChanged.connect(self.updateSelected)
    L.addWidget(name)

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

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)
    
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, scale]:
      setting.valueChanged.connect(self.updateSelected)

    visible.stateChanged.connect(self.updateSelected)

    W = self.linkEdit = QWidget()
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
    self.gl.update()

  def reinitSelected(self):
    '''Prompts user to reinitialise the selected object from different files/assets'''
    S = engine.monoselected
    if type(S) is Mesh:
      ID = S.ID
      fd = QFileDialog()
      fd.setAcceptMode(QFileDialog.AcceptOpen)
      fd.setFileMode(QFileDialog.ExistingFile)
      fd.setNameFilters([r"Wavefront Object files (*.obj)"])
      if fd.exec_():
        fn = fd.selectedFiles()[0]
        try:
          newMesh = Mesh(fn)
          newMesh.cullbackface = S.cullbackface
          newMesh.name = S.name
          self.R.delete(S)
          S.__dict__ = newMesh.__dict__
          self.R.add(S)
        except:
          self.logEntry("Error", "Bad mesh file: %s"%shortfn(fn))
        else:
          self.logEntry("Success", "Loaded mesh from %s"%shortfn(fn))
        finally:
          for i in range(self.modelList.count()):
            model = self.modelList.item(i).obj
            if model.mesh is S:
              model.update_bbox()

    elif type(S) is Tex:
      fd = QFileDialog()
      fd.setAcceptMode(QFileDialog.AcceptOpen)
      fd.setFileMode(QFileDialog.ExistingFile)
      fd.setNameFilters([r"Images (*.bmp;*.png;*.jpg;*.jpeg)"])
      if fd.exec_():
        fn = fd.selectedFiles()[0]
        try:
          newTex = Tex(fn)
          newTex.name = S.name
          self.R.delete(S)
          S.__dict__ = newTex.__dict__
          self.R.add(S)
        except:
          self.logEntry("Error", "Bad image file: %s"%shortfn(fn))
        else:
          self.logEntry("Success", "Loaded texture from %s"%shortfn(fn))

    elif type(S) is Bulb:
      M = QColorDialog(self)
      C = M.getColor()
      S.color = (C.redF(), C.greenF(), C.blueF())

    elif type(S) is Model:
      M = Modal(self)
      M.setWindowTitle("Change Model")
      layout = QGridLayout()
      M.setLayout(layout)

      # ASSET GROUP BOX
      assetBox = QGroupBox("Assets")
      layout.addWidget(assetBox, 0,0, 1,1)
      assetLayout = QFormLayout()
      assetBox.setLayout(assetLayout)
      mList = copyObjList(self.meshList)
      assetLayout.addRow("Mesh", mList)
      tList = copyObjList(self.texList)
      assetLayout.addRow("Texture", tList)

      if not S.mesh.deleted:
        mList.setCurrentRow(mList.find(S.mesh))
      if not S.tex.deleted:
        tList.setCurrentRow(tList.find(S.tex))

      def tryChangeModel():
        m = mList.selectedItems()
        t = tList.selectedItems()
        if not (len(m) and len(t)):
          return
        S.mesh = m[0].obj
        S.tex = t[0].obj
        S.update_bbox()
        self.update()
      
      mList.itemClicked.connect(tryChangeModel)
      tList.itemClicked.connect(tryChangeModel)
      M.exec_()

    self.updateSelEdit()


  def deleteSelected(self):
    '''Deletes selected object'''
    self.delete(engine.monoselected)
    self.update()

  def delete(self, obj):
    '''Deletes object (Mesh, Tex, Model, or Lamp) from user environment, ui list, and file cache and deselects it'''
    # Remove from list
    if isinstance(obj, Renderable):
      self.rendTree.delete(obj)
    listDict = {Mesh: self.meshList,
                Tex: self.texList,
                Bulb: self.bulbList,
                Model: self.modelList,
                Lamp: self.lampList}
    if type(obj) in listDict:
      l = listDict[type(obj)]
      l.take(obj)
    self.R.delete(obj)
    # Deselect object
    engine.selected.discard(obj)
    if isinstance(engine.monoselected, Renderable):
      engine.monoselected.update_bbox()
    if engine.monoselected is obj:
      self.select(None)

  def copySelected(self):
    engine.clipboard = engine.monoselected

  def shallowPaste(self, obj):
    cam = self.UE.camera
    if obj is not None:
      try:
        sCopy = copy.copy(obj)
        if isinstance(sCopy, Renderable):
          sCopy.pos, sCopy.rot = obj.pos, obj.rot
        self.add(sCopy)
      except TreeError as e:
        self.logEntry("Error", "Symlink cycle: %s"%e)
      else:
        self.select(sCopy)

  def deepPaste(self, obj):
    cam = self.UE.camera
    if obj is not None:
      try:
        dCopy = copy.deepcopy(obj)
        if isinstance(dCopy, Renderable):
          dCopy.pos, dCopy.rot = obj.pos, obj.rot
        self.add(dCopy)
      except TreeError as e:
        self.logEntry("Error", "Symlink cycle: %s"%e)
      else:
        self.select(dCopy)

  def shallowPasteClipboard(self):
    self.shallowPaste(engine.clipboard)

  def deepPasteClipboard(self):
    self.deepPaste(engine.clipboard)

  def shallowPasteSelected(self):
    sel = engine.monoselected
    self.selectParent()
    self.shallowPaste(sel)

  def deepPasteSelected(self):
    sel = engine.monoselected
    self.selectParent()
    self.deepPaste(sel)

  def move(self, rend, directory):
    try:
      if rend.parent is None:
        self.UE.scene.discard(rend)
      rend.setParent(directory)
      if rend.parent is None:
        self.UE.scene.add(rend)
    except TreeError as e:
      self.logEntry("Error", "Symlink cycle: %s"%e)
    else:
      self.rendTree.move(rend, directory)
      self.gl.update()

  def cutSelected(self):
    self.copySelected()
    self.deleteSelected()

  def updateSelected(self):
    '''Updates selected object from displayed settings'''
    S = engine.monoselected
    if type(S) is Tex:
      S.name = self.texEdit_name.text()
      S.diffuse = self.texEdit_diffuse.value()/100
      S.specular = self.texEdit_specular.value()/100
      S.fresnel = self.texEdit_fresnel.value()/100
      S.shininess = self.texEdit_shininess.value()
      self.texList.update()
      
    elif type(S) is Mesh:
      S.name = self.meshEdit_name.text()
      S.cullbackface = self.meshEdit_cullbackface.isChecked()
      self.meshList.update()

    elif type(S) is Bulb:
      S.name = self.bulbEdit_name.text()
      S.power = self.bulbEdit_power.value()
      self.bulbList.update()
      
    elif type(S) is Model:
      S.name = self.modelEdit_name.text()
      S.pos = Point(self.modelEdit_x.value(),
                    self.modelEdit_y.value(),
                    self.modelEdit_z.value())
      S.rot = Rot(pi*self.modelEdit_rx.value()/180,
                  pi*self.modelEdit_ry.value()/180,
                  pi*self.modelEdit_rz.value()/180)
      S.scale = self.modelEdit_scale.value()
      S.visible = self.modelEdit_visible.isChecked()
      self.modelList.update()
      self.rendTree.update()

    elif type(S) is Lamp:
      S.name = self.lampEdit_name.text()
      S.pos = Point(self.lampEdit_x.value(),
                    self.lampEdit_y.value(),
                    self.lampEdit_z.value())
      S.visible = self.lampEdit_visible.isChecked()
      self.lampList.update()
      self.rendTree.update()

    elif type(S) is Directory:
      S.name = self.dirEdit_name.text()
      S.pos = Point(self.dirEdit_x.value(),
                    self.dirEdit_y.value(),
                    self.dirEdit_z.value())
      S.rot = Rot(pi*self.dirEdit_rx.value()/180,
                  pi*self.dirEdit_ry.value()/180,
                  pi*self.dirEdit_rz.value()/180)
      S.scale = self.dirEdit_scale.value()
      S.visible = self.dirEdit_visible.isChecked()
      self.rendTree.update()

    elif type(S) is Link:
      S.name = self.linkEdit_name.text()
      S.pos = Point(self.linkEdit_x.value(),
                    self.linkEdit_y.value(),
                    self.linkEdit_z.value())
      S.rot = Rot(pi*self.linkEdit_rx.value()/180,
                  pi*self.linkEdit_ry.value()/180,
                  pi*self.linkEdit_rz.value()/180)
      S.scale = self.linkEdit_scale.value()
      S.visible = self.linkEdit_visible.isChecked()
      self.rendTree.update()
      
    self.gl.update()

  def switchSelEdit(self, objType):
    '''Updates the stacked widget in the "Selected" tab of the edit pane'''
    widgetDict = {Mesh: self.meshEdit,
                  Tex: self.texEdit,
                  Bulb: self.bulbEdit,
                  Model: self.modelEdit,
                  Lamp: self.lampEdit,
                  Directory: self.dirEdit,
                  Link: self.linkEdit
                  }
    if objType in widgetDict:
      self.selEdit.setCurrentWidget(widgetDict[objType])
    else:
      self.selEdit.setCurrentWidget(self.nilEdit)

  def updateSelEdit(self):
    '''Switch to relevent layout and put in correct settings to display'''
    S = engine.monoselected
    self.switchSelEdit(type(S))
    if type(S) is Tex:
      name = S.name
      diffuse = int(100*S.diffuse)
      specular = int(100*S.specular)
      fresnel = int(100*S.fresnel)
      shininess = S.shininess
      qpm = QPixmap.fromImage(S.thumbnailQt)
      self.texEdit_thumbnail.setPixmap(qpm)
      for setting, text in [(self.texEdit_name, name)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      for setting, val in [(self.texEdit_diffuse, diffuse),
                           (self.texEdit_specular, specular),
                           (self.texEdit_fresnel, fresnel),
                           (self.texEdit_shininess, shininess)]:
        setting.blockSignals(True)
        setting.setValue(val)
        setting.blockSignals(False)
      self.texEdit.update()
        
    if type(S) is Mesh:
      name = S.name
      cullbackface = S.cullbackface
      info = [["Vertices", len(S.vertices)-1],
              ["Edges", len(S.edges)],
              ["Faces", len(S.tri_faces)+len(S.quad_faces)+len(S.poly_faces)],
              ["Tris", len(S.vbo_tri_indices)//3],
              ["VBO length", S.vbo_bufferlen]]

      loadQTable(self.meshEdit_info, info)
      self.meshEdit_info.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
      self.meshEdit_info.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
      
      for setting, text in [(self.meshEdit_name, name)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
        
      for checkbox, state in [(self.meshEdit_cullbackface, cullbackface)]:
        checkbox.blockSignals(True)
        checkbox.setCheckState(state*2)
        checkbox.blockSignals(False)

      self.meshEdit.update()

    elif type(S) is Bulb:
      name = S.name
      r,g,b = S.color
      power = S.power

      for setting, text in [(self.bulbEdit_name, name),
                            (self.bulbEdit_color, rrggbb(r,g,b))]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)

      for setting, var in [(self.bulbEdit_power, power)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)
      
    elif type(S) is Model:
      name = S.name
      x, y, z = S.pos
      rx, ry, rz = S.rot
      rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in S.rot)
      scale = S.scale
      visible = S.visible
      mesh = S.mesh.name
      tex = S.tex.name
      
      for setting, text in [(self.modelEdit_name, name)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      
      for setting, var in [(self.modelEdit_x, x),
                           (self.modelEdit_y, y),
                           (self.modelEdit_z, z),
                           (self.modelEdit_rx, rx),
                           (self.modelEdit_ry, ry),
                           (self.modelEdit_rz, rz),
                           (self.modelEdit_scale, scale)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)

      for setting, text in [(self.modelEdit_mesh, mesh),
                            (self.modelEdit_tex, tex)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      
      for checkbox, state in [(self.modelEdit_visible, visible)]:
        checkbox.blockSignals(True)
        checkbox.setCheckState(state*2)
        checkbox.blockSignals(False)

      self.modelEdit.update()

    elif type(S) is Lamp:
      name = S.name
      x, y, z = S.pos
      visible = S.visible
      bulb = S.bulb.name

      for setting, text in [(self.lampEdit_name, name),
                            (self.lampEdit_bulb, bulb)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)

      for setting, var in [(self.lampEdit_x, x),
                           (self.lampEdit_y, y),
                           (self.lampEdit_z, z)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)

      for checkbox, state in [(self.lampEdit_visible, visible)]:
        checkbox.blockSignals(True)
        checkbox.setCheckState(state*2)
        checkbox.blockSignals(False)

    elif type(S) is Directory:
      name = S.name
      x, y, z = S.pos
      rx, ry, rz = S.rot
      rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in S.rot)
      scale = S.scale
      visible = S.visible
      
      for setting, text in [(self.dirEdit_name, name)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      
      for setting, var in [(self.dirEdit_x, x),
                           (self.dirEdit_y, y),
                           (self.dirEdit_z, z),
                           (self.dirEdit_rx, rx),
                           (self.dirEdit_ry, ry),
                           (self.dirEdit_rz, rz),
                           (self.dirEdit_scale, scale)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)
      
      for checkbox, state in [(self.dirEdit_visible, visible)]:
        checkbox.blockSignals(True)
        checkbox.setCheckState(state*2)
        checkbox.blockSignals(False)

      self.dirEdit.update()

    elif type(S) is Link:
      name = S.name
      x, y, z = S.pos
      rx, ry, rz = S.rot
      rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in S.rot)
      scale = S.scale
      visible = S.visible
      
      for setting, text in [(self.linkEdit_name, name)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      
      for setting, var in [(self.linkEdit_x, x),
                           (self.linkEdit_y, y),
                           (self.linkEdit_z, z),
                           (self.linkEdit_rx, rx),
                           (self.linkEdit_ry, ry),
                           (self.linkEdit_rz, rz),
                           (self.linkEdit_scale, scale)]:
        setting.blockSignals(True)
        setting.setValue(var)
        setting.blockSignals(False)
      
      for checkbox, state in [(self.linkEdit_visible, visible)]:
        checkbox.blockSignals(True)
        checkbox.setCheckState(state*2)
        checkbox.blockSignals(False)

      self.linkEdit.update()
        
    self.selEdit.update()
    
  def select(self, obj):
    '''Selects an object for editing'''
    engine.selected.clear()
    if obj is not None:
      engine.selected.add(obj)
    if isinstance(obj, Renderable):
      obj.update_bbox()
    engine.monoselected = obj
    self.edit.setCurrentWidget(self.selScrollArea)
    self.updateSelEdit()
    self.gl.sel_dv = None
    self.gl.sel_dr = None
    self.gl.update()
    self.rendTree.select(obj)

  def selectParent(self):
    if isinstance(engine.monoselected, Renderable):
      self.select(engine.monoselected.parent)

  def selectFirstChild(self):
    if engine.monoselected is None and self.rendTree.topLevelItemCount():
      self.select(self.rendTree.topLevelItem(0).obj)
    elif isinstance(engine.monoselected, Directory):
      node = self.rendTree.objNodeDict[engine.monoselected]
      if node.childCount():
        self.select(node.child(0).obj)

  def selectLastChild(self):
    if engine.monoselected is None and self.rendTree.topLevelItemCount():
      self.select(self.rendTree.topLevelItem(self.rendTree.topLevelItemCount()-1).obj)
    elif isinstance(engine.monoselected, Directory):
      node = self.rendTree.objNodeDict[engine.monoselected]
      if node.childCount():
        self.select(node.child(node.childCount()-1).obj)

  def selectPrevSibling(self):
    if engine.monoselected is None:
      self.selectLastChild()
    elif isinstance(engine.monoselected, Renderable):
      parentNode = self.rendTree.objNodeDict[engine.monoselected].parent()
      if parentNode is None:
        prevIndex = self.rendTree.find(engine.monoselected) - 1
        if prevIndex in range(self.rendTree.topLevelItemCount()):
          self.select(self.rendTree.topLevelItem(prevIndex).obj)
      else:
        prevIndex = parentNode.find(engine.monoselected) - 1
        if prevIndex in range(parentNode.childCount()):
          self.select(parentNode.child(prevIndex).obj)

  def selectNextSibling(self):
    if engine.monoselected is None:
      self.selectFirstChild()
    elif isinstance(engine.monoselected, Renderable):
      parentNode = self.rendTree.objNodeDict[engine.monoselected].parent()
      if parentNode is None:
        nextIndex = self.rendTree.find(engine.monoselected) + 1
        if nextIndex in range(self.rendTree.topLevelItemCount()):
          self.select(self.rendTree.topLevelItem(nextIndex).obj)
      else:
        nextIndex = parentNode.find(engine.monoselected) + 1
        if nextIndex in range(parentNode.childCount()):
          self.select(parentNode.child(nextIndex).obj)

  def update(self):
    '''Overload: update to display correct features'''
    self.updateMenu()
    self.updateCamEdit()
    self.updateSelEdit()
    self.gl.update()
    super().update()

  def closeEvent(self, event):
    if YNPrompt(self, "Close", "Exit %s? Unsaved progress may still be accessed next session."%APPNAME, factory=QMessageBox.warning):
      event.accept()
    else:
      event.ignore()
      return
    self.envPane.hide()
    self.editPane.hide()
    self.logPane.hide()
    self.helpPane.hide()
    self.S.update()
    print("Goodbye!")

  def dragEnterEvent(self, event):
    if event.mimeData().hasUrls():
      event.accept()

  def dropEvent(self, event):
    mimeData = event.mimeData()
    paths = [urlObj.adjusted(QUrl.RemoveScheme).url()[1:] for urlObj in mimeData.urls()]
    if len(paths) == 1 and os.path.splitext(paths[0])[1] == ".3dproj":
      self.load(paths[0])
    else:
      for path in paths:
        self.loadAssetFile(path)

if __name__ == "__main__":
  window = QApplication(sys.argv)
  app = MainApp()
  app.restoreProject()
  def tryexec():
    try:
      return window.exec_()
    except Exception as e:
      print(e)
      return 1
  sys.exit(tryexec())
