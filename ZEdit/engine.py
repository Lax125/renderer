#!/usr/bin/env python
'''
engine.py
describes 3-D scenes and it's rendering process
with the help of OpenGL

Rendering is based on a single projection matrix and a stack of modelview matrices.
The stack is used to walk through a tree of Renderables in a depth-first search.
Whenever a Renderable is processed in the dfs, it modifies the current working
modelview matrix and pushes it onto the stack. Several layers of matrix math
are handled, each layer consisting of a translation, rotation, and scaling.
'''

from all_modules import *

# CUSTOM SCRIPTS FOR:
#   - DESCRIBING POSITIONS IN 3-D AND ROTATIONAL ORIENTATION
#   - LOADING SHADERS
from rotpoint import Point, Rot
from shader import *
from asset import id_gen

EPSILON = abs(0.3 - 0.1 - 0.1 - 0.1)

# FOR LOGGING
FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('engine')

NUM_MODES = 2
FLAT = 0
FULL = 1
exporting = False
renderingMode = FULL
selected = set()
monoselected = None
highlighted = None
clipboard = None
camPos = None
camTrueFovy = None
linkDepth = 0

def mix_permute(A, B):
  '''
Generates all permutations of mixing lists A and B.
Example - mix_permute([1, 2, 3], [4, 5, 6]) yields:
   [1, 2, 3],
   [1, 2, 6],
   [1, 5, 3],
   [1, 5, 6],
   [4, 2, 3],
   [4, 2, 6],
   [4, 5, 3],
   [4, 5, 6]
  '''
  if len(A) == 0 or len(B) == 0:
    yield []
    return
  for l in mix_permute(A[:-1], B[:-1]):
    yield l+[A[-1]]
    yield l+[B[-1]]

def normalize(xyz):
  '''Returns normalized version of vector xyz'''
  magnitude = np.linalg.norm(xyz)
  return xyz/magnitude

def glGetModelview():
  '''Get OpenGL Model*View transformation matrix'''
  return np.matrix(glGetFloatv(GL_MODELVIEW_MATRIX))

def glGetModelviewPos():
  '''Get position from OpenGL Model*View transformation matrix'''
  A = np.array(glGetModelview())
  return np.array(A[3,0:3])

def glGetModelviewAxes():
  '''
Gets 3 vectors that define the 3 axes (x,y,z)
from OpenGL Model*View transformation matrix.
  '''
  A = np.array(glGetModelview())
  return A[0,0:3], A[1,0:3], A[2,0:3]

def glApplyRot(rot, invert=False):
  '''Applies rotation (rx, ry, rz) with this program's rotational standards.'''
  rx, ry, rz = rot
  if not invert:
    glRotate(degrees(-ry), 0.0, 1.0, 0.0)
    glRotate(degrees(rx), 1.0, 0.0, 0.0)
    glRotate(degrees(-rz), 0.0, 0.0, 1.0)
  else:
    glRotate(-degrees(-rz), 0.0, 0.0, 1.0)
    glRotate(-degrees(rx), 1.0, 0.0, 0.0)
    glRotate(-degrees(-ry), 0.0, 1.0, 0.0)

def gluGlobe():
  '''
Places a radius 1 sphere where OpenGL's Model*View
transformation matrix iswithout writing to depth buffer.
  '''
  glMatrixMode(GL_MODELVIEW)
  glPushMatrix()
  PLAIN_SHADER.use()
  glColor4f(0.0, 0.0, 0.0, 0.0)
  glLineWidth(1)
  glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
  glDepthMask(False)
  glRotated(90, 1,0,0)
  gluSphere(gluNewQuadric(), 1, 24, 12)
  glRotated(-90, 1,0,0)
  glDepthMask(True)
  glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
  glPopMatrix()

def gluCamera(camera, aspect):
  glMatrixMode(GL_PROJECTION)
  glLoadIdentity()
  defacto_fovy = degrees(atan(tan(radians(camera.fovy)/2)/camera.zoom))*2
  gluPerspective(defacto_fovy, aspect, *camera.zRange)
  glMatrixMode(GL_MODELVIEW)
  glLoadIdentity()
  gluLookAt(0,0,0, *camera.rot.get_forward_vector(invert=True), *camera.rot.get_upward_vector(invert=True))
  glTranslatef(*-camera.pos)

def testRayBBIntersection(rayV, BBmin, BBmax):
  '''Test if a ray from modelview origin intersects a bounding box in current modelview matrix. Returns the distance if they instersect and None they do not.'''
  ## credit: http://www.opengl-tutorial.org/miscellaneous/clicking-on-objects/picking-with-custom-ray-obb-function/
  rayV = np.array(rayV)
  BBmin = np.array(BBmin)
  BBmax = np.array(BBmax)
  invertedModelview = glGetModelview()**-1
  # test if origin is in the OBB
  xyz1 = np.matrix([0.0, 0.0, 0.0, 1.0])*invertedModelview
  origin_rel = np.array(xyz1).flatten()[0:3]
  if (BBmin < origin_rel).all() and (origin_rel < BBmax).all():
    return None
  dMin = 0.0
  dMax = float('Inf')
  rayV_rel = np.array(np.matrix([*rayV, 1.0])*invertedModelview).flatten()[0:3] - origin_rel
##  print()
##  print(origin_rel, rayV_rel)
  # test all axes
  def extrapolateDistance(xyz, dxyz, axis, n):
    if dxyz[axis] == 0:
      return float("Inf")
    m = np.linalg.norm(dxyz)/dxyz[axis]
    a = n - xyz[axis]
    return a*m
  # x
  d1 = extrapolateDistance(origin_rel, rayV_rel, 0, BBmin[0])
  d2 = extrapolateDistance(origin_rel, rayV_rel, 0, BBmax[0])
##  print("x", d1, d2)
  if d1 > d2:
    d1, d2 = d2, d1
  dMin = max(dMin, d1)
  dMax = min(dMax, d2)
  if dMax < dMin:
    return None

  # y
  d1 = extrapolateDistance(origin_rel, rayV_rel, 1, BBmin[1])
  d2 = extrapolateDistance(origin_rel, rayV_rel, 1, BBmax[1])
##  print("y", d1, d2)
  if d1 > d2:
    d1, d2 = d2, d1
  dMin = max(dMin, d1)
  dMax = min(dMax, d2)
  if dMax < dMin:
    return None

  # z
  d1 = extrapolateDistance(origin_rel, rayV_rel, 2, BBmin[2])
  d2 = extrapolateDistance(origin_rel, rayV_rel, 2, BBmax[2])
##  print("z", d1, d2)
  if d1 > d2:
    d1, d2 = d2, d1
  dMin = max(dMin, d1)
  dMax = min(dMax, d2)
  if dMax < dMin:
    return None

  return dMin

class Camera:
  '''Describes a camera in 3-D position and rotation'''
  
  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), fovy=60, zoom=1.0, zRange=(0.1, 10000)):
    '''Initialise a Camera object in a position and rotation'''
    self.pos = pos
    self.rot = rot
    self.fovy = fovy # field of view in degrees in y axis
    self.zoom = zoom # true fovy == atan(tan(fovy/2)/zoom)*2
    self.zRange = zRange # visible slice of the scene

  def get_forward_vector(self, *args, **kwargs):
    return self.rot.get_forward_vector(*args, **kwargs)

  def get_upward_vector(self, *args, **kwargs):
    return self.rot.get_upward_vector(*args, **kwargs)

  def getTrueFovy(self):
    return degrees(atan(tan(radians(self.fovy)/2)/self.zoom))*2

class Renderable:
  '''Base class for renderable objects: Models, Lamps'''
##  IDs = id_gen(1)
##  rendDict = dict()
  
  def __init__(self, pos=Point(0, 0, 0), rot=Rot(0, 0, 0), scale=np.array([1.0, 1.0, 1.0]), visible=True, name="renderable0"):
##    self.ID = next(Renderable.IDs)
##    Renderable.rendDict[self.ID] = self
    self.parent = None
    self.pos = pos
    self.rot = rot
    self.scale = scale
    self.visible = visible
    self.name = name
    self.minPoint = Point(0, 0, 0)
    self.maxPoint = Point(0, 0, 0)
    self.update_bbox()
    self.init_axes()

  def __str__(self):
    return self.name

  def glMat(self, invert=False): # gl transform according to position, orientation, and scale
    if not invert:
      # TRANSLATE
      glTranslatef(*self.pos)

      # ROTATE
      glApplyRot(self.rot)

      # SCALE
      glScalef(self.scale[0], self.scale[1], self.scale[2])
    else:
      glScalef(1/self.scale[0], 1/self.scale[1], 1/self.scale[2])
      glApplyRot(self.rot, invert=True)
      glTranslatef(*-self.pos)

  def place(self): # overload with function that puts the renderable in the OpenGL environment
    pass

  def placeASel(self):
    pass

  def placeSel(self): # place extra stuff because i am selected
    pass

  def placeMonosel(self): # place extra stuff because i am THE selected
    pass

  def placeHighlight(self):
    self.placeBBox()
    self.placeSel()

  def placeBBox(self):
    PLAIN_SHADER.use()
    glEnable(GL_BLEND)
    if renderingMode == FULL:
      glColor4f(1.0, 1.0, 1.0, 0.75)
    elif renderingMode == FLAT:
      glColor4f(0.0, 0.0, 0.0, 0.75)
    glLineWidth(3)
    V, LINE_I = self.vbo_bbox_buffers
    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, V)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, LINE_I)
    glDrawElements(GL_LINES, len(self.vbo_bbox_line_indices), GL_UNSIGNED_INT, None)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisable(GL_BLEND)

  def placeAxes(self):
    PLAIN_SHADER.use()
    glLineWidth(5)
    V, C, LINE_I = self.vbo_axes_buffers
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_COLOR_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, V)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, C)
    glColorPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, LINE_I)
    glDrawElements(GL_LINES, len(self.vbo_bbox_line_indices), GL_UNSIGNED_INT, None)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_COLOR_ARRAY)

  def placePlanes(self):
    PLAIN_SHADER.use()
    # Face culling is, by default, disabled
    glEnable(GL_BLEND) # needed for alpha
    glDepthMask(False) # prevent writing to depth buffer
    V, TRI_I = self.vbo_plane_buffers
    glColor4f(1.0, 1.0, 1.0, 0.25)
    glEnableClientState(GL_VERTEX_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, V)
    glVertexPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, TRI_I)
    glDrawElements(GL_TRIANGLES, len(self.vbo_plane_tri_indices), GL_UNSIGNED_INT, None)
    glDepthMask(True) # resume writing to depth buffer
    glDisable(GL_BLEND) # needed for alpha

  def placeOrigin(self):
    PLAIN_SHADER.use()
    glEnable(GL_BLEND)
    glColor4f(0.0, 0.0, 1.0, 0.2)
##    glLineWidth(10)
##    x, y, z = self.getTruePos()
##    camx, camy, camz = camPos
##    dist = ((x-camx)**2 + (y-camy)**2 + (z-camz)**2)**0.5
##    scale = tan(radians(camTrueFovy))*dist/(100*glGetScale())
##    gluSphere(gluNewQuadric(), scale, 25, 25)
    gluSphere(gluNewQuadric(), 1, 25, 25)
    glDisable(GL_BLEND)

  def renderLight(self):
    self.glMat()
  
  def render(self, ancestorSelected=False):
    self.glMat()
    if self.visible:
      self.place()
    if exporting:
      return
    if ancestorSelected:
      self.placeASel()
    if self in selected:
      self.placeBBox()
      self.placeSel()
    if self is highlighted:
      self.placeHighlight()
    if self is monoselected and linkDepth == 0:
      self.placeAxes()
      self.placeMonosel()
  
  def renderSelectedAE(self):
    '''render after effects for selected'''
    if exporting:
      return
    self.glMat()
    if self is monoselected:
      self.placePlanes()
    # dashed lines for hidden lines
    glLineStipple(1, 0x000F)
    glEnable(GL_LINE_STIPPLE)
    glDepthFunc(GL_GREATER) # render the following if it is behind
    if self in selected:
      self.placeBBox()
    if self is monoselected:
      self.placeAxes()
    glDepthFunc(GL_LESS)
    glDisable(GL_LINE_STIPPLE)

  def renderOverlay(self):
    if exporting:
      return
    self.glMat()
    if self is highlighted:
      self.placeOrigin()

  def _setParent(self, parent):
    # remove self from parent's set
    if self.parent is not None:
      self.parent.rends.discard(self)

    # add self to new parent
    if parent is not None:
      parent.rends.add(self)

    self.parent = parent

  def setParent(self, parent):
    # check for loops
    old_parent = self.parent
    self._setParent(parent)
    hasCycle, badPath = self.cycleCheck()
    if hasCycle:
      self._setParent(old_parent)
      raise TreeError(badPath)

  def getPath(self):
    if self.parent is None:
      return [self]
    result = self.parent.getPath()
    result.append(self) # avoids quadratic time antipattern
    return result

  def getTruePos(self, basePos=(0, 0, 0)):
    # xyz in my modelview matrix to xyz in world
    glPushMatrix()
    glLoadIdentity()
##    glTranslatef(*basePos)
    for rend in self.getPath():
      rend.glMat()
    M = np.matrix([[*basePos, 1]])
    T = glGetModelview()
    R = np.array(M*T)
    glPopMatrix()
    return Point(*R[0,0:3])

  def getTrueRot(self, baseRot=(0, 0, 0)):
    glPushMatrix()
    glLoadIdentity()
    glApplyRot(baseRot, invert=True)
    for rend in self.getPath():
      rend.glMat()
    r = Rot.from_transmat(glGetModelview())
    glPopMatrix()
    return r

  def getBasePos(self, truePos=(0, 0, 0)):
    # inverse of getTruePos: xyz in world to xyz in my modelview matrix
    glPushMatrix()
    glLoadIdentity()
    for rend in self.getPath()[-1::-1]:
      rend.glMat(invert=True)
    M = np.matrix([[*truePos, 1]])
    T = glGetFloatv(GL_MODELVIEW_MATRIX)
    R = np.array(M*T)
    glPopMatrix()
    return Point(*R[0,0:3])

  def getDirBasePos(self, truePos=(0, 0, 0)):
    # xyz in world to xyz in my directory's modelview matrix
    glPushMatrix()
    glLoadIdentity()
    for rend in self.getPath()[-2::-1]:
      rend.glMat(invert=True)
    M = np.matrix([[*truePos, 1]])
    T = glGetFloatv(GL_MODELVIEW_MATRIX)
    R = np.array(M*T)
    glPopMatrix()
    return Point(*R[0,0:3])

  def getBaseRot(self, trueRot=(0, 0, 0)):
    glPushMatrix()
    glLoadIdentity()
    for rend in self.getPath()[-1::-1]:
      rend.glMat(invert=True)
    glApplyRot(trueRot)
    r = Rot.from_transmat(glGetModelview())
    glPopMatrix()
    return r

  def getDirBaseRot(self, trueRot=(0, 0, 0)):
    glPushMatrix()
    glLoadIdentity()
    for rend in self.getPath()[-2::-1]:
      rend.glMat(invert=True)
    glApplyRot(trueRot)
    r = Rot.from_transmat(glGetModelview())
    glPopMatrix()
    return r

  def update_bbox(self):
    self.vbo_bbox_vertices = []
    for xyz in mix_permute(self.minPoint, self.maxPoint):
      self.vbo_bbox_vertices.extend(xyz)
    self.vbo_bbox_line_indices = [0,1, 0,2, 0,4,
                                  1,3, 1,5, 2,3,
                                  2,6, 4,5, 4,6,
                                  3,7, 5,7, 6,7]

    # update buffers
    buffers = glGenBuffers(2)
    glBindBuffer(GL_ARRAY_BUFFER, buffers[0])
    glBufferData(GL_ARRAY_BUFFER,
                 len(self.vbo_bbox_vertices)*4,
                 (ctypes.c_float*len(self.vbo_bbox_vertices))(*self.vbo_bbox_vertices),
                 GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffers[1])
    glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                 len(self.vbo_bbox_line_indices)*4,
                 (ctypes.c_uint*len(self.vbo_bbox_line_indices))(*self.vbo_bbox_line_indices),
                 GL_STATIC_DRAW)
    self.vbo_bbox_buffers = buffers

    self.update_planes()

  def update_planes(self):
    minx, miny, minz = self.minPoint
    maxx, maxy, maxz = self.maxPoint
    self.vbo_plane_vertices = [minx, miny,  0.0,
                               minx, maxy,  0.0,
                               maxx, maxy,  0.0,
                               maxx, miny,  0.0,
                                0.0, miny, minz,
                                0.0, miny, maxz,
                                0.0, maxy, maxz,
                                0.0, maxy, minz,
                               minx,  0.0, minz,
                               maxx,  0.0, minz,
                               maxx,  0.0, maxz,
                               minx,  0.0, maxz,
                               ]
    self.vbo_plane_tri_indices = [ 0, 1, 2,  0, 2, 3,
                                   4, 5, 6,  4, 6, 7,
                                   8, 9,10,  8,10,11,
                                  12,13,14, 12,14,15
                                  ]
    buffers = glGenBuffers(2)
    glBindBuffer(GL_ARRAY_BUFFER, buffers[0])
    glBufferData(GL_ARRAY_BUFFER,
                 len(self.vbo_plane_vertices)*4,
                 (ctypes.c_float*len(self.vbo_plane_vertices))(*self.vbo_plane_vertices),
                 GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffers[1])
    glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                 len(self.vbo_plane_tri_indices)*4,
                 (ctypes.c_uint*len(self.vbo_plane_tri_indices))(*self.vbo_plane_tri_indices),
                 GL_STATIC_DRAW)
    self.vbo_plane_buffers = buffers

  def init_axes(self):
    self.vbo_axes_vertices = [0.0, 0.0, 0.0,
                              100000.0, 0.0, 0.0,
                              0.0, 0.0, 0.0,
                              0.0, 100000.0, 0.0,
                              0.0, 0.0, 0.0,
                              0.0, 0.0, -100000.0]
    self.vbo_axes_colors = [1.0, 0.0, 0.0,
                            1.0, 0.0, 0.0,
                            0.0, 1.0, 0.0,
                            0.0, 1.0, 0.0,
                            0.0, 0.0, 1.0,
                            0.0, 0.0, 1.0]
    self.vbo_axes_line_indices = [0,1, 2,3, 4,5]
    buffers = glGenBuffers(3)
    glBindBuffer(GL_ARRAY_BUFFER, buffers[0])
    glBufferData(GL_ARRAY_BUFFER,
                 len(self.vbo_axes_vertices)*4,
                 (ctypes.c_float*len(self.vbo_axes_vertices))(*self.vbo_axes_vertices),
                 GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, buffers[1])
    glBufferData(GL_ARRAY_BUFFER,
                 len(self.vbo_axes_colors)*4,
                 (ctypes.c_float*len(self.vbo_axes_colors))(*self.vbo_axes_colors),
                 GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffers[2])
    glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                 len(self.vbo_axes_line_indices)*4,
                 (ctypes.c_uint*len(self.vbo_axes_line_indices))(*self.vbo_axes_line_indices),
                 GL_STATIC_DRAW)
    self.vbo_axes_buffers = buffers

  def cycleCheck(self):
    todo = [[self]]
    while todo:
      next_dir = todo.pop(-1)
      for next_node in next_dir[-1].cycleCheckChildren():
        if next_node in next_dir: # loop!
          return True, next_dir + [next_node]
        todo.append(next_dir+[next_node])
    return False, []

  def cycleCheckChildren(self):
    return []

  def rayBBIntersections(self, rayV):
    self.glMat()
    dist = testRayBBIntersection(rayV, self.minPoint, self.maxPoint)
    if dist is None:
      return
    yield self, dist

class Model(Renderable):
  '''Describes polyhedron-like 3-D model in a position and orientation'''
  
  def __init__(self, mesh, tex, *args, **kwargs):
    '''Initialise 3-D model from loaded mesh and texture files with position pos, rotation rot, and scale scale'''
    self.mesh = mesh
    self.tex = tex
    super().__init__(*args, **kwargs)

  def __repr__(self):
    reprtuple = (repr(self.mesh), repr(self.tex), repr(self.pos), repr(self.rot), repr(self.scale), repr(self.visible))
    return "Model(%s, %s, pos=%s, rot=%s, scale=%s, visible=%s)"%reprtuple

  def __copy__(self):
    # all attributes are immutable
    return Model(self.mesh, self.tex, pos=self.pos, rot=self.rot, scale=self.scale.copy(), visible=self.visible, name=self.name)

  def __deepcopy__(self, memo):
    return copy.copy(self) # i am a dead end

  def place(self):
    if renderingMode == FULL:
      PHONG_SHADER.use()
    elif renderingMode == FLAT:
      PLAIN_SHADER.use()
      glColor4f(0.0, 0.0, 0.0, 1.0)
      glLineWidth(2)
      self.mesh.render_wireframe()
      FLAT_SHADER.use()
    glColor4f(1.0, 1.0, 1.0, 1.0)
    if np.prod(self.scale) < 0.0:
      glFrontFace(GL_CW)
    self.mesh.render(self.tex)
    glFrontFace(GL_CCW)

  def placeASel(self):
    PLAIN_SHADER.use()
    glEnable(GL_BLEND)
    glColor4f(0.79, 0.75, 1.0, 0.5)
    glLineWidth(2)
    self.mesh.render_wireframe()
    glDisable(GL_BLEND)

  def placeSel(self):
    PLAIN_SHADER.use()
    glEnable(GL_BLEND)
    glColor4f(0.79, 1.0, 0.75, 0.5)
    glLineWidth(2)
    self.mesh.render_wireframe()
    glDisable(GL_BLEND)

  def update_bbox(self):
    self.minPoint = Point(*self.mesh.min_xyz)
    self.maxPoint = Point(*self.mesh.max_xyz)
    super().update_bbox()

class Lamp(Renderable):
  '''A light source'''
  i = 0
  lPositions = np.empty((MAX_LIGHTS, 3), np.float32)
  lColorPowers = np.empty((MAX_LIGHTS, 3), np.float32)
  def __init__(self, bulb, *args, **kwargs):
    self.bulb = bulb
    super().__init__(*args, **kwargs)

  def begin():
    Lamp.i = 0

  def renderLight(self):
    if not self.visible:
      return
    super().renderLight()
    Lamp.lPositions[Lamp.i] = glGetModelviewPos()
    Lamp.lColorPowers[Lamp.i] = np.array(self.bulb.color) * self.bulb.power
    Lamp.i += 1

  def end():
    PHONG_SHADER.use()
    glUniform1i(Shader.current.uniformLocs["lCount"], Lamp.i)
    glUniform3fv(Shader.current.uniformLocs["lPositions"], Lamp.i, Lamp.lPositions)
    glUniform3fv(Shader.current.uniformLocs["lColorPowers"], Lamp.i, Lamp.lColorPowers)

  def update_bbox(self):
    self.minPoint = Point(-1, -1, -1)
    self.maxPoint = Point(1, 1, 1)
    super().update_bbox()

  def places_axes(self):
    pass

  def place(self):
    if renderingMode == FLAT:
      PLAIN_SHADER.use()
      glColor4f(1.0, 1.0, 0.0, 1.0)
      gluSphere(gluNewQuadric(), 1, 25, 25)

  def __copy__(self):
    return Lamp(self.bulb, pos=self.pos, rot=self.rot, scale=self.scale.copy(), visible=self.visible, name=self.name)

  def __deepcopy__(self, memo):
    return copy.copy(self)

class Directory(Renderable):
  # Provides an OpenGL matrix transformation to put other Renderables in
  def __init__(self, rends=None, *args, **kwargs):
    if rends is None:
      rends = set()
    self.rends = rends
    super().__init__(*args, **kwargs)

  def __iter__(self):
    return self.rends.__iter__()

  def __copy__(self):
    return Link(self)

  def __deepcopy__(self, memo):
    directory = Directory(pos=self.pos, rot=self.rot, scale=self.scale.copy(), visible=self.visible, name=self.name)
    for rend in self.rends:
      directory.add(copy.deepcopy(rend))
    return directory

  def add(self, rend):
    rend.setParent(self)

  def remove(self, rend):
    assert rend in self.rends
    rend.setParent(None)

  def discard(self, rend):
    rend.setParent(None)

  def clear(self):
    self.rends.clear()

  def renderLight(self):
    super().renderLight()
    for rend in self.rends:
      glPushMatrix()
      rend.renderLight()
      glPopMatrix()

  def render(self, ancestorSelected=False):
    super().render(ancestorSelected=ancestorSelected)
    if self in selected:
      ancestorSelected = True
    if not self.visible:
      return
    for rend in self.rends:
      glPushMatrix()
      rend.render(ancestorSelected=ancestorSelected)
      glPopMatrix()

  def renderSelectedAE(self):
    super().renderSelectedAE()
    for rend in self.rends:
      glPushMatrix()
      rend.renderSelectedAE()
      glPopMatrix()

  def renderOverlay(self):
    super().renderOverlay()
    for rend in self.rends:
      glPushMatrix()
      rend.renderOverlay()
      glPopMatrix()

  def update_bbox(self):
    if not self.rends:
      self.minPoint = Point(0, 0, 0)
      self.maxPoint = Point(0, 0, 0)
      super().update_bbox()
      return
    min_xyz = [None, None, None]
    max_xyz = [None, None, None]
    for rend in self.rends:
      for i, (minn, maxn, n) in enumerate(zip(min_xyz, max_xyz, rend.pos)):
        if minn is None or n < minn:
          min_xyz[i] = n
        if maxn is None or n > maxn:
          max_xyz[i] = n
    self.minPoint = Point(*min_xyz)
    self.maxPoint = Point(*max_xyz)
    super().update_bbox()

  def cycleCheckChildren(self):
    return self.rends

  def rayBBIntersections(self, rayV):
    self.glMat()
    for rend in self.rends:
      glPushMatrix()
      yield from rend.rayBBIntersections(rayV)
      glPopMatrix()

class Link(Renderable): # TODO: more overloads
  # Be cautious while using these
  # they're like link files in directories
  # you could end up in a loop if not careful
  def __init__(self, directory, *args, **kwargs):
    # There should only be links to directories.
    # non-pose attributes of all other Renderable objects
    # should be immutable.
    assert isinstance(directory, Directory)
    self.directory = directory
    super().__init__(*args, **kwargs)
##    self.pos = directory.pos
##    self.rot = directory.rot
##    self.name = directory.name + "_COPY"

  def __copy__(self):
    return Link(self.directory)

  def __deepcopy__(self, memo):
    return copy.copy(self)

  def renderLight(self):
    super().renderLight()
    for rend in self.directory.rends:
      glPushMatrix()
      rend.renderLight()
      glPopMatrix()

  def render(self, ancestorSelected=False):
    if self.directory in selected:
      selected.add(self)
    super().render(ancestorSelected=ancestorSelected)
    if self in selected:
      ancestorSelected = True
    if not self.visible:
      return
    global linkDepth
    linkDepth += 1
    for rend in self.directory.rends:
      glPushMatrix()
      rend.render(ancestorSelected=ancestorSelected)
      glPopMatrix()
    linkDepth -= 1

  def renderSelectedAE(self):
    super().renderSelectedAE()
    for rend in self.directory.rends:
      glPushMatrix()
      rend.renderSelectedAE()
      glPopMatrix()

  def renderOverlay(self):
    super().renderOverlay()
    for rend in self.directory.rends:
      glPushMatrix()
      rend.renderOverlay()
      glPopMatrix()

  def update_bbox(self):
    self.directory.update_bbox()
    self.minPoint = Point(0, 0, 0)
    self.maxPoint = Point(0, 0, 0)
    super().update_bbox()

  def placeBBox(self):
    self.directory.placeBBox()

  def cycleCheckChildren(self):
    return self.directory.rends

  def rayBBIntersections(self, rayV):
    self.glMat()
    for rend in self.directory.rends:
      glPushMatrix()
      yield from rend.rayBBIntersections(rayV)
      glPopMatrix()

class TreeError(Exception): # call when a tree is invalid (including links--they should not cycle to themselves)
  def __init__(self, path):
    self.path = path

  def __str__(self):
    return " > ".join(node.name for node in self.path)

class Scene:
  '''Defines a list of renderable objects'''
  
  def __init__(self, rends=None, ambientColor=(1.0, 1.0, 1.0), ambientPower=0.1):
    if rends == None:
      rends = set()
    self.rends = rends
    self.ambientColor = ambientColor
    self.ambientPower = ambientPower

  # convenience functions for set operation

  def __iter__(self):
    return self.rends.__iter__()

  def add(self, rend):
    self.rends.add(rend)

  def remove(self, rend):
    self.rends.remove(rend)

  def discard(self, rend):
    self.rends.discard(rend)

  def clear(self):
    self.rends.clear()

  def render(self, camera, aspect=1.33):
    '''Renders this entire scene'''
    global camPos, camTrueFovy, PHONG_SHADER
    camPos = camera.pos
    camTrueFovy = camera.getTrueFovy()
    if renderingMode == FULL:
      glClearColor(0.0, 0.0, 0.0, 0.0)
    elif renderingMode == FLAT:
      glClearColor(1.0, 1.0, 1.0, 0.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    
    # Push camera position/perspective matrix onto stack
    gluCamera(camera, aspect) # custom convenience function
    glMatrixMode(GL_MODELVIEW)

    glPushMatrix()
    glTranslatef(*camera.pos)
    if renderingMode == FLAT:
      gluGlobe() # draw a globe around the camera as a guide when orienting it
    glPopMatrix()

    # Ambient Light
    ambientColorPower = np.array(self.ambientColor)*self.ambientPower
    PHONG_SHADER.use()
    glUniform3f(Shader.current.uniformLocs["ambientColorPower"], *ambientColorPower)

    global linkDepth
    linkDepth = 0
    
    Lamp.begin()
    for rend in self.rends:
      glPushMatrix()
      rend.renderLight()
      glPopMatrix()
    Lamp.end()

    for rend in self.rends & selected:
      glPushMatrix()
      rend.render()
      glPopMatrix()

    for rend in self.rends - selected:
      glPushMatrix()
      rend.render()
      glPopMatrix()

    for rend in self.rends:
      glPushMatrix()
      rend.renderSelectedAE()
      glPopMatrix()
    
    ## RENDER OVERLAY
    glClear(GL_DEPTH_BUFFER_BIT)
    for rend in self.rends:
      glPushMatrix()
      rend.renderOverlay()
      glPopMatrix()

  def getRendFromXY(self, XY, camera, aspect=1.33):
    '''
Uses ray-box collision to get closes renderable whose
bbox collides with the ray made by the user's cursor.
If there aren't any, returns None.
    '''
    gluCamera(camera, aspect)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    rayV = gluUnProject(*XY,1.0)
    rayV = normalize(rayV)
    
    gluCamera(camera, aspect)
    glMatrixMode(GL_MODELVIEW)
    result = None
    minDist = float("Inf")
    for rend in self.rends:
      glPushMatrix()
      for rend, dist in rend.rayBBIntersections(rayV):
        if dist < minDist:
          result = rend
          minDist = dist
      glPopMatrix()

    return result

  def rendExists(self, rend):
    '''Tests whether rend is in my tree of renderables.'''
    def test(r):
      if r == rend:
        return True
      elif isinstance(r, Directory):
        return any(test(child) for child in r)
      else:
        return False
    return any(test(r) for r in self.rends)

  def debug_tree(self):
    '''Prints out tree of renderable objects, treating links as their directories.'''
    def tree(rend):
      yield "%d: %s"%(id(rend), rend.name)
      for child in rend.cycleCheckChildren():
        for line in tree(child):
          yield "    " + line
    print("SCENE")
    for rend in self.rends:
      for line in tree(rend):
        print("    " + line)
    print()
    

initialised = False

def initEngine(): # only call once context has been established
  '''
Initialises this module. Only call this
once an OpenGL context is established.
  '''
  global initialised
  if initialised:
    return

  global PHONG_SHADER, FLAT_SHADER, PLAIN_SHADER
  PHONG_SHADER = Shader(*SHADER_FILENAME_PAIRS["phong"])
  FLAT_SHADER = Shader(*SHADER_FILENAME_PAIRS["flat"])
  PLAIN_SHADER = Shader(*SHADER_FILENAME_PAIRS["plain"])
  
  # Enable wanted gl modes
  glEnable(GL_DEPTH_TEST)
  glEnable(GL_NORMALIZE)
  glEnable(GL_POLYGON_SMOOTH)
  glEnable(GL_DITHER)
  glEnable(GL_MULTISAMPLE)
  glEnable(GL_LIGHTING)
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
  glFogi(GL_FOG_MODE, GL_EXP)
  glFogf(GL_FOG_END, 1000.0)
  glFogf(GL_FOG_DENSITY, 0.1)

  global frameBuffer
  frameBuffer = glGenFramebuffers(1)
  
  
  initialised = True
  
if __name__ == "__main__":
  print("Hello, engine?")
  print("Engine BROKE.")
  print("Understandable, have a nice day.")
  print("...")
  print("To use engine.py, import it.")
  
