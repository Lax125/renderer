import sys, os
import zipfile
from appdata import *
from rotpoint import Rot, Point

def lazyReadlines(f):
  l = f.readline()
  while l:
    yield l
    l = f.readline()

def strRotPos(rot, pos):
  " ".join([*rot, *pos])

def deStrRotPos(s):
  nums = s.split()
  rot = Rot(*nums[0:3])
  pos = Point(*nums[3:6])
  return rot, pos

class Saver:
  def __init__(self, userenv, remote):
    self.userenv = userenv
    self.remote = remote

  def update(): # construct a .obj-like file that specifies construction of a userenv
    with dataopen("save/blueprint.dat", "w") as f:
      f.write("camera %s %s %s\n")

  def save(fn):
    self.update()

  def load(fn):
    self.remote.clearUserEnv()
    
