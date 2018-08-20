#!/usr/bin/python

from filein import *
from math import pi, tau, sin, cos, tan, atan, sqrt
import numpy as np

def intify(words):
  '''Intifies all items in list'''
  return [int(word) for word in words]

def floatify(words):
  '''Floatifies all items in list'''
  return [float(word) for word in words]

def fix_range(n, R):
  '''Rectifies n into the range R'''
  a, b = R
  assert a <= b
  return max(a, min(b, n))

def get_rotmatrix(rx, ry, rz): # -TILT, PAN, -ROLL
  '''Gets transformation matrix that rotates a point about rx, ry, rx'''
  x_rm = np.matrix([[1, 0,        0      ],
                    [0, cos(rx), -sin(rx)],
                    [0, sin(rx),  cos(rx)]
                    ])
  y_rm = np.matrix([[ cos(ry), 0, sin(ry)],
                    [ 0,       1, 0      ],
                    [-sin(ry), 0, cos(ry)]
                    ])
  z_rm = np.matrix([[cos(rz), -sin(rz), 0],
                    [sin(rz),  cos(rz), 0],
                    [0,        0,       1]
                    ])
  return x_rm * y_rm * z_rm

def mix_permute(lA, lB):
  '''Generates mixtures of lA and lB in a strict order'''
  # mix_permute([A, B, C], [D, E, F])
  # == ([A, B, C],
  #     [A, B, F],
  #     [A, E, C],
  #     [A, E, F],
  #     [D, B, C],
  #     [D, B, F],
  #     [D, E, C],
  #     [D, E, F]
  #     )
  assert len(lA) == len(lB)
  if len(lA) == 0:
    yield []
    return
  for result in mix_permute(lA[:-1], lB[:-1]):
    yield result + [lA[-1]]
    yield result + [lB[-1]]

class Point2d: # IMMUTABLE
  '''Describes a point in 2 dimensions'''
  def __init__(self, xy):
    assert len(xy) == 2
    assert all(type(n) in (int, float) for n in xy)
    self._xy = xy[0], xy[1]

  def __repr__(self):
    return "Point2d(%s)"%self._xy

  def __str__(self):
    return str(self._xy)

  def __getitem__(self, i):
    return self._xy[i]

  def __iter__(self):
    for n in self._xy:
      yield n

  def __len__(self):
    return 2

  def __add__(self, dxy): # vector-like addition
    assert len(dxy) == 2
    assert all(type(n) in (int, float) for n in dxy)
    x, y = self._xy
    dx, dy = dxy
    return Point2d((x+dx, y+dy))

  def __sub__(self, dxy): # vector-like subtraction
    assert len(dxy) == 2
    assert all(type(n) in (int, float) for n in dxy)
    x, y = self._xy
    dx, dy = dxy
    return Point2d((x+dx, y+dy))

  def __mul__(self, a): # scalar * vector
    x, y = self._xy
    return Point2d((a*x, a*y))

  def __rmul__(self, a): # __mul__ alias
    return self * a

  def __div__(self, a): # (1/scalar) * vector
    assert a != 0
    return self * (1/a)

class Point: # IMMUTABLE
  '''Describes a point in 3 dimensions'''
  def __init__(self, xyz):
    assert len(xyz) == 3
    assert all(type(n) in (int, float) for n in xyz)
    self._xyz = xyz[0], xyz[1], xyz[2]

  def __repr__(self):
    return "Point(%s)"%self._xyz

  def __str__(self):
    return str(self._xyz)

  def __getitem__(self, i):
    return self._xyz[i]

  def __iter__(self):
    for n in self._xyz:
      yield n

  def __len__(self):
    return 3

  def __add__(self, dxyz):
    assert len(dxyz) == 3
    assert all(type(n) in (int, float) for n in dxyz)
    x, y, z = self._xyz
    dx, dy, dz = dxyz
    return Point((x+dx, y+dy, z+dz))

  def __sub__(self, dxyz):
    assert len(dxyz) == 3
    assert all(type(n) in (int, float) for n in dxyz)
    x, y, z = self._xyz
    dx, dy, dz = dxyz
    return Point((x-dx, y-dy, z-dz))

  def __mul__(self, a):
    x, y, z = self._xyz
    if type(a) is Point:
      x2, y2, z2 = a
      return x*x2 + y*y2 + z*z2
    return Point((a*x, a*y, a*z))

  def __rmul__(self, a):
    if type(a) is np.matrix:
      return self.transform(a)
    return self * a

  def __div__(self, a):
    if type(a) is np.matrix:
      return a**-1 * self
    assert a != 0
    return self * (1/a)

  def get_mat(self):
    x, y, z = self._xyz
    return np.matrix([[x],
                      [y],
                      [z]])

  def transform(self, transmatrix):
    m = self.get_mat()
    new_m = transmatrix * m
    return Point(floatify(new_m.A1))

class Tri: # IMMUTABLE
  '''Describes a 3-D triangle with a 3-tuple of 3-D points'''
  def __init__(self, points, colour="#ff00ff60"):
    assert type(points) in (tuple, list)
    assert len(points) == 3
    assert all(type(p) is Point for p in points)
    self._points = tuple(points)
    self._normal = None
    self._eval_all()
    self._colour = colour

  def __repr__(self):
    return "Tri(%s, %s)"%(self._points, self._colour)

  def __str__(self):
    return ""

  def _eval_all(self):
    self._eval_normal()

  def _eval_normal(self):
    A, B, C = self
    b = (B - A)
    c = (C - A)
    self._normal = Point(floatify(np.cross(b, c)))

  def __getitem__(self, i):
    return self._points[i]

  def __iter__(self):
    for p in self._points:
      yield p

  def get_colour(self):
    return self._colour

  def get_normal(self):
    return self._normal

  def get_edges(self):
    yield (self._points[0], self._points[1])
    yield (self._points[1], self._points[2])
    yield (self._points[2], self._points[0])

class Polygon: # IMMUTABLE
  '''Describes a 3-D polygon with a list of 3-D points'''
  def __init__(self, points, colour="#ff00ff60"):
    assert type(points) in (tuple, list)
    assert len(points) >= 3
    assert all(type(p) is Point for p in points)
    self._points = list(points)

    self._tris = []
    p0 = self._points[0]
    for i in range(1, len(self._points)-1):
      pa, pb = self._points[i], self._points[i+1]
      self._tris.append(Tri((p0, pa, pb), colour=colour))

    self._colour = colour

  def __getitem__(self, i):
    return self._points[i]

  def __iter__(self):
    for p in self._points:
      yield p

  def get_tris(self):
    for tri in self._tris:
      yield tri

  def transform(self, transmatrix):
    return Polygon([transmatrix*p for p in self._points], colour=self._colour)

  def move(self, dxyz):
    return Polygon([p + dxyz for p in self._points], colour=self._colour)

  def scale(self, a):
    return Polygon([a*p for p in self._points], colour=self._colour)

  def get_edges(self):
    for i in range(len(self._points)):
      pA = self._points[i-1]
      pB = self._points[i]
      yield (pA, pB)

class BoundingBox: # IMMUTABLE
  '''Describes a 3-d bounding box from a minimum and maximum point'''
  def __init__(self, pMIN, pMAX):
    assert type(pMIN) is Point
    assert type(pMAX) is Point
    assert all(a <= b for a, b in zip(pMIN, pMAX))
    self._pMIN = pMIN
    self._pMAX = pMAX
    self._points = [] # In specific order
    self._edges = []
    self._faces = []
    self._eval_all()
  
  def _eval_all(self):
    self._eval_points()
    self._eval_edges()
    self._eval_faces()

  def _eval_points(self):
    self._points = []
    xyzs = mix_permute(list(self._pMIN), list(self._pMAX))
    for xyz in xyzs:
      self._points.append(Point(xyz))

  def _eval_edges(self):
    self._edges = []
    index_connections = [(0, 1), (2, 3), (4, 5), (6, 7), # Zward edges
                         (0, 2), (1, 3), (4, 6), (5, 7), # Yward edges
                         (0, 4), (1, 5), (2, 6), (3, 7)  # Xward edges
                         ]
    for iA, iB in index_connections:
      self._edges.append((self._points[iA], self._points[iB]))

  def _eval_faces(self):
    self._faces = []
    index_polypoints = [(0, 2, 1, 3), (7, 5, 6, 4),
                        (0, 4, 2, 6), (7, 3, 5, 1),
                        (0, 1, 5, 4), (7, 6, 2, 3)]
    for ituple in index_polypoints:
      self._faces.append(Polygon([self._points[i] for i in ituple]))

  def get_points(self):
    return self._points

  def get_edges(self):
    return self._edges

  def get_faces(self):
    return self._faces

class Model: # MUTABLE: CHANGE SCALE, ORIENTATION, AND POSITION
  '''Describes a polyhedron-like model with polygons that may share points'''
  def loadfrom_off(fn, colour="#ff00ff60", *args, **kwargs):
    contents = get_offcontents(fn)
    basepoints = []
    basepolys = []
    V, F = intify(contents[0][:2])
    for i in range(1, V+1):
      basepoints.append(Point(floatify(contents[i])))
    for i in range(V+1, len(contents)):
      _, *p_indices = intify(contents[i])
      poly_bps = [basepoints[p_i] for p_i in p_indices]
      basepolys.append(Polygon(poly_bps, colour=colour))
    return Model(basepolys, *args, **kwargs)
      
  def __init__(self, basepolys=[], pos=Point((0, 0, 0)), scale=1, rx=0.0, ry=0.0, rz=0.0):
    assert all(type(bp) is Polygon for bp in basepolys)
    assert type(pos) is Point
    self._basepolys = basepolys
    self._baseedges = self.eval_baseedges()
    self._pos = pos
    self._scale = scale
    self._rx = rx
    self._ry = ry
    self._rz = rz
    self._rotmatrix = np.matrix([[1, 0, 0],
                                 [0, 1, 0],
                                 [0, 0, 1]
                                 ])
    self._polys = []
    self._edges = []
    self._bbox = None
    self._refresh_all()

  def eval_baseedges(self):
    edge_set = set()
    for bp in self._basepolys:
      for edge in bp.get_edges():
        if edge in edge_set:
          continue
        if edge[::-1] in edge_set:
          continue
        edge_set.add(edge)
    return list(edge_set)

  def _refresh_all(self):
    self._refresh_polys()
    self._refresh_edges()
    self._refresh_bbox()

  def _refresh_polys(self):
    # update rotmatrix
    self._rotmatrix = get_rotmatrix(self._rx, self._ry, self._rz)
    self._polys = []
    for bp in self._basepolys:
      ## To 19 yo Marcus: I am so, so sorry you had to see this.
      poly = bp.transform(self._rotmatrix).scale(self._scale).move(self._pos)
      self._polys.append(poly)

  def _refresh_edges(self):
    self._edges = []
    for edge in self._baseedges:
      pA, pB = edge
      pA_dash = self._scale*(self._rotmatrix*pA) + self._pos
      pB_dash = self._scale*(self._rotmatrix*pB) + self._pos
      self._edges.append((pA_dash, pB_dash))

  def _refresh_bbox(self):
    minxyz = [None, None, None]
    maxxyz = [None, None, None]
    for poly in self._polys:
      for point in poly:
        for i, n in enumerate(point):
          minn = minxyz[i]
          maxn = maxxyz[i]
          if minn is None or n < minn:
            minxyz[i] = n
          if maxn is None or n > maxn:
            maxxyz[i] = n
    self._bbox = BoundingBox(Point(minxyz), Point(maxxyz))

  def __getitem__(self, i):
    return self._polys[i]

  def __iter__(self):
    for poly in self._polys:
      yield poly

  def get_edges(self):
    for edge in self._edges:
      yield edge

  def get_tris(self):
    for poly in self._polys:
      for tri in poly.get_tris():
        yield tri

  def get_bbox(self):
    return self._bbox

  def get_bbox_points(self):
    return self._bbox.get_points()

  def get_bbox_edges(self):
    return self._bbox.get_edges()

  def get_bbox_faces(self):
    return self._bbox.get_faces()

class Scene: # MUTABLE: ADD/REMOVE MODELS
  '''Describes a scene of objects using a list of them'''
  def __init__(self, models=set(), bg="#000000"):
    assert all(type(m) is Model for m in models)
    self._models = set(models)
    self._bg = bg

  def __getitem__(self, i):
    return self._models[i]

  def __iter__(self):
    for m in self._models:
      yield m

  def set_bg(self, bg):
    self._bg = bg

  def get_bg(self):
    return self._bg

  def add(self, model):
    assert type(model) is Model
    self._models.add(model)

  def remove(self, model):
    self._models.remove(model)

  def get_edges(self):
    for model in self._models:
      for edge in model.get_edges():
        yield edge

  def get_tris(self):
    for model in self._models:
      for tri in model.get_tris():
        yield tri

class Camera: # MUTABLE: CHANGE ORIENTATION, POSITION, ZOOM
  '''Describes a point in 3 dimensions in which a picture may be projected to'''
  def __init__(self, pos=Point((0, 0, 0)), pan=0.0, tilt=0.0, roll=0.0, xspan=300, yspan=200, logzoom=1.8, maxdepth=100, scene=Scene()):
    assert type(pos) is Point
    assert type(pan) in (int, float)
    assert type(tilt) in (int, float)
    assert type(roll) in (int, float)
    assert type(xspan) in (int, float)
    assert type(yspan) in (int, float)
    assert type(logzoom) in (int, float)
    pan %= tau # rotates counterclockwise as pan increases
    tilt = fix_range(tilt, (-pi, pi)) # tilt increase: camera tilts upwards and vise-versa
    roll = fix_range(roll, (-pi, pi)) # roll increase: camera rotates counterclockwise and vise-versa
    
    self._pos = pos
    self._pan = pan
    self._tilt = tilt
    self._roll = roll
    self._rotmatrix = np.matrix([[1, 0, 0],
                                 [0, 1, 0],
                                 [0, 0, 1]
                                 ])
    self._update_rotvars()
    self._xspan = xspan # == tan(angle from centre to right of view)
    self._yspan = yspan # == tan(angle from centre to top of view)
    self._logzoom = logzoom
    self._zoom = 10**logzoom # scales xy of projected points
    self._maxdepth = maxdepth
    self._visible_models = []
    self._scene = scene

  def _update_all(self):
    self._update_rotvars()
    self._update_visible_models()

  def _update_rotvars(self):
    self._rotmatrix = get_rotmatrix(self._tilt, -self._pan, self._roll)

  def _update_visible_models(self):
    self._visible_models = []
    for model in self._scene:
      if self.isvisible_bbox(model.get_bbox()):
        self._visible_models.append(model)

  def get_visible_tris(self):
    for model in self._visible_models:
      for tri in model.get_tris():
        yield tri

  def set_resolution(self, X2, Y2):
    assert X2 > 0
    assert Y2 > 0
    self._xspan = X2 / 2
    self._yspan = Y2 / 2

  def get_resolution(self):
    return (round(2*abs(self._xspan)), round(2*abs(self._yspan)))

  def set_xaov(self, xaov): # sets zoom based on xaov--Angle of View in the x axis
    assert 0 < xaov < pi
    X = tan(xaov/2)
    self._zoom = self._xspan/X

  def get_xaov(self):
    return 2 * atan(self._xspan/self._zoom)

  def get_pos(self):
    return self._pos

  def move(self, dxyz):
    self._pos += dxyz

  def move_to(self, xyz):
    self._pos = Point(xyz)

  def get_pan(self):
    return self._pan

  def get_tilt(self):
    return self._tilt

  def get_roll(self):
    return self._pan

  def set_pan(self, new_pan):
    assert type(new_pan) in (int, float)
    new_pan %= tau
    self._pan = new_pan
    self._update_rotvars()

  def set_tilt(self, new_tilt):
    assert type(new_tilt) in (int, float)
    new_tilt = fix_range(new_tilt, (-pi, pi))
    self._tilt = new_tilt
    self._update_rotvars()

  def set_roll(self, new_roll):
    assert type(new_roll) in (int, float)
    new_roll = fix_range(new_roll, (-pi, pi))
    self._roll = new_roll
    self._update_rotvars()

  def change_pan(self, d_theta):
    self.set_pan(self._pan + d_theta)

  def change_tilt(self, d_phi):
    self.set_tilt(self._tilt + d_phi)

  def change_roll(self, d_psi):
    self.set_roll(self._roll + d_psi)

  def set_logzoom(self, new_logzoom):
    assert type(new_logzoom) in (int, float)
    self._logzoom = new_logzoom
    self._zoom = 10**new_logzoom

  def change_logzoom(self, dlz):
    self.set_logzoom(self._logzoom + dlz)

  def set_maxdepth(self, new_maxdepth):
    assert type(new_maxdepth) in (int, float)
    assert new_maxdepth > 0
    self._maxdepth = new_maxdepth

  def get_maxdepth(self):
    return self._maxdepth

  def get_reldirvector(self, XY):
    z = self._zoom
    X, Y = XY
    return Point((X, Y, z))

  def get_relcoords(self, point):
    dxyz = point - self._pos
    rotated_dxyz = self._rotmatrix*dxyz
    return rotated_dxyz

  def get_depth(self, point):
    return self.get_relcoords(point)[2]
      

  def orthoproject_point(self, point):
    rdx, rdy, rdz = self.get_relcoords(point)
    X = self._zoom*rdx
    Y = self._zoom*rdy
    return Point2d((X, Y))

  def project_point(self, point): # returns (X, Y)--The displacements from the centre of viewbox
    rdx, rdy, rdz = self.get_relcoords(point)
    if rdz <= 0:
      return (None, None)
    X = self._zoom*(rdx/rdz)
    Y = self._zoom*(rdy/rdz)
    return Point2d((X, Y))

  def project_segment(self, pA, pB):
    xA, yA, zA = self.get_relcoords(pA)
    xB, yB, zB = self.get_relcoords(pB)
    if zA > 0 and zB > 0:
      return ((self._zoom*(xA/zA), self._zoom*(yA/zA)),
              (self._zoom*(xB/zB), self._zoom*(yB/zB))
              )
    elif zA <= 0 and zB <= 0:
      return (None, None)
    return (None, None) # TECHNICAL DIFFICULTIES
    # find point where (pA, pB) intersects the camera's normal plane
    dz = zB - zA
    dx = xB - xA
    dy = yB - yA
    xC = xA - (dx/dz)*zA
    yC = xA - (dy/dz)*zA
    
    if zA > 0:
      return (self._zoom*(xA/zA), self._zoom*(yA/zA)), (self._zoom*(xA + xC*10000), self._zoom*(yA + yC*10000))
    return (self._zoom*(xB/zB), self._zoom*(yB/zB)), (self._zoom*(xB + xC*10000), self._zoom*(yB + yC*10000))

  def set_scene(self, scene):
    self._scene = scene

  def isvisible_bbox(self, bbox):
    return True # TODO

  def get_wireframe_drawlines(self):
    for model in self._visible_models:
      for pA, pB in model.get_edges():
        ppA, ppB = self.project_segment(pA, pB)
        if ppA is None:
          continue
        coord_A = (ppA[0] + self._xspan, -ppA[1] + self._yspan)
        coord_B = (ppB[0] + self._xspan, -ppB[1] + self._yspan)
        yield (coord_A, coord_B)

  def get_bboxframe_drawlines(self):
    for model in self._visible_models:
      for pA, pB in model.get_bbox().get_edges():
        ppA, ppB = self.project_segment(pA, pB)
        if ppA is None:
          continue
        coord_A = (ppA[0] + self._xspan, -ppA[1] + self._yspan)
        coord_B = (ppB[0] + self._xspan, -ppB[1] + self._yspan)
        yield (coord_A, coord_B)

