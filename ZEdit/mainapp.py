#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
gui.py

Makes the graphical application and runs the main systems
'''

from all_modules import *
from dropshadow import DropShadowFrame, _DropShadowWidget

from rotpoint import Rot, Point
from asset import id_gen, Asset, Mesh, Tex, Bulb
from engine import Camera, Renderable, Model, Lamp, Directory, Link, initEngine, TreeError
import engine
from userenv import UserEnv
from remote import Remote
from saver import Saver

PRECISION = 4
EPSILON = 10**-PRECISION
B32 = 2147483648

def nonzero(fl):
  return EPSILON if fl == 0.0 else fl

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

def qtifyColor(colorName):
  qc = QColor()
  qc.setNamedColor(colorName)
  return qc

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

def iconLabel(icon, size=(24, 24)):
  return QLabel(pixmap=icon.pixmap(QSize(*size)))

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

class WidgetRow(QWidget):
  def __init__(self, widgets):
    super().__init__()
    L = QHBoxLayout()
    for widget in widgets:
      L.addWidget(widget)
    self.setLayout(L)

class InteractiveGLWidget(QGLWidget):
  '''OpenGL+QT widget'''
  drawScene = pyqtSignal(float) # signal emmited when wanting to redraw scene
  mouseOver = pyqtSignal(QMouseEvent)
  clicked = pyqtSignal(QMouseEvent)
  requestSelect = pyqtSignal(object)
  requestUpdate = pyqtSignal()
  requestRectifyCamera = pyqtSignal()
  requestLookAt = pyqtSignal(object)
  resizeViewport = pyqtSignal(int, int)
  focusChanged = pyqtSignal(bool)

  requestChangeRendRot = pyqtSignal(Renderable, float, float, float)
  requestChangeCameraRot = pyqtSignal(float, float, float)
  requestMoveRendTo = pyqtSignal(Renderable, float, float, float)
  
  def __init__(self, *args, **kwargs):
    QGLWidget.__init__(self, *args, **kwargs)
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

    self.dropShadow = QGraphicsDropShadowEffect(self)
    self.dropShadow.setOffset(0, 0)
    self.dropShadow.setBlurRadius(0)
##    self.setGraphicsEffect(self.dropShadow)

  def qt2glXY(self, XY):
    '''Input: QT XY coordinates
       Output: OpenGL XY coordinates'''
    X, Y = XY
    # Flip Y
    Y = self.dims[1] - Y
    return X, Y

  def getCamera(self): # redefined elsewhere
    return Camera()

  def initializeGL(self):
    initEngine()

  def paintGL(self):
    self.drawScene.emit(self.aspect)

  def resizeGL(self, w, h):
    self.dims = w, h
    self.aspect = w/h
    self.resizeViewport.emit(w,h)
    super().resizeGL(w, h)
    self.update()

  def keyPressEvent(self, event):
    if event.key() == Qt.Key_Escape:
      self.requestSelect.emit(None)
    elif (event.key() == Qt.Key_Shift):
      if isinstance(engine.monoselected, Renderable):
        self.requestLookAt.emit(engine.monoselected)
      else:
        self.requestLookAt.emit(Point(0, 0, 0)) # look at origin
      self.update()
    self.heldKeys.add(event.key())

  def keyReleaseEvent(self, event):
    self.heldKeys.discard(event.key())

  def onTick(self): # custom: scheduled to call at regular intervals
    now = time.time()
    self.dt = now - self.lastt
    self.lastt = now
    if self.handleHeldKeys():
##      engine.renderingMode = engine.FLAT
      self.requestUpdate.emit()
##    else:
##      if not engine.renderingMode == engine.FULL and not self.dragging:
##        engine.renderingMode = engine.FULL
##        self.update()
      

  def handleHeldKeys(self):
    cam = self.getCamera()
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
        self.requestChangeRendRot.emit(sel, dt*drx, dt*dry, dt*drz)
      else:
        self.requestChangeCameraRot.emit(dt*drx, dt*dry, dt*drz)

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
          self.requestLookAt.emit(engine.monoselected)
          self.sel_dv = dict()
          selpos = sel.getTruePos()
          self.sel_dv[sel] = selpos - cam.pos
##          for rend in selRends:
##            selpos = rend.getTruePos()
##            self.sel_dv[rend] = selpos - cam.pos
        cam.pos += np.linalg.norm(np.array(self.sel_dv[sel])) * dp
        for rend in selRends:
          new_selpos = cam.pos + self.sel_dv[rend]
          self.requestMoveRendTo.emit(rend, *new_selpos)
      else:
        cam.pos += dp
        
    if not moved:
      self.sel_dv = None

    return count

  def wheelEvent(self, event):
    self.setFocus()
    cam = self.getCamera()
    sel = engine.monoselected
    if keyModFlags() & Qt.ShiftModifier:
      if isinstance(sel, Renderable):
        selpos = sel.getTruePos()
      else:
        selpos = Point(0, 0, 0)
      dx0, dy0, dz0 = cam.pos - selpos
      dist0 = (dx0**2+dy0**2+dz0**2)**0.5
      dist = min(max(0.1, dist0*10**(-event.angleDelta().y()/(360*10))), B32-1)
      cam.pos = selpos - (cam.rot.get_forward_vector(invert=True)*dist)
      self.sel_dr = dist
    else:
      cam.zoom *= 10**(event.angleDelta().y()/(360*10))
      cam.zoom = min(max(1.0, cam.zoom), 1000.0)
    self.requestUpdate.emit()

  def mousePressEvent(self, event):
    super().mousePressEvent(event)
    self.mousePos = event.x(), event.y()
    self.cam_rot = self.getCamera().rot
    self.dragging = True
    self.update()

  def mouseMoveEvent(self, event):
    X, Y = event.x(), event.y()
    cam = self.getCamera()
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
            self.requestLookAt.emit(selpos)
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
        
      self.requestRectifyCamera.emit()
    self.mouseOver.emit(event)
    self.update()

  def mouseReleaseEvent(self, event):
    super().mouseReleaseEvent(event)
    self.dragging = False
    self.sel_dr = None
    if (event.x(), event.y()) == self.mousePos:
      self.clicked.emit(event)
    self.update()

  def focusInEvent(self, event):
    super().focusInEvent(event)
    self.dropShadow.setBlurRadius(20)
    self.focusChanged.emit(True)

  def focusOutEvent(self, event):
    super().focusOutEvent(event)
    self.dropShadow.setBlurRadius(0)
    self.focusChanged.emit(False)

class ObjList(QListWidget):
  '''QListWidget of environment objects (Mesh, Tex, Model, Lamp)'''
  requestUpdate = pyqtSignal()
  requestSelect = pyqtSignal(object)
  
  iconDict = dict() # obj type --> icon
  bgDict = dict() # obj type --> bg brush
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
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
    if isinstance(item.obj, Link):
      self.requestSelect.emit(item.obj.directory)
    elif isinstance(item.obj, Renderable):
      self.requestLookAt.emit(item.obj)
      self.requestUpdate.emit()

  def onItemSelectionChanged(self):
    items = self.selectedItems()
    engine.selected = set([item.obj for item in items])
    if items:
      self.requestSelect.emit(items[0].obj)
    else:
      self.requestSelect.emit(None)

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
    pass # delete key now handled globally

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
  requestUpdate = pyqtSignal() # signal emitted when wanting to update the entire app
  requestMove = pyqtSignal(object, object) # signal emitted when wanting to put the first object into the second as a child
  requestSelect = pyqtSignal(object) # signal emitted when wanting to select an object
  requestSelectParent = pyqtSignal()
  requestSelectFirstChild = pyqtSignal()
  requestSelectPrevSibling = pyqtSignal()
  requestSelectNextSibling = pyqtSignal()
  requestLookAt = pyqtSignal(object) # signal emitted when wanting to look at a Renderable or Point
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setSelectionMode(QAbstractItemView.SingleSelection)
    self.setDragEnabled(True)
    self.viewport().setAcceptDrops(True)
    self.setDropIndicatorShown(False)
    self.setDragDropMode(QAbstractItemView.InternalMove)
    self.objNodeDict = dict() # asset/renderable --> node
    self.groupNums = id_gen()
    self.itemClicked.connect(self.onItemClicked)
    self.itemDoubleClicked.connect(self.onItemDoubleClicked)
    self.itemChanged.connect(self.onItemChanged)
    self.itemSelectionChanged.connect(self.onItemSelectionChanged)
    self.itemEntered.connect(self.onItemEntered)
    self.setMouseTracking(True)
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
      self.scrollToItem(self.objNodeDict[obj])
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
    if keyModFlags() & Qt.ShiftModifier:
      self.requestMove.emit(item.obj, self.getCurrentDir())

  def onItemDoubleClicked(self, item):
    if isinstance(item.obj, Link):
      self.requestSelect.emit(item.obj.directory)
    elif isinstance(item.obj, Renderable):
      self.requestLookAt.emit(item.obj)
      self.requestUpdate.emit()

  def onItemChanged(self, item):
    if isinstance(item.obj, Renderable):
      item.obj.visible = item.checkState(2)==2
      self.requestUpdate.emit()

  def onItemSelectionChanged(self):
    selItems = self.selectedItems()
    if selItems:
      self.requestSelect.emit(selItems[0].obj)

  def onItemEntered(self, item):
    engine.highlighted = item.obj
    self.requestUpdate.emit()

  def keyPressEvent(self, event):
    selItems = self.selectedItems()
    if selItems:
      selItem = selItems[0]
      sel = selItem.obj
    else:
      selItem = None
      sel = None
    k = event.key()
    if k == Qt.Key_Escape:
      self.requestSelect.emit(None)
    elif k == Qt.Key_Shift:
      self.setSelectionMode(QTreeWidget.NoSelection)
    elif k == Qt.Key_Return:
      selItems = self.selectedItems()
      if selItems:
        selItems[0].setExpanded(not selItems[0].isExpanded())
    elif k == Qt.Key_Left:
      self.requestSelectParent.emit()
    elif k == Qt.Key_Right:
      self.requestSelectFirstChild.emit()
    elif k == Qt.Key_Up:
      self.requestSelectPrevSibling.emit()
    elif k == Qt.Key_Down:
      self.requestSelectNextSibling.emit()

  def keyReleaseEvent(self, event):
    k = event.key()
    if k == Qt.Key_Shift:
      self.setSelectionMode(QTreeWidget.SingleSelection)

  def focusOutEvent(self, event):
    self.itemDragged = None
    self.setSelectionMode(QTreeWidget.SingleSelection)

  def mousePressEvent(self, event):
    index = self.indexAt(event.pos())
    if (index.row() == -1):
      self.requestSelect.emit(None)
    else:
      self.itemDragged = self.itemAt(event.pos())
      super().mousePressEvent(event)

  def mouseMoveEvent(self, event):
    index = self.indexAt(event.pos())
    if index.row() == -1:
      engine.highlighted = None
      self.requestUpdate.emit()
    super().mouseMoveEvent(event)

  def mouseReleaseEvent(self, event):
    self.itemDragged = None
    super().mouseReleaseEvent(event)

  def dropEvent(self, event):
    index = self.indexAt(event.pos())
    if (index.row() == -1):
      return
    item = self.itemAt(event.pos())
    if isinstance(item.obj, Directory) or self.itemDragged is None:
      self.requestMove.emit(self.itemDragged.obj, item.obj)
    else:
      self.requestMove.emit(self.itemDragged.obj, item.obj.parent)
  
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

def CBrush(colorName):
  return QBrush(qtifyColor(colorName))

class MainApp(QMainWindow):
  '''Main Application, uses QT'''
  def __init__(self, parent=None):
    self.remote = Remote(UserEnv())

    super().__init__(parent)
    self._init_style()
    self._load_assets()
    self._make_widgets()
    self._init_hotkeys()
    self.resize(1000, 500)
    self.setWindowIcon(self.icons["Window Icon"])
    self.setWindowTitle(APPNAME)
    self.show()
    self.newProject(silent=True, base=True)
    self.saver = Saver(self)
    
    self.setAcceptDrops(True)
  
  def _init_style(self):
    '''Apply stylesheet'''
    self.setStyleSheet(open("./style.qss").read())

  def _load_assets(self):
    '''Load all icons'''
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

    ICON_PATH = "./assets/icons/dark_theme/"
    for name, fn in [("Mesh", r"mesh.png"),
                     ("Texture", r"texture.png"),
                     ("Bulb", r"bulb.png"),
                     ("Model", r"model.png"),
                     ("Lamp", r"lamp.png"),
                     ("Object Group", r"objectgroup.png"),
                     ("Link", r"link.png"),
                     ("3D Scene", r"3dscene.png"),
                     ("Scene", r"scene.png"),
                     ("Edit", r"edit.png"),
                     ("Camera", r"camera.png"),
                     ("Selected", r"selected.png"),
                     ("Image File", r"imagefile.png"),
                     ("Color", r"color.png")]:
      self.icons[name] = QIcon(os.path.join(ICON_PATH, fn))

    WINDOW_ICON_FN = "./assets/icons/window_icon.png"
    self.icons["Window Icon"] = QIcon(WINDOW_ICON_FN)

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
    render = bar.addMenu("&Render")
    self.renderMenu_fullmode = QAction(self.icons["3D Scene"], "&Full Mode")
    self.renderMenu_flatmode = QAction(self.icons["Model"], "Fl&at Mode")
    render.addAction(self.renderMenu_fullmode)
    render.addAction(self.renderMenu_flatmode)
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

    self.gl = InteractiveGLWidget(self)
    self.gl.getCamera = self.remote.getCamera
    self.glDSF = _DropShadowWidget()
    self.glDSFLayout = QVBoxLayout()
    self.glDSFLayout.setContentsMargins(0,0, 0,0)
    self.glDSFLayout.addWidget(self.gl)
    self.glDSF.setLayout(self.glDSFLayout)
    self.setCentralWidget(self.glDSF)
    self.glDSF.setOffset(QPoint(0,0))
    self.glDSF.setColor(qtifyColor("#ffff30"))
    self.glDSF.setRadius(10)
    self.glDSF.setProperty("class", "DarkTheme")
    
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
    self.env.addTab(self.rendTree, self.icons["3D Scene"], "")
    self.envPane.setWidget(self.env)
    self.envPane.setFloating(False)
    self.addDockWidget(Qt.LeftDockWidgetArea, self.envPane)

    self.editPane = QDockWidget("Edit", self)
    self.edit = ResizableTabWidget(movable=True, tabPosition=QTabWidget.North)
    self.edit.setProperty("class", "BigTabs")
    self.sceneEdit = QWidget()
    self.sceneScrollArea = VerticalScrollArea()
    self.camEdit = QWidget()
    self.camScrollArea = VerticalScrollArea()
    self.selEdit = ResizableStackedWidget()
    self.selEdit.currentChanged.connect(lambda i: self.edit.onCurrentChanged(0))
    self.selScrollArea = VerticalScrollArea()
    self.edit.addTab(self.sceneScrollArea, self.icons["Scene"], "")
    self.edit.addTab(self.camScrollArea, self.icons["Camera"], "")
    self.edit.addTab(self.selScrollArea, self.icons["Selected"], "")
    self.editPane.setWidget(self.edit)
    self.initEditPane()
    self.sceneScrollArea.setWidget(self.sceneEdit)
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
    self.logEntry("Info", "Welcome to %s 1.0.0"%APPNAME)
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
    self.renderMenu_fullmode.triggered.connect(self.fullMode)
    self.renderMenu_flatmode.triggered.connect(self.flatMode)
    self.viewMenu_env.triggered.connect(self.curryTogglePane(self.envPane))
    self.viewMenu_edit.triggered.connect(self.curryTogglePane(self.editPane))
    self.viewMenu_log.triggered.connect(self.curryTogglePane(self.logPane))
    self.envPane.visibilityChanged.connect(self.updateMenu)
    self.editPane.visibilityChanged.connect(self.updateMenu)
    self.logPane.visibilityChanged.connect(self.updateMenu)
    self.helpMenu_help.triggered.connect(self.showHelp)

    # connect signals from widgets
    self.gl.drawScene.connect(self.remote.renderScene)
    self.gl.mouseOver.connect(lambda e: self.highlightFromXY((e.x(),e.y())))
    self.gl.clicked.connect(lambda e: self.selectFromXY((e.x(),e.y())))
    self.gl.requestSelect.connect(self.select)
    self.gl.requestUpdate.connect(self.update)
    self.gl.requestRectifyCamera.connect(self.remote.rectifyCamera)
    self.gl.requestLookAt.connect(self.remote.lookAt)
    self.gl.resizeViewport.connect(self.remote.resizeViewport)
    self.gl.focusChanged.connect(self.glFocusChanged)
    self.gl.requestChangeRendRot.connect(self.remote.changeRendRot)
    self.gl.requestChangeCameraRot.connect(self.remote.changeCameraRot)
    self.gl.requestMoveRendTo.connect(self.remote.moveRendTo)

    self.texList.requestUpdate.connect(self.update)
    self.texList.requestSelect.connect(self.select)
    self.meshList.requestUpdate.connect(self.update)
    self.meshList.requestSelect.connect(self.select)
    self.bulbList.requestUpdate.connect(self.update)
    self.bulbList.requestSelect.connect(self.select)
    
    self.rendTree.requestUpdate.connect(self.update)
    self.rendTree.requestMove.connect(self.move)
    self.rendTree.requestSelect.connect(self.select)
    self.rendTree.requestSelectParent.connect(self.selectParent)
    self.rendTree.requestSelectFirstChild.connect(self.selectFirstChild)
    self.rendTree.requestSelectPrevSibling.connect(self.selectPrevSibling)
    self.rendTree.requestSelectNextSibling.connect(self.selectNextSibling)
    self.rendTree.requestLookAt.connect(self.remote.lookAt)
    

  def _init_hotkeys(self):
    '''Initialise hotkeys for ease-of-use'''
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

    quickShortcut("Ctrl+Alt+M", self.sceneMenu_makemodels)
    quickShortcut("Ctrl+Alt+L", self.sceneMenu_makelamps)
    quickShortcut("Ctrl+Alt+G", self.sceneMenu_makegroups)
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
    self.keyBind_focusgl = quickKeybind("/", self.focusGL)
    self.keyBind_togglemode = quickKeybind("Q", self.toggleMode)

  def showHelp(self):
    '''Show help pane'''
    self.helpPane.show()
    self.helpPane.activateWindow()
    self.helpPane.setFocus()

  def focusGL(self):
    '''Set mouse and keyboard focus on gl widget'''
    self.activateWindow()
    self.gl.setFocus()

  def glFocusChanged(self, glHasFocus):
    '''Activates when focus of gl widget changes'''
    if glHasFocus:
      self.glDSF.setRadius(20)
    else:
      self.glDSF.setRadius(0)
    self.glDSF.update()

  def updateMenu(self):
    '''Update menu's checkboxes'''
    self.viewMenu_env.setChecked(self.envPane.isVisible())
    self.viewMenu_edit.setChecked(self.editPane.isVisible())
    self.viewMenu_log.setChecked(self.logPane.isVisible())

  def curryTogglePane(self, pane):
    '''Get function for toggling the visibility of pane'''
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
    self.bulbList.clear()
    self.modelList.clear()
    self.lampList.clear()
    self.rendTree.clear()

  def fullMode(self):
    '''Set rendering mode to FULL'''
    engine.renderingMode = engine.FULL
    self.gl.update()

  def flatMode(self):
    '''Set rendering mode to FLAT'''
    engine.renderingMode = engine.FLAT
    self.gl.update()

  def toggleMode(self):
    '''Toggle rendering mode between FLAT and FULL'''
    engine.renderingMode += 1
    engine.renderingMode %= engine.NUM_MODES
    self.gl.update()

  def addEnvObj(self, envobj, directory=None):
    '''Add environment object into appropriate QListWidget'''
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
    '''Add Asset or Renderable, optionally to a directory'''
    if directory is None:
      directory = self.rendTree.getCurrentDir()
    if self.remote.add(obj, directory):
      return
    self.addEnvObj(obj, directory)
##    self.remote.getScene().debug_tree()

  def setCurrentFilename(self, fn, silent=False):
    '''Set fn as the current filename to save to'''
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
    self.remote.new()
    if base:
      B = Bulb(name="Main Bulb")
      self.add(B)
      self.add(Lamp(B, pos=Point(1, 1.7579, 0.7396), name="Main Lamp"))
      T = Tex("./assets/textures/white.png", name="White")
      M = Mesh("./assets/meshes/cube.obj", name="Cube")
      self.add(T)
      self.add(M)
      default_cube = Model(M, T)
      main_directory = Directory(name="Main")
      self.add(main_directory)
      self.add(default_cube, main_directory)
      cam = self.remote.getCamera()
      cam.pos = Point(-2, 2, 2)
      self.remote.lookAt(default_cube)
      
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
      self.saver.save(self.filename)
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
        self.saver.save(fn)
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
      self.load(fn, setGlobals=False)

  def load(self, fn, setGlobals=True):
    '''Load project from filename fn'''
    try:
      self.saver.load(fn, setGlobals=setGlobals)
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
    if self.saver.canRestore() and YNPrompt(self, "Restore", "Restore previous session?"):
      try:
        self.newProject(silent=True)
        self.saver.load_appdata(setGlobals=False)
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
    '''Make new Bulb with default settings'''
    B = Bulb()
    # Modify bulb with modal: TODO
    self.add(B)
    self.logEntry("Success", "Made bulb.")

  def loadAssetFile(self, fn):
    '''Load asset from file fn'''
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
      engine.exporting = True
      self.gl.paintGL()
      im = self.gl.grabFrameBuffer()
      engine.exporting = False
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
    basepos, baserot = basePosRot(self.remote.getCamera().pos, self.remote.getCamera().rot, engine.monoselected)
    basex, basey, basez = basepos
    baserx, basery, baserz = [cyclamp(r*180/pi, (-180, 180)) for r in baserot]
    x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basex)
    y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basey)
    z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basez)
    rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserx), suffix="°")
    ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=basery), suffix="°")
    rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserz), suffix="°")
    sx = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
    sy = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
    sz = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
##    scale = WidgetRow([sx, sy, sz])
    poseLayout.addRow("x", x)
    poseLayout.addRow("y", y)
    poseLayout.addRow("z", z)
    poseLayout.addRow("Yaw", ry)
    poseLayout.addRow("Pitch", rx)
    poseLayout.addRow("Roll", rz)
    poseLayout.addRow("Scale x", sx)
    poseLayout.addRow("Scale y", sy)
    poseLayout.addRow("Scale z", sz)

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

    def tryMakeModel():
      '''Attempt to construct Model from selected settings'''
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
                    pos=pos, rot=rot, scale=np.array([sx.value(), sy.value(), sz.value()]),
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
    '''Show modal for making lamps'''
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
    basepos, _ = basePosRot(self.remote.getCamera().pos, self.remote.getCamera().rot, engine.monoselected)
    basex, basey, basez = basepos
    x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basex)
    y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basey)
    z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basez)
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
    '''Show modal for making groups'''
    M = Modal(self)
    M.setWindowTitle("Make Groups")
    layout = QGridLayout()
    M.setLayout(layout)

    # POSE GROUP BOX
    poseBox = QGroupBox("Pose")
    layout.addWidget(poseBox, 0,0, 1,1)
    poseLayout = QFormLayout()
    poseBox.setLayout(poseLayout)
    basepos, baserot = basePosRot(self.remote.getCamera().pos, self.remote.getCamera().rot, engine.monoselected)
    basex, basey, basez = basepos
    baserx, basery, baserz = [cyclamp(r*180/pi, (-180, 180)) for r in baserot]
    x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basex)
    y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basey)
    z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=basez)
    rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserx), suffix="°")
    ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=basery), suffix="°")
    rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180, value=baserz), suffix="°")
    sx = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sy = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sz = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    scale = WidgetRow([sx, sy, sz])
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

    def tryMakeGroup():
      '''Attempt to construct Group from selected settings'''
      nonlocal lastx, lasty, lastz # allows access to lastx, lasty, lastz declared in the outer function
      xv, yv, zv = x.value(), y.value(), z.value()
      pos = Point(xv, yv, zv)
      rot = Rot(pi*rx.value()/180, pi*ry.value()/180, pi*rz.value()/180)
      group = Directory(pos=pos, rot=rot, scale=np.array([sx.value(), sy.value(), sz.value()]),
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
    '''Make Group in current Directory'''
    cam = self.remote.getCamera()
    directory = Directory()
    directory.pos, directory.rot = basePosRot(cam.pos, cam.rot, engine.monoselected)
    directory.name = "My Group"
    self.add(directory)
    self.select(directory)

  def recolorAmbientLight(self):
    '''Prompt user to recolor the ambient light'''
    M = QColorDialog(self)
    C = M.getColor()
    self.remote.getScene().ambientColor = C.redF(), C.greenF(), C.blueF()
    self.updateSceneEdit()

  def initEditPane(self):
    '''Initialise the edit pane'''
    self.initSceneEdit()
    self.initCamEdit()
    self.initSelEdit()

  def initSceneEdit(self):
    L = self.sceneEditLayout = QVBoxLayout()
    self.sceneEdit.setLayout(L)

    heading = QLabel("Scene", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    ambientColor = self.sceneEdit_ambientColor = QLineEdit(readOnly=True)
    ambientPower = self.sceneEdit_ambientPower = QDoubleSpinBox(decimals=PRECISION, minimum=0.0, maximum=1.0, singleStep=0.01)
    recolorAmbient = self.sceneEdit_recolorAmbient = QPushButton(text="Recolor Ambient", icon=self.icons["Color"])

    ambientBox = QGroupBox("Ambient Light")
    ambientLayout = QFormLayout()
    ambientBox.setLayout(ambientLayout)
    ambientLayout.addRow("Color", ambientColor)
    ambientLayout.addRow("Power", ambientPower)
##    ambientLayout.addWidget(recolorAmbient)

    ambientPower.valueChanged.connect(self.updateScene)
    recolorAmbient.clicked.connect(self.recolorAmbientLight)

    L.addWidget(heading)
    L.addWidget(ambientBox)
    L.addWidget(recolorAmbient)

    self.updateSceneEdit()

  def initCamEdit(self):
    '''Initialises the camera tab on the edit pane'''
    L = self.camEditLayout = QVBoxLayout()
    self.camEdit.setLayout(L)

    heading = QLabel("Camera", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    x = self.camEdit_x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    y = self.camEdit_y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    z = self.camEdit_z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    rx = self.camEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.camEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.camEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    fovy = self.camEdit_fovy = QDoubleSpinBox(decimals=PRECISION, minimum=0.05, maximum=179.95, value=60, singleStep=0.05)
    zoom = self.camEdit_zoom = QDoubleSpinBox(decimals=PRECISION, minimum=1.0, maximum=1000.0, value=1, singleStep=0.05)
    for setting in [x, y, z, rx, ry, rz, fovy, zoom]:
      setting.valueChanged.connect(self.updateCamera)
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
    shininess = self.texEdit_shininess = QDoubleSpinBox(decimals=PRECISION, minimum=1, maximum=B32-1)
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
    power = self.bulbEdit_power = QDoubleSpinBox(decimals=PRECISION, minimum=0, maximum=B32-1)
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
    x = self.modelEdit_x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    y = self.modelEdit_y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    z = self.modelEdit_z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    rx = self.modelEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.modelEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.modelEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    sx = self.modelEdit_sx = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sy = self.modelEdit_sy = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sz = self.modelEdit_sz = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
##    scale = WidgetRow([sx, sy, sz])
    visible = self.modelEdit_visible = QCheckBox(text="Visible", tristate=False)
    mesh = self.modelEdit_mesh = QPushButton()
    tex = self.modelEdit_tex = QPushButton()
    
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
    poseLayout.addRow("Scale x", sx)
    poseLayout.addRow("Scale y", sy)
    poseLayout.addRow("Scale z", sz)

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)

    assetBox = QGroupBox("Assets")
    L.addWidget(assetBox)
    assetLayout = QFormLayout()
    assetBox.setLayout(assetLayout)
    assetLayout.addRow(iconLabel(self.icons["Mesh"]), mesh)
    assetLayout.addRow(iconLabel(self.icons["Texture"]), tex)

    change.clicked.connect(self.reinitSelected)
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(change)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, sx,sy,sz]:
      setting.valueChanged.connect(self.updateSelected)

    def selectMesh():
      assert isinstance(engine.monoselected, Model)
      if engine.monoselected.mesh.deleted:
        self.reinitSelected()
      else:
        self.select(engine.monoselected.mesh)
    mesh.clicked.connect(selectMesh)

    def selectTexture():
      assert isinstance(engine.monoselected, Model)
      if engine.monoselected.tex.deleted:
        self.reinitSelected()
      else:
        self.select(engine.monoselected.tex)
    tex.clicked.connect(selectTexture)
    
    visible.stateChanged.connect(self.updateSelected)

    W = self.modelEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===LAMP===
    L = QVBoxLayout()
    heading = QLabel("Lamp", font=self.fonts["heading"], alignment=Qt.AlignCenter)
    name = self.lampEdit_name = QLineEdit()
    change = self.lampEdit_change = QPushButton(text="Change Assets", icon=self.icons["Form"])
    delete = self.lampEdit_delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.lampEdit_x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    y = self.lampEdit_y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    z = self.lampEdit_z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    visible = self.lampEdit_visible = QCheckBox(text="Visible", tristate=False)
    bulb = self.lampEdit_bulb = QPushButton()

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
    assetLayout.addRow(iconLabel(self.icons["Bulb"]), bulb)

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
    
    def selectBulb():
      assert isinstance(engine.monoselected, Lamp)
      if engine.monoselected.bulb.deleted:
        self.reinitSelected()
      else:
        self.select(engine.monoselected.bulb)
    bulb.clicked.connect(selectBulb)

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
    x = self.dirEdit_x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    y = self.dirEdit_y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    z = self.dirEdit_z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    rx = self.dirEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.dirEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.dirEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    sx = self.dirEdit_sx = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
    sy = self.dirEdit_sy = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
    sz = self.dirEdit_sz = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=0.05)
##    scale = WidgetRow([sx, sy, sz])
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
    poseLayout.addRow("Scale x", sx)
    poseLayout.addRow("Scale y", sy)
    poseLayout.addRow("Scale z", sz)

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)
    
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, sx, sy, sz]:
      setting.valueChanged.connect(self.updateSelected)

    visible.stateChanged.connect(self.updateSelected)

    W = self.dirEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===LINK===
    L = QVBoxLayout()

    heading = QLabel("Symlink", font=self.fonts["heading"], alignment=Qt.AlignCenter)

    name = self.linkEdit_name = QLineEdit()
    directory = self.linkEdit_directory = QPushButton(icon=self.icons["Link"])
    delete = QPushButton(text="Delete", icon=self.icons["Delete"])
    x = self.linkEdit_x = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    y = self.linkEdit_y = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    z = self.linkEdit_z = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1)
    rx = self.linkEdit_rx = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    ry = self.linkEdit_ry = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    rz = self.linkEdit_rz = BetterSlider(QSlider(Qt.Horizontal, tickPosition=1, tickInterval=90, minimum=-180, maximum=180), suffix="°")
    sx = self.linkEdit_sx = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sy = self.linkEdit_sy = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
    sz = self.linkEdit_sz = QDoubleSpinBox(decimals=PRECISION, minimum=-B32, maximum=B32-1, value=1, singleStep=1)
##    scale = WidgetRow([sx, sy, sz])
    visible = self.linkEdit_visible = QCheckBox(text="Visible", tristate=False)
    
    L.addWidget(heading)
    
    name.textChanged.connect(self.updateSelected)
    L.addWidget(name)
    L.addWidget(directory)

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
    poseLayout.addRow("Scale x", sx)
    poseLayout.addRow("Scale y", sy)
    poseLayout.addRow("Scale z", sz)

    sceneBox = QGroupBox("Scene")
    L.addWidget(sceneBox)
    sceneLayout = QFormLayout()
    sceneBox.setLayout(sceneLayout)
    sceneLayout.addWidget(visible)

    def selectDirectory():
      assert isinstance(engine.monoselected, Link)
      self.select(engine.monoselected.directory)
    directory.clicked.connect(selectDirectory)
    
    delete.clicked.connect(self.deleteSelected)
    L.addWidget(delete)

    for setting in [x,y,z, rx,ry,rz, sx,sy,sz]:
      setting.valueChanged.connect(self.updateSelected)

    visible.stateChanged.connect(self.updateSelected)

    W = self.linkEdit = QWidget()
    W.setLayout(L)
    self.selEdit.addWidget(W)

    #===UPDATE===
    self.updateSelEdit()

  def updateSceneEdit(self):
    ambientColor = self.remote.getScene().ambientColor
    ambientPower = self.remote.getScene().ambientPower
    self.sceneEdit_ambientColor.setText(rrggbb(*ambientColor))
    self.sceneEdit_ambientPower.setValue(ambientPower)

  def updateScene(self):
    ambientPower = self.sceneEdit_ambientPower.value()
    self.remote.getScene().ambientPower = ambientPower
    self.gl.update()

  def updateCamEdit(self): # true settings -> displayed settings
    '''Updates the displayed settings for the camera'''
    x, y, z = self.remote.getCamera().pos
    rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in self.remote.getCamera().rot)
    fovy = self.remote.getCamera().fovy
    zoom = self.remote.getCamera().zoom
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

  def updateCamera(self): # displayed settings -> true settings
    '''Updates the camera variables from the displayed settings'''
    pos = Point(self.camEdit_x.value(),
                self.camEdit_y.value(),
                self.camEdit_z.value())
    rot = Rot(pi*self.camEdit_rx.value()/180,
              pi*self.camEdit_ry.value()/180,
              pi*self.camEdit_rz.value()/180)
    fovy = self.camEdit_fovy.value()
    zoom = self.camEdit_zoom.value()
    self.remote.configCamera(pos=pos, rot=rot, fovy=fovy, zoom=zoom)
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
          self.remote.delete(S)
          S.__dict__ = newMesh.__dict__
          self.remote.add(S)
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
          self.remote.delete(S)
          S.__dict__ = newTex.__dict__
          self.remote.add(S)
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

    elif type(S) is Lamp:
      M = Modal(self)
      M.setWindowTitle("Change Lamp")
      layout = QGridLayout()
      M.setLayout(layout)

      assetBox = QGroupBox("Assets")
      layout.addWidget(assetBox)
      assetLayout = QFormLayout()
      assetBox.setLayout(assetLayout)
      bList = copyObjList(self.bulbList)
      assetLayout.addRow("Bulb", bList)

      if not S.bulb.deleted:
        bList.setCurrentRow(bList.find(S.bulb))

      def tryChangeLamp():
        b = bList.selectedItems()
        if not len(b):
          return
        S.bulb = b[0].obj
        self.update()

      bList.itemClicked.connect(tryChangeLamp)
      M.exec_()

    self.updateSelEdit()


  def deleteSelected(self):
    '''Deletes selected object'''
    self.delete(engine.monoselected)
    self.update()

  def delete(self, obj):
    '''Deletes object (Mesh, Tex, Model, or Lamp) from user environment, ui list, and file cache and deselects it'''
    # delete any links to the obj
    links = []
    if isinstance(obj, Directory):
      for link in self.remote.getLinksTo(obj):
        links.append(link)
    for link in links:
      self.delete(link)

    # Remove from list/tree
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
      
    self.remote.delete(obj)
    # Deselect object
    engine.selected.discard(obj)
    if isinstance(engine.monoselected, Renderable):
      engine.monoselected.update_bbox()
    if engine.monoselected is obj:
      self.select(None)

  def copySelected(self):
    engine.clipboard = engine.monoselected
    self.logEntry("Success", "Copied %s."%engine.monoselected.name)

  def shallowPaste(self, obj):
    cam = self.remote.getCamera()
    if obj is not None:
      try:
        sCopy = copy.copy(obj)
        if isinstance(sCopy, Renderable):
          sCopy.pos, sCopy.rot = obj.pos, obj.rot
        self.add(sCopy)
      except TreeError as e:
        self.logEntry("Error", "Symlink cycle: %s"%e)
      else:
        self.logEntry("Success", "Deep pasted %s."%obj.name)

  def deepPaste(self, obj):
    cam = self.remote.getCamera()
    if obj is not None:
      try:
        dCopy = copy.deepcopy(obj)
        if isinstance(dCopy, Renderable):
          dCopy.pos, dCopy.rot = obj.pos, obj.rot
        self.add(dCopy)
      except TreeError as e:
        self.logEntry("Error", "Symlink cycle: %s"%e)
      else:
        self.logEntry("Success", "Deep pasted %s."%obj.name)

  def shallowPasteClipboard(self):
    self.shallowPaste(engine.clipboard)

  def deepPasteClipboard(self):
    try:
      self.deepPaste(engine.clipboard)
    except:
      traceback.print_exc()

  def shallowPasteSelected(self):
    sel = engine.monoselected
    self.selectParent()
    self.shallowPaste(sel)
    self.select(sel)

  def deepPasteSelected(self):
    sel = engine.monoselected
    self.selectParent()
    self.deepPaste(sel)
    self.select(sel)

  def move(self, rend, directory):
    try:
      if rend.parent is None:
        self.remote.getScene().discard(rend)
      rend.setParent(directory)
      if rend.parent is None:
        self.remote.getScene().add(rend)
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
      S.scale = np.array([nonzero(self.modelEdit_sx.value()),
                          nonzero(self.modelEdit_sy.value()),
                          nonzero(self.modelEdit_sz.value())])
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
      S.scale = np.array([nonzero(self.dirEdit_sx.value()),
                          nonzero(self.dirEdit_sy.value()),
                          nonzero(self.dirEdit_sz.value())])
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
      S.scale = np.array([nonzero(self.linkEdit_sx.value()),
                          nonzero(self.linkEdit_sy.value()),
                          nonzero(self.linkEdit_sz.value())])
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
      sx, sy, sz = S.scale
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
                           (self.modelEdit_sx, sx),
                           (self.modelEdit_sy, sy),
                           (self.modelEdit_sz, sz)]:
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
      sx, sy, sz = S.scale
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
                           (self.dirEdit_sx, sx),
                           (self.dirEdit_sy, sy),
                           (self.dirEdit_sz, sz)]:
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
      dirName = S.directory.name
      x, y, z = S.pos
      rx, ry, rz = S.rot
      rx, ry, rz = (cyclamp(r*180/pi, (-180, 180)) for r in S.rot)
      sx, sy, sz = S.scale
      visible = S.visible
      
      for setting, text in [(self.linkEdit_name, name),
                            (self.linkEdit_directory, dirName)]:
        setting.blockSignals(True)
        setting.setText(text)
        setting.blockSignals(False)
      
      for setting, var in [(self.linkEdit_x, x),
                           (self.linkEdit_y, y),
                           (self.linkEdit_z, z),
                           (self.linkEdit_rx, rx),
                           (self.linkEdit_ry, ry),
                           (self.linkEdit_rz, rz),
                           (self.linkEdit_sx, sx),
                           (self.linkEdit_sy, sy),
                           (self.linkEdit_sz, sz)]:
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

  def highlight(self, rend):
    engine.highlighted = rend

  def update(self):
    '''Overload: update to display correct features'''
    self.updateMenu()
    self.updateSceneEdit()
    self.updateCamEdit()
    self.updateSelEdit()
    self.gl.update()

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
    self.saver.update()
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

  def selectFromXY(self, XY):
    XY = self.gl.qt2glXY(XY)
    self.select(self.remote.getScene().getRendFromXY(XY, self.remote.getCamera(), self.gl.aspect))

  def highlightFromXY(self, XY):
    XY = self.gl.qt2glXY(XY)
    self.highlight(self.remote.getScene().getRendFromXY(XY, self.remote.getCamera(), self.gl.aspect))

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
