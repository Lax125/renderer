#!/usr/bin/python
'''
remote.py

All user-friendly functions to modify a UserEnv go here.

'''

from rotpoint import Rot, Point
from assetloader import Obj, Tex
from engine import Model, Camera
from math import radians
from OpenGL.GL import glViewport

class Remote:
  def __init__(self, userenv):
    self.userenv = userenv

  def loadObject(self, fn):
    new_obj = Obj(fn)
    self.addAsset(new_obj)
    return new_obj

  def loadTexture(self, fn):
    new_tex = Tex(fn)
    self.addAsset(new_tex)
    return new_tex

  def addAsset(self, asset):
    has_asset = asset in self.userenv.assets
    self.userenv.assets.add(asset)
    return has_asset

  def delAsset(self, asset):
    asset.delete()
    self.userenv.assets.discard(asset)

  def newRend(self, RendClass, *args, **kwargs):
    new_rend = RendClass(*args, **kwargs)
    self.addRend(new_rend)
    return new_rend

  def addRend(self, rend):
    has_rend = rend in self.userenv.scene.rends
    self.userenv.scene.add(rend)
    return has_rend

  def delRend(self, rend):
    self.userenv.scene.discard(rend)

  def showRend(self, rend):
    rend.visible = True

  def hideRend(self, rend):
    rend.visible = False

  def configModel(self, model, obj=None, tex=None, pos=None, rot=None, scale=None, name=None):
    assert model in self.userenv.models
    model.obj = obj if obj is not None else model.obj
    model.tex = tex if tex is not None else model.tex
    model.pos = pos if pos is not None else model.pos
    model.rot = rot if rot is not None else model.rot
    model.scale = scale if scale is not None else model.scale
    model.name = name if name is not None else model.name

  def configCamera(self, pos=None, rot=None, fovy=None):
    cam = self.userenv.camera # sorry my fingers are tired
    cam.pos = pos if pos is not None else cam.pos
    cam.rot = rot if rot is not None else cam.rot
    cam.fovy = fovy if fovy is not None else cam.fovy

  def changeCameraRot(self, drx, dry, drz):
    self.userenv.camera.rot += (drx, dry, drz)

  def lookAt(self, rend):
    dpos = rend.pos - self.userenv.camera.pos
    self.userenv.camera.rot = Rot.from_delta3(dpos)

  def setFocus(self, rend):
    self.lookAt(rend)
    self.userenv.focus = rend

  def moveCamera(self, dx, dy, dz):
    self.userenv.camera.pos += (dx, dy, dz)

  def resizeViewport(self, X, Y):
    glViewport(0,0, X,Y)

  def renderScene(self, aspect=1.33):
    self.userenv.scene.render(self.userenv.camera, aspect=aspect)

  def getContextRes(self):
    return self.context.getres()

  
