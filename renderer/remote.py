#!/usr/bin/python
'''
remote.py

All user-friendly functions to modify a UserEnv go here.

'''
import sys, os

from rotpoint import Rot, Point
from assetloader import Mesh, Tex
from engine import Model, Camera, Scene
from math import radians
from OpenGL.GL import glViewport
from appdata import *
from PIL import Image
import saver

datainit()

class Remote:
  '''A remote to control a user environment with methods.'''
  def __init__(self, userenv):
    self.userenv = userenv # should be clear for saving
    self.saver = saver.Saver(userenv, self)

  def new(self):
    '''New project'''
    self.clearUserEnv()

  def load(self, fn):
    '''Load project--NOT IMPLEMENTED'''
    saver.load(fn)

  def save(self, fn):
    '''Save project--NOT IMPLEMENTED'''
    saver.save(fn)

  def loadMesh(self, fn, *args, **kwargs):
    '''Load a mesh into a Mesh object and an appdata file'''
    new_mesh = Mesh(fn, *args, **kwargs)
    dataclone(fn, "save/assets/meshes/%d.obj"%new_mesh.ID)
    return new_mesh

  def loadTexture(self, fn, *args, **kwargs):
    '''Load a texture into a Tex object and an appdata file'''
    new_tex = Tex(fn, *args, **kwargs)
    im = Image.open(fn)
    im.save(datapath("save/assets/textures/%d.png"%new_tex.ID), "PNG")
    return new_tex

  def addAsset(self, asset):
    '''Add a Texture object (Mesh, Tex) into the userenv'''
    has_asset = asset in self.userenv.assets
    self.userenv.assets.add(asset)
    return has_asset

  def delAsset(self, asset, rmpointer=True):
    '''Delete an asset from both its appdata location and userenv and unload it'''
    if type(asset) is Mesh:
      fn = "save/assets/meshes/%d.obj"%asset.ID
    elif type(asset) is Tex:
      fn = "save/assets/textures/%d.png"%asset.ID
    datarm(fn)
    asset.delete()
    if rmpointer:
      self.userenv.assets.discard(asset)

  def addRend(self, rend):
    '''Adds rend into userenv's scene'''
    has_rend = rend in self.userenv.scene.rends
    self.userenv.scene.add(rend)
    return has_rend

  def delRend(self, rend):
    '''Deletes rend from userenv's scene'''
    self.userenv.scene.discard(rend)

  def configModel(self, model, mesh=None, tex=None, pos=None, rot=None, scale=None, name=None):
    '''Configures Model object's assets, position, rotation, scale, and name'''
    assert model in self.userenv.models
    model.mesh = mmesh if mesh is not None else model.mesh
    model.tex = tex if tex is not None else model.tex
    model.pos = pos if pos is not None else model.pos
    model.rot = rot if rot is not None else model.rot
    model.scale = scale if scale is not None else model.scale
    model.name = name if name is not None else model.name

  def configCamera(self, pos=None, rot=None, fovy=None, zoom=None):
    '''Configure's camera's position, rotation, and field of view'''
    cam = self.userenv.camera # sorry my fingers are tired
    cam.pos = pos if pos is not None else cam.pos
    cam.rot = rot if rot is not None else cam.rot
    cam.fovy = fovy if fovy is not None else cam.fovy
    cam.zoom = zoom if zoom is not None else cam.zoom

  def changeCameraRot(self, drx, dry, drz):
    '''Adds delta rotation to camera's rotation'''
    self.userenv.camera.rot += (drx, dry, drz)

  def lookAt(self, rend):
    '''Makes camera look at object with 0 roll'''
    dpos = rend.pos - self.userenv.camera.pos
    self.userenv.camera.rot = Rot.from_delta3(dpos)

  def setFocus(self, rend):
    '''Sets focus on a renderable'''
    self.lookAt(rend)
    self.userenv.focus = rend

  def moveCamera(self, dx, dy, dz):
    '''Moves camera by deltas'''
    self.userenv.camera.pos += (dx, dy, dz)

  def resizeViewport(self, X, Y):
    '''Resizes the OpenGL viewport to (X, Y)'''
    glViewport(0,0, X,Y)

  def renderScene(self, aspect=1.33):
    '''Renders the scene into the OpenGL view buffer'''
    self.userenv.scene.render(self.userenv.camera, aspect=aspect)

  def getContextRes(self):
    '''Returns resolution of context'''
    return self.context.getres()

  def clearUserEnv(self):
    '''Clears user environment to a clean slate'''
    UE = self.userenv
    for asset in UE.assets:
      self.delAsset(asset, rmpointer = False)
    UE.focus = None
    UE.camera = Camera()
    UE.scene = Scene()
    UE.assets.clear()

  
