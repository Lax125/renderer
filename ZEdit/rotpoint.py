#!/usr/bin/env python
'''
rotpoint.py
describes positioning and rotation of cameras and models
'''

from all_modules import *

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('rotpoint')

def floatify(l):
  return [float(n) for n in l]

class Tuple3f: #IMMUTABLE
  '''Describes a 3-tuple of floats'''
  
  def __init__(self, *abc) -> None:
    '''Initialise 3-tuple of floats'''
    if isinstance(abc[0], Tuple3f): # recursive initialisation does not break it
      self._abc = tuple(abc[0]._abc)
      return
    try:
      a, b, c = abc
      self._abc = (float(a), float(b), float(c))
    except Exception:
      logger.warning("Bad init args for Tuple3f object: {}".format(abc))
      self._abc = (0.0, 0.0, 0.0)

  def __repr__(self) -> str:
    return "{}{}".format(type(self).__name__, self._abc)

  def __str__(self) -> str:
    return str(self._abc)

  def __getitem__(self, i) -> float:
    return self._abc[i]

  def __iter__(self) -> Iterable[float]:
    for n in self._abc:
      yield n

  def __len__(self) -> int:
    return 3

  def __add__(self, dabc):
    a, b, c = self
    da, db, dc = dabc
    return type(self)(a+da, b+db, c+dc)

  def __sub__(self, dabc):
    a, b, c = self
    da, db, dc = dabc
    return type(self)(a-da, b-db, c-dc)

  def __copy__(self):
    return type(self)(*self._xyz)

  def __deepcopy__(self):
    return Tuple3f.__copy__(self)

class Point(Tuple3f): # IMMUTABLE
  '''Describes a point in 3 dimensions'''

  def __neg__(self):
    x, y, z = self
    return Point(-x, -y, -z)

  def __mul__(self, a):
    x, y, z = self
    if type(a) is Point: # dot multiplication
      x2, y2, z2 = a
      return x*x2 + y*y2 + z*z2
    return Point(a*x, a*y, a*z)

  def __rmul__(self, a):
    if type(a) is Rot:
      return self.transform(a.get_transmat())
    if type(a) is np.matrix:
      return self.transform(a)
    return self * a

  def __div__(self, a):
    if type(a) is np.matrix:
      return a**-1 * self
    assert a != 0
    return self * (1/a)

  def get_mat(self):
    x, y, z = self
    return np.matrix([[x],
                      [y],
                      [z]])

  def transform(self, transmatrix):
    '''Apply matrix transformation and return result'''
    m = self.get_mat()
    new_m = transmatrix * m
    return Point(*floatify(new_m.A1))

class Rot(Tuple3f):
  '''Describes a rotation in 3 dimensions.
     (rx, ry, rz):
       rx - pitch
       ry - yaw
       rz - roll
  '''

  def __init__(self, rx, ry, rz):
    rx %= tau
    ry %= tau
    rz %= tau
    super().__init__(rx, ry, rz)

  def from_delta3(dp, roll=0.0):
    '''Make Rot object from position delta'''
    dx, dy, dz = dp
    rz = roll
    ry = atan2(dx, -dz)
    rx = atan2(dy, hypot(dx, dz))
    return Rot(rx, ry, rz)

  def from_transmat(T):
    A = np.array(T)
    sy = hypot(A[0,1], A[1,1])
    ry = atan2(-A[2,0], A[2,2])
    rx = atan2(-A[2,1], sy)
    rz = atan2(-A[0,1], A[1,1])
    return Rot(rx, ry, rz)

  def __neg__(self):
    rx, ry, rz = self
    return Rot(-rx, -ry, -rz)

  def __mul__(self, a):
    if type(a) is Rot:
      return Rot.from_transmat(self.get_transmat()*a.get_transmat())
    return a.__rmul__(self)

  def get_transmat(self, invert=False):
    '''Get transformation matrix of Rot object'''
    rx, ry, rz = self
    if invert:
      rx, ry, rz = -rx, -ry, -rz
    x_rm = np.matrix([[1,  0,       0      ],
                      [0,  cos(rx), sin(rx)],
                      [0, -sin(rx), cos(rx)]
                      ])
    y_rm = np.matrix([[ cos(ry), 0, sin(ry)],
                      [ 0,       1, 0      ],
                      [-sin(ry), 0, cos(ry)]
                      ])
    z_rm = np.matrix([[cos(rz), -sin(rz), 0],
                      [sin(rz),  cos(rz), 0],
                      [0,        0,       1]
                      ])
    if invert:
      return y_rm * x_rm * z_rm
    return z_rm * x_rm * y_rm

  def get_forward_vector(self, invert=False):
    '''Forward is originally negative z'''
    return self.get_transmat(invert=invert) * Point(0, 0, -1)

  def get_upward_vector(self, invert=False):
    '''Upward is originally positive y'''
    return self.get_transmat(invert=invert) * Point(0, 1, 0)


if __name__ == "__main__":
  pass
