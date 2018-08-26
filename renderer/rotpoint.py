#!usr/bin/python
'''
rotpoint.py
describes positioning and rotation of cameras and models
'''

import logging
from typing import Iterable
from math import sin, cos, tan, atan2, pi, tau

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('rotpoint')

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

  def __mul__(self, a):
    x, y, z = self
    if type(a) is Point: # dot multiplication
      x2, y2, z2 = a
      return x*x2 + y*y2 + z*z2
    return Point(a*x, a*y, a*z)

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
    x, y, z = self
    return np.matrix([[x],
                      [y],
                      [z]])

  def transform(self, transmatrix):
    m = self.get_mat()
    new_m = transmatrix * m
    return Point(*floatify(new_m.A1))

class Rot(Tuple3f):
  '''Describes a rotation in 3 dimensions.
     (rx, ry, rz):
       rx - roll
       ry - pitch
       rz - yaw
  '''

  def from_delta3(dp, roll=0.0):
    '''Make Rot object from position delta'''
    dx, dy, dz = dp
    rz = atan2(dy, dx)
    ry = atan2(dz, hypot(dx, dy))
    rx = roll
    return Rot(rx, ry, rz)

  def get_transmat(self):
    '''Get transformation matrix of Rot object'''
    rx, ry, rz = self
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


if __name__ == "__main__":
  print(repr(Point(Point(1, 2, 3)) * Point(3, 2, 1)))
